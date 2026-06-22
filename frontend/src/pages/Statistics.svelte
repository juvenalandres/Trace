<script lang="ts">
  import { onMount } from 'svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { statsApi } from '$lib/api/types';
  import type { VolumeResponse, PersonalRecordsResponse } from '$lib/api/types';

  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  const currentYear = new Date().getFullYear();
  let selectedYear = $state<number | null>(null);
  let volume = $state<VolumeResponse | null>(null);
  let prs = $state<PersonalRecordsResponse | null>(null);
  let loading = $state(true);
  let chartContainer = $state<HTMLDivElement | null>(null);
  let chart: uPlot | null = null;
  let tooltipEl = $state<HTMLDivElement | null>(null);
  let mouseX = 0;
  let mouseY = 0;
  let error = $state('');
  let resizeObserver: ResizeObserver | null = null;
  let availableYears = $state<number[]>([]);

  const sportColors: Record<string, string> = {
    ride: '#378ADD',
    run: '#1D9E75',
    swim: '#06b6d4',
    hike: '#f59e0b',
    walk: '#f59e0b',
    other: '#64748b',
  };

  const sportIcons: Record<string, string> = {
    ride: 'ride',
    run: 'activity',
    swim: 'swim',
    hike: 'hike',
    walk: 'activity',
    other: 'activity',
  };

  function formatKm(m: number): string {
    return (m / 1000).toFixed(1);
  }

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function formatDurationShort(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function formatSpeed(ms: number): string {
    return `${(ms * 3.6).toFixed(1)} km/h`;
  }

  const prConfig: Record<string, { label: string; icon: string; color: string; bg: string; unit: string; format: (v: number) => string }> = {
    longest_distance: { label: 'Longest distance', icon: 'distance', color: '#3b82f6', bg: '#3b82f620', unit: 'km', format: (v) => formatKm(v) },
    longest_duration: { label: 'Longest duration', icon: 'duration', color: '#14b8a6', bg: '#14b8a620', unit: '', format: (v) => formatDuration(v) },
    highest_elevation: { label: 'Highest elevation', icon: 'elevationUp', color: '#f59e0b', bg: '#f59e0b20', unit: 'm', format: (v) => `${Math.round(v)}` },
    fastest_speed: { label: 'Fastest avg speed', icon: 'speed', color: '#f97316', bg: '#f9731620', unit: 'km/h', format: formatSpeed },
    max_speed: { label: 'Top speed', icon: 'bolt', color: '#8b5cf6', bg: '#8b5cf620', unit: 'km/h', format: formatSpeed },
    highest_hr: { label: 'Highest avg HR', icon: 'heart', color: '#ec4899', bg: '#ec489920', unit: 'bpm', format: (v) => `${Math.round(v)}` },
  };

  function backfillMonths(monthly: VolumeResponse['monthly']) {
    if (monthly.length === 0) return monthly;
    const first = monthly[0].month;
    const last = monthly[monthly.length - 1].month;
    const [fy, fm] = first.split('-').map(Number);
    const [ly, lm] = last.split('-').map(Number);
    const dataMap = new Map(monthly.map(m => [m.month, m]));
    const result: VolumeResponse['monthly'] = [];
    let y = fy, m = fm;
    while (y < ly || (y === ly && m <= lm)) {
      const key = `${y}-${String(m).padStart(2, '0')}`;
      const existing = dataMap.get(key);
      if (existing) {
        result.push(existing);
      } else {
        result.push({ month: key, count: 0, distance_m: 0, duration_s: 0, elevation_m: 0, calories: 0 });
      }
      m++;
      if (m > 12) { m = 1; y++; }
    }
    return result;
  }

  function buildChart() {
    if (!chartContainer || !volume || volume.monthly.length === 0) return;

    chart?.destroy();
    chart = null;

    const filled = backfillMonths(volume.monthly);
    const months = filled.map(m => {
      const [y, mo] = m.month.split('-');
      return new Date(parseInt(y), parseInt(mo) - 1, 1).getTime() / 1000;
    });
    const distances = filled.map(m => m.distance_m / 1000);

    const plotData: uPlot.AlignedData = [
      new Float64Array(months),
      new Float64Array(distances),
    ];

    const multiYear = new Set(filled.map(m => m.month.split('-')[0])).size > 1;

    chart = new uPlot({
      width: chartContainer.clientWidth,
      height: 220,
      padding: [10, 40, 15, 0],
      cursor: {
        x: {
          formatter: (_u, val) => {
            const d = new Date(val * 1000);
            if (multiYear) {
              return d.toLocaleString('en', { month: 'short', year: '2-digit' });
            }
            return d.toLocaleString('en', { month: 'short' });
          },
        },
        points: {
          size: 4,
          fill: '#378ADD',
          stroke: '#fff',
          width: 1.5,
        },
      },
      axes: [
        {
          stroke: '#888',
          grid: { show: false },
          values: (_u, ticks) => ticks.map(t => {
            const d = new Date(t * 1000);
            if (multiYear) {
              return d.toLocaleString('en', { month: 'short', year: '2-digit' });
            }
            return d.toLocaleString('en', { month: 'short' });
          }),
        },
        {
          stroke: '#888',
          grid: { stroke: '#eee' },
          values: (_u, ticks) => ticks.map(t => `${t} km`),
        },
      ],
      series: [
        {},
        {
          stroke: '#378ADD',
          fill: '#E6F1FB',
          width: 1.5,
          points: { size: 5, fill: '#378ADD', stroke: '#fff', width: 1.5 },
        },
      ],
      legend: { show: false },
      hooks: {
        setCursor: [
          (u: uPlot) => {
            const idx = u.cursor.idx;
            if (idx != null && tooltipEl) {
              const val = distances[idx];
              if (val != null) {
                const d = new Date(months[idx] * 1000);
                const dateStr = d.toLocaleString('en', { month: 'short', year: 'numeric' });
                tooltipEl.innerHTML = `${dateStr} · <strong>${val.toFixed(1)} km</strong>`;
                tooltipEl.style.display = 'block';
                let finalLeft = mouseX + 12;
                let finalTop = mouseY - 36;
                const tw = tooltipEl.offsetWidth;
                const th = tooltipEl.offsetHeight;
                if (finalLeft + tw > window.innerWidth) finalLeft = mouseX - tw - 12;
                if (finalTop < 0) finalTop = mouseY + 12;
                tooltipEl.style.left = `${finalLeft}px`;
                tooltipEl.style.top = `${finalTop}px`;
              }
            }
          },
        ],
      },
    }, plotData, chartContainer);
  }

  function handleChartMouseMove(e: MouseEvent) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }

  function handleChartMouseLeave() {
    if (tooltipEl) tooltipEl.style.display = 'none';
  }

  async function loadStats() {
    loading = true;
    error = '';
    try {
      const [v, p] = await Promise.all([
        statsApi.volume(selectedYear ?? undefined),
        statsApi.personalRecords(undefined, selectedYear ?? undefined),
      ]);
      volume = v;
      prs = p;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load statistics';
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    try {
      availableYears = await statsApi.availableYears();
    } catch {
      availableYears = [currentYear];
    }
    loadStats();
    return () => {
      resizeObserver?.disconnect();
      chart?.destroy();
    };
  });

  function setupChartResize() {
    if (!chartContainer) return;
    resizeObserver?.disconnect();
    resizeObserver = new ResizeObserver(() => {
      if (chart && chartContainer) {
        chart.setSize({ width: chartContainer.clientWidth, height: chart.height });
      }
    });
    resizeObserver.observe(chartContainer);
  }

  $effect(() => {
    if (chartContainer && volume && volume.monthly.length > 0 && !loading && chartContainer.clientWidth > 0) {
      buildChart();
      setupChartResize();
    } else if (chart && (!volume || volume.monthly.length === 0 || loading)) {
      chart.destroy();
      chart = null;
    }
  });

  function setYear(y: number | null) {
    selectedYear = y;
    loadStats();
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Statistics</h1>
    <div class="year-picker">
      <button class="year-btn" class:active={selectedYear === null} onclick={() => setYear(null)}>All</button>
      {#each availableYears as y}
        <button class="year-btn" class:active={selectedYear === y} onclick={() => setYear(y)}>{y}</button>
      {/each}
    </div>
  </div>

  {#if loading}
    <LoadingSpinner />
  {:else if error}
    <ErrorBanner message={error} retry={loadStats} />
  {:else if !volume || (volume.monthly.length === 0 && volume.by_sport.length === 0)}
    <EmptyState icon="eddington" message="No statistics yet. Upload some activities to see your stats here." action="Upload" onAction={() => onNavigate?.('upload')} />
  {:else}
    {#if volume && volume.monthly.length > 0}
      <div class="dash-card">
        <div class="card-header">
          <div>
            <h3>Volume over time</h3>
            <div class="chart-subtitle">Monthly distance (km)</div>
          </div>
        </div>
        <div bind:this={chartContainer} class="chart" role="presentation" onmousemove={handleChartMouseMove} onmouseleave={handleChartMouseLeave}></div>
        <div bind:this={tooltipEl} class="chart-tooltip" style="display: none;"></div>
        <div class="chart-footer">
          <span class="footer-label">Time: —</span>
          <span class="footer-legend">
            <span class="legend-swatch" style="background: #378ADD"></span>
            Distance (km)
          </span>
        </div>
      </div>
    {/if}

    {#if volume && volume.by_sport.length > 0}
      {@const totalSportDistance = volume.by_sport.reduce((s, sp) => s + sp.distance_m, 0)}
      <div class="dash-card">
        <div class="card-header">
          <h3>By sport</h3>
        </div>
        <div class="sport-rows">
          {#each volume.by_sport as sport}
            {@const pct = totalSportDistance > 0 ? (sport.distance_m / totalSportDistance * 100) : 0}
            <div class="sport-row">
              <div class="sport-icon" style="background: {sportColors[sport.sport_type] ?? sportColors.other}20; color: {sportColors[sport.sport_type] ?? sportColors.other}">
                <Icon name={sportIcons[sport.sport_type] ?? 'activity'} size={16} />
              </div>
              <span class="sport-name">{sport.sport_type}</span>
              <div class="sport-bar-track">
                <div class="sport-bar-fill" style="width: {pct}%; background: {sportColors[sport.sport_type] ?? sportColors.other}"></div>
              </div>
              <span class="sport-stats">{formatKm(sport.distance_m)} km · {formatDurationShort(sport.duration_s)}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    {#if prs}
      <div class="pr-section">
        <h2>Personal records</h2>
        <div class="pr-grid">
          {#each Object.entries(prConfig) as [key, meta]}
            {@const pr = prs[key as keyof PersonalRecordsResponse]}
            {#if pr}
              <button class="record-card" onclick={() => onNavigate?.('activity', pr.activity_id)}>
                <div class="record-icon" style="background: {meta.bg}; color: {meta.color}">
                  <Icon name={meta.icon} size={18} />
                </div>
                <div class="record-label">{meta.label}</div>
                <div class="record-value">{meta.format(pr.value)}{#if meta.unit}<span class="record-unit">{meta.unit}</span>{/if}</div>
                <div class="record-source">{pr.name}</div>
              </button>
            {/if}
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .page {
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
    font-family: var(--font-sans);
  }
  .page-header {
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
  .year-picker {
    display: flex;
    gap: 4px;
  }
  .year-btn {
    padding: 5px 12px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    cursor: pointer;
    transition: all 0.15s;
  }
  .year-btn:hover {
    background: var(--hover);
    color: var(--text);
  }
  .year-btn.active {
    border: 1.5px solid #378ADD;
    color: #185FA5;
    font-weight: var(--font-weight-medium, 500);
    background: transparent;
  }
  .chart-subtitle {
    font-size: 12px;
    font-weight: 400;
    color: #185FA5;
    margin-top: 2px;
  }
  .chart {
    margin-bottom: 8px;
    width: 100%;
  }
  .chart-tooltip {
    position: fixed;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    z-index: 1000;
    pointer-events: none;
    white-space: nowrap;
    color: var(--text-secondary);
  }
  .chart-tooltip :global(strong) {
    font-weight: 500;
    color: var(--text);
  }
  .chart-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    font-size: 11px;
    color: var(--text-secondary);
    padding-top: 8px;
    border-top: 0.5px solid var(--border);
  }
  .footer-label {
    color: var(--text-secondary);
  }
  .footer-legend {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .legend-swatch {
    width: 8px;
    height: 8px;
    border-radius: 1px;
    display: inline-block;
  }
  .dash-card {
    margin-bottom: 20px;
  }
  .sport-rows {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .sport-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .sport-icon {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .sport-name {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text);
    width: 40px;
    text-transform: capitalize;
  }
  .sport-bar-track {
    flex: 1;
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
  }
  .sport-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .sport-stats {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    white-space: nowrap;
    min-width: 100px;
    text-align: right;
  }
  .pr-section {
    margin-top: 20px;
  }
  .pr-section h2 {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    margin-bottom: 12px;
    color: var(--text);
  }
  .pr-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
  .record-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 16px;
    text-align: left;
    cursor: pointer;
    font-family: var(--font-sans);
    transition: all 0.15s;
  }
  .record-card:hover {
    border-color: var(--primary);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }
  .record-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
  }
  .record-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }
  .record-value {
    font-size: 26px;
    font-weight: 500;
    color: var(--text);
    line-height: 1.1;
  }
  .record-unit {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-left: 4px;
  }
  .record-source {
    font-size: 12px;
    font-weight: 400;
    color: #185FA5;
    margin-top: 4px;
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: var(--font-size-2xl, 22px); }
    .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
    .year-picker { flex-wrap: wrap; }
    .pr-grid { grid-template-columns: repeat(2, 1fr); }
  }
</style>
