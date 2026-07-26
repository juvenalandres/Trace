<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import { api } from '$lib/api/client';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import Modal from '$lib/components/Modal.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';

  interface FitnessTest {
    id: number;
    user_id: number;
    test_type: string;
    value: number;
    unit: string;
    start_time: string;
    end_time: string;
    fit_file_path: string | null;
    notes: string | null;
    created_at: string;
  }

  interface ChartData {
    timestamps: number[];
    power: (number | null)[];
    hr: (number | null)[];
    elevation: (number | null)[];
    speed: (number | null)[];
    fit_start_time: string | null;
  }

  const TEST_TYPES = [
    { value: 'ftp', label: 'FTP (Functional Threshold Power)', unit: 'watts', icon: 'chart' },
    { value: 'lthr', label: 'LTHR (Lactate Threshold HR)', unit: 'bpm', icon: 'insights' },
    { value: 'threshold_pace', label: 'Threshold Pace', unit: 'min/km', icon: 'activities' },
    { value: 'max_hr', label: 'Max Heart Rate', unit: 'bpm', icon: 'heart' },
  ];

  const HR_ZONE_PERCENTAGES = [
    { zone: 1, min: 0.50, max: 0.60, label: 'Recovery' },
    { zone: 2, min: 0.60, max: 0.70, label: 'Aerobic' },
    { zone: 3, min: 0.70, max: 0.80, label: 'Tempo' },
    { zone: 4, min: 0.80, max: 0.90, label: 'Threshold' },
    { zone: 5, min: 0.90, max: 1.00, label: 'VO2 Max' },
  ];

  let tests = $state<FitnessTest[]>([]);
  let loading = $state(true);
  let error = $state('');
  let showAddTest = $state(false);
  let testType = $state('ftp');
  let notes = $state('');
  let fitFile = $state<File | null>(null);
  let chartData = $state<ChartData | null>(null);
  let uploading = $state(false);
  let saving = $state(false);
  let parsing = $state(false);

  let chartContainer = $state<HTMLDivElement>();
  let chart: uPlot | null = null;
  let selectionStart = $state(0);
  let selectionEnd = $state(0);
  let startIdx = $state(0);
  let endIdx = $state(0);
  let computedValue = $state<number | null>(null);

  let progressContainer = $state<HTMLDivElement>();
  let progressChart: uPlot | null = null;

  let filterType = $state<string>('');

  let filteredTests = $derived(
    filterType ? tests.filter(t => t.test_type === filterType) : tests
  );

  let groupedTests = $derived.by(() => {
    const groups: Record<string, FitnessTest[]> = {};
    for (const t of filteredTests) {
      if (!groups[t.test_type]) groups[t.test_type] = [];
      groups[t.test_type].push(t);
    }
    return groups;
  });

  function formatTestType(type: string): string {
    return TEST_TYPES.find(t => t.value === type)?.label ?? type;
  }

  function formatTestValue(value: number, unit: string): string {
    if (unit === 'min/km') {
      const mins = Math.floor(value);
      const secs = Math.round((value - mins) * 60);
      return `${mins}:${secs.toString().padStart(2, '0')} /km`;
    }
    if (unit === 'watts') return `${Math.round(value)} W`;
    if (unit === 'bpm') return `${Math.round(value)} bpm`;
    return `${value} ${unit}`;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function formatDuration(startIso: string, endIso: string): string {
    const s = new Date(startIso).getTime();
    const e = new Date(endIso).getTime();
    const secs = Math.round((e - s) / 1000);
    const m = Math.floor(secs / 60);
    const sec = secs % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  async function load() {
    loading = true;
    error = '';
    try {
      tests = await api.get<FitnessTest[]>('/tests');
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load tests';
    } finally {
      loading = false;
    }
  }

  function openAddTest() {
    testType = 'ftp';
    notes = '';
    fitFile = null;
    chartData = null;
    computedValue = null;
    selectionStart = 0;
    selectionEnd = 0;
    showAddTest = true;
  }

  function closeAddTest() {
    showAddTest = false;
    if (chart) { chart.destroy(); chart = null; }
  }

  function handleFileSelect(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      fitFile = file;
      parseFitFile(file);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer?.files[0];
    if (file && file.name.toLowerCase().endsWith('.fit')) {
      fitFile = file;
      parseFitFile(file);
    }
  }

  async function parseFitFile(file: File) {
    parsing = true;
    error = '';
    try {
      chartData = await api.upload<ChartData>('/tests/parse-fit', file);
      if (chartData && chartData.timestamps.length > 0) {
        startIdx = 0;
        endIdx = chartData.timestamps.length - 1;
        selectionStart = chartData.timestamps[0];
        selectionEnd = chartData.timestamps[chartData.timestamps.length - 1];
        await tick();
        buildChart();
        computeValue();
      }
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to parse FIT file';
    } finally {
      parsing = false;
    }
  }

  function buildChart() {
    if (!chartContainer || !chartData) return;
    if (chart) chart.destroy();

    const ts = chartData.timestamps;
    const power = chartData.power;
    const hr = chartData.hr;
    const ele = chartData.elevation;

    const data: uPlot.AlignedData = [ts, power, hr, ele];

    const opts: uPlot.Options = {
      width: chartContainer.clientWidth,
      height: 300,
      axes: [
        { stroke: '#888', grid: { stroke: '#eee' }, values: (_u: uPlot, vals: number[]) => vals.map(v => formatChartTime(v)) },
        { stroke: '#888', grid: { stroke: '#eee' }, side: 1, values: (_u: uPlot, vals: number[]) => vals.map(v => `${Math.round(v)} W`) },
        { stroke: '#ef4444', grid: { show: false }, side: 3, values: (_u: uPlot, vals: number[]) => vals.map(v => `${Math.round(v)} bpm`) },
        { show: false },
      ],
      series: [
        {},
        { stroke: '#3b82f6', width: 2, label: 'Power' },
        { stroke: '#ef4444', width: 1.5, label: 'HR', points: { show: false } },
        { stroke: '#94a3b8', width: 1, fill: 'rgba(148,163,184,0.1)', label: 'Elevation' },
      ],
    };

    chart = new uPlot(opts, data, chartContainer);
  }

  function formatChartTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function updateSelectionFromIdx() {
    if (!chartData) return;
    if (startIdx >= chartData.timestamps.length) startIdx = chartData.timestamps.length - 1;
    if (endIdx >= chartData.timestamps.length) endIdx = chartData.timestamps.length - 1;
    if (endIdx < startIdx) endIdx = startIdx;
    selectionStart = chartData.timestamps[startIdx];
    selectionEnd = chartData.timestamps[endIdx];
    computeValue();
  }

  function computeValue() {
    if (!chartData) return;

    const ts = chartData.timestamps;
    const power = chartData.power;
    const hr = chartData.hr;

    let totalPower = 0;
    let powerCount = 0;
    let totalHr = 0;
    let hrCount = 0;
    let maxHr = 0;
    let totalSpeed = 0;
    let speedCount = 0;

    for (let i = 0; i < ts.length; i++) {
      if (ts[i] >= selectionStart && ts[i] <= selectionEnd) {
        if (power[i] != null) { totalPower += power[i]!; powerCount++; }
        if (hr[i] != null) { totalHr += hr[i]!; hrCount++; if (hr[i]! > maxHr) maxHr = hr[i]!; }
        if (chartData.speed[i] != null) { totalSpeed += chartData.speed[i]!; speedCount++; }
      }
    }

    const testDef = TEST_TYPES.find(t => t.value === testType);
    if (!testDef) return;

    if (testType === 'ftp') {
      computedValue = powerCount > 0 ? Math.round((totalPower / powerCount) * 0.95) : null;
    } else if (testType === 'lthr') {
      computedValue = hrCount > 0 ? Math.round(totalHr / hrCount) : null;
    } else if (testType === 'threshold_pace') {
      if (speedCount > 0) {
        const avgSpeed = totalSpeed / speedCount;
        computedValue = avgSpeed > 0 ? Math.round((1 / avgSpeed) * 1000 * 100) / 100 : null;
      } else {
        computedValue = null;
      }
    } else if (testType === 'max_hr') {
      computedValue = maxHr > 0 ? maxHr : null;
    }
  }

  function buildProgressChart() {
    if (!progressContainer) return;
    if (progressChart) progressChart.destroy();

    const grouped = groupedTests;
    const types = Object.keys(grouped);
    if (types.length === 0) return;

    const series: uPlot.Series[] = [{}];
    const colors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b'];

    types.forEach((_, i) => {
      series.push({
        stroke: colors[i % colors.length],
        width: 2,
        points: { show: true, size: 4 },
      });
    });

    const allDates = new Set<number>();
    for (const type of types) {
      for (const t of grouped[type]) {
        allDates.add(new Date(t.created_at).getTime() / 1000);
      }
    }
    const sortedDates = [...allDates].sort((a, b) => a - b);

    const data: uPlot.AlignedData = [sortedDates];
    for (const type of types) {
      const vals: (number | null)[] = [];
      for (const d of sortedDates) {
        const match = grouped[type].find(t => Math.abs(new Date(t.created_at).getTime() / 1000 - d) < 86400);
        vals.push(match ? match.value : null);
      }
      data.push(vals);
    }

    const opts: uPlot.Options = {
      width: progressContainer.clientWidth,
      height: 200,
      axes: [
        { stroke: '#888', grid: { stroke: '#eee' }, values: (_u: uPlot, vals: number[]) => vals.map(v => new Date(v * 1000).toLocaleDateString('en-GB', { month: 'short', year: '2-digit' })) },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series,
    };

    progressChart = new uPlot(opts, data, progressContainer);
  }

  async function saveTest() {
    if (!fitFile || !chartData || computedValue === null) return;
    saving = true;
    error = '';

    const fitRefTime = chartData.fit_start_time ? new Date(chartData.fit_start_time) : new Date();
    const startIso = new Date(fitRefTime.getTime() + selectionStart * 1000).toISOString();
    const endIso = new Date(fitRefTime.getTime() + selectionEnd * 1000).toISOString();

    try {
      const testDef = TEST_TYPES.find(t => t.value === testType);
      await api.upload<FitnessTest>('/tests', fitFile, {
        test_type: testType,
        value: String(computedValue),
        unit: testDef?.unit ?? '',
        start_time: startIso,
        end_time: endIso,
        notes: notes || '',
      });

      if (testType === 'lthr' && computedValue) {
        const lthr = computedValue;
        const zones: Record<string, number> = {};
        for (const z of HR_ZONE_PERCENTAGES) {
          zones[`zone_${z.zone}_min`] = Math.round(lthr * z.min);
          zones[`zone_${z.zone}_max`] = Math.round(lthr * z.max);
        }
        try {
          await api.post('/zones', { zone_type: 'hr', ...zones });
        } catch {
          // zone update is best-effort
        }
      }

      await load();
      closeAddTest();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save test';
    } finally {
      saving = false;
    }
  }

  async function deleteTest(id: number) {
    try {
      await api.del(`/tests/${id}`);
      await load();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete test';
    }
  }

  onMount(() => {
    load();
  });

  $effect(() => {
    if (tests.length > 0) {
      setTimeout(() => buildProgressChart(), 50);
    }
  });

  onDestroy(() => {
    chart?.destroy();
    progressChart?.destroy();
  });
</script>

<div class="fitness-tests">
  <div class="top-bar">
    <h1>Fitness Tests</h1>
    <button class="btn btn-primary" onclick={openAddTest}>
      <Icon name="upload" size={16} />
      Add Test
    </button>
  </div>

  {#if error}
    <ErrorBanner message={error} />
  {/if}

  {#if loading}
    <LoadingSpinner size="lg" />
  {:else}
    {#if tests.length > 0}
      <div class="section">
        <h2>Progression</h2>
        <div class="chart-card">
          <div bind:this={progressContainer} class="chart-container"></div>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>Test History</h2>
          <div class="filter-pills">
            <button class="pill" class:active={filterType === ''} onclick={() => filterType = ''}>All</button>
            {#each TEST_TYPES as tt}
              {#if tests.some(t => t.test_type === tt.value)}
                <button class="pill" class:active={filterType === tt.value} onclick={() => filterType = tt.value}>
                  {tt.value.toUpperCase()}
                </button>
              {/if}
            {/each}
          </div>
        </div>
        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Result</th>
                <th>Duration</th>
                <th>Notes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {#each filteredTests as test}
                <tr>
                  <td>{formatDate(test.created_at)}</td>
                  <td><span class="type-badge" data-type={test.test_type}>{test.test_type.toUpperCase()}</span></td>
                  <td class="result-value">{formatTestValue(test.value, test.unit)}</td>
                  <td>{formatDuration(test.start_time, test.end_time)}</td>
                  <td class="notes-cell">{test.notes || '--'}</td>
                  <td>
                    <button class="btn btn-icon btn-danger-icon" onclick={() => deleteTest(test.id)} title="Delete">
                      <Icon name="logout" size={14} />
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {:else}
      <div class="empty-state">
        <Icon name="chart" size={48} />
        <h3>No tests recorded yet</h3>
        <p>Upload a FIT file from a test effort to track your fitness progression.</p>
        <button class="btn btn-primary" onclick={openAddTest}>Add Your First Test</button>
      </div>
    {/if}
  {/if}
</div>

<Modal open={showAddTest} title="Add Fitness Test" onClose={closeAddTest}>
  <div class="add-test-form">
    <div class="field">
      <label for="test-type">Test Type</label>
      <select id="test-type" bind:value={testType}>
        {#each TEST_TYPES as tt}
          <option value={tt.value}>{tt.label}</option>
        {/each}
      </select>
    </div>

    <div class="field">
      <label>FIT File</label>
      {#if fitFile}
        <div class="file-loaded">
          <Icon name="activities" size={16} />
          <span>{fitFile.name}</span>
          <button class="btn btn-sm" onclick={() => { fitFile = null; chartData = null; computedValue = null; }}>Change</button>
        </div>
      {:else}
        <div
          class="upload-zone"
          ondragover={(e) => e.preventDefault()}
          ondrop={handleDrop}
          onclick={() => document.getElementById('fit-upload')?.click()}
          role="button"
          tabindex="0"
        >
          <Icon name="upload" size={24} />
          <span>Drop FIT file here or click to browse</span>
          <input id="fit-upload" type="file" accept=".fit" onchange={handleFileSelect} style="display:none" />
        </div>
      {/if}
      {#if parsing}
        <div class="parsing-indicator">
          <LoadingSpinner size="sm" /> Parsing FIT file...
        </div>
      {/if}
    </div>

    {#if chartData && chartData.timestamps.length > 0}
      <div class="field">
        <label>Select Time Window</label>
        <div class="chart-card">
          <div bind:this={chartContainer} class="chart-container"></div>
        </div>
        <div class="range-sliders">
          <div class="range-row">
            <span class="range-label">Start</span>
            <input
              type="range"
              min={0}
              max={chartData.timestamps.length - 1}
              value={startIdx}
              oninput={(e) => { startIdx = parseInt((e.target as HTMLInputElement).value); updateSelectionFromIdx(); }}
            />
            <span class="range-value">{formatChartTime(selectionStart)}</span>
          </div>
          <div class="range-row">
            <span class="range-label">End</span>
            <input
              type="range"
              min={0}
              max={chartData.timestamps.length - 1}
              value={endIdx}
              oninput={(e) => { endIdx = parseInt((e.target as HTMLInputElement).value); updateSelectionFromIdx(); }}
            />
            <span class="range-value">{formatChartTime(selectionEnd)}</span>
          </div>
        </div>
        <div class="selection-info">
          <span class="selection-duration">Selected: {formatChartTime(selectionEnd - selectionStart)}</span>
        </div>
      </div>

      {#if computedValue !== null}
        <div class="result-preview">
          <div class="result-label">Computed {testType.toUpperCase()}</div>
          <div class="result-number">{formatTestValue(computedValue, TEST_TYPES.find(t => t.value === testType)?.unit ?? '')}</div>
          {#if testType === 'ftp'}
            <div class="result-hint">95% of average power in selection</div>
          {:else if testType === 'lthr'}
            <div class="result-hint">Average HR in selection. HR zones will be updated.</div>
          {:else if testType === 'threshold_pace'}
            <div class="result-hint">Average pace in selection</div>
          {:else if testType === 'max_hr'}
            <div class="result-hint">Maximum HR in selection</div>
          {/if}
        </div>
      {/if}
    {/if}

    <div class="field">
      <label for="test-notes">Notes (optional)</label>
      <textarea id="test-notes" bind:value={notes} rows="2" placeholder="e.g. Ramp test, felt strong..."></textarea>
    </div>

    <div class="form-actions">
      <button class="btn btn-outline" onclick={closeAddTest}>Cancel</button>
      <button class="btn btn-primary" onclick={saveTest} disabled={saving || !fitFile || computedValue === null}>
        {saving ? 'Saving...' : 'Save Test'}
      </button>
    </div>
  </div>
</Modal>

<style>
  .fitness-tests {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
    font-family: var(--font-sans);
  }
  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }
  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  h2 {
    font-size: var(--font-size-lg, 15px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0 0 12px 0;
  }
  .section { margin-bottom: 28px; }
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .chart-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 16px;
    overflow: hidden;
  }
  .chart-container {
    width: 100%;
  }
  .filter-pills {
    display: flex;
    gap: 6px;
  }
  .pill {
    padding: 4px 12px;
    border-radius: 16px;
    border: 0.5px solid var(--border);
    background: var(--surface);
    color: var(--text-secondary);
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
    font-family: var(--font-sans);
  }
  .pill.active {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
  }
  .table-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    overflow: hidden;
  }
  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm, 12px);
  }
  .data-table th {
    text-align: left;
    padding: 10px 14px;
    font-weight: var(--font-weight-medium, 500);
    font-size: var(--font-size-xs, 11px);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg);
    border-bottom: 0.5px solid var(--border);
  }
  .data-table td {
    padding: 10px 14px;
    border-bottom: 0.5px solid var(--border);
  }
  .type-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    text-transform: uppercase;
  }
  .type-badge[data-type="ftp"] { background: #3b82f620; color: #3b82f6; }
  .type-badge[data-type="lthr"] { background: #ef444420; color: #ef4444; }
  .type-badge[data-type="threshold_pace"] { background: #22c55e20; color: #22c55e; }
  .type-badge[data-type="max_hr"] { background: #f59e0b20; color: #f59e0b; }
  .result-value {
    font-weight: var(--font-weight-medium, 500);
  }
  .notes-cell {
    color: var(--text-secondary);
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-secondary);
  }
  .empty-state h3 {
    font-size: var(--font-size-lg, 15px);
    font-weight: var(--font-weight-medium, 500);
    margin: 16px 0 8px 0;
    color: var(--text);
  }
  .empty-state p {
    font-size: var(--font-size-base, 13px);
    margin: 0 0 20px 0;
  }
  .add-test-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 500px;
    font-family: var(--font-sans);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
  }
  .field select, .field textarea {
    padding: 10px 12px;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    background: var(--bg);
    color: var(--text);
  }
  .field select:focus, .field textarea:focus {
    outline: none;
    border-color: var(--primary);
  }
  .upload-zone {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 24px;
    border: 2px dashed var(--border);
    border-radius: 10px;
    cursor: pointer;
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    transition: border-color 0.2s;
  }
  .upload-zone:hover {
    border-color: var(--primary);
  }
  .file-loaded {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: var(--bg);
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-size: var(--font-size-base, 13px);
  }
  .file-loaded span {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .parsing-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: var(--font-size-sm, 12px);
    color: var(--primary);
  }
  .selection-info {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: center;
    margin-top: 8px;
    font-size: var(--font-size-sm, 12px);
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }
  .range-sliders {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .range-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .range-label {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    width: 40px;
    flex-shrink: 0;
  }
  .range-row input[type="range"] {
    flex: 1;
    accent-color: var(--primary);
  }
  .range-value {
    font-size: var(--font-size-sm, 12px);
    font-variant-numeric: tabular-nums;
    color: var(--text);
    width: 50px;
    text-align: right;
    flex-shrink: 0;
  }
  .selection-duration {
    color: var(--text-secondary);
  }
  .result-preview {
    background: color-mix(in srgb, var(--primary) 8%, transparent);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
  }
  .result-label {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .result-number {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--primary);
  }
  .result-hint {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    margin-top: 4px;
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border: none;
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
  }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { opacity: 0.9; }
  .btn-outline {
    background: var(--surface);
    color: var(--text);
    border: 0.5px solid var(--border);
  }
  .btn-outline:hover { background: var(--hover); }
  .btn-sm { padding: 4px 8px; font-size: var(--font-size-xs, 11px); }
  .btn-icon {
    background: none;
    border: none;
    color: var(--text-secondary);
    padding: 6px;
    border-radius: 6px;
    cursor: pointer;
  }
  .btn-icon:hover { background: var(--hover); }
  .btn-danger-icon { color: #dc2626; }
  .btn-danger-icon:hover { background: #fee2e2; }
  @media (max-width: 768px) {
    .fitness-tests { padding: 16px; }
    .add-test-form { min-width: auto; }
    .section-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  }
</style>
