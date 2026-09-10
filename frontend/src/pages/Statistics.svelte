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
  import TimeDistribution from '$lib/components/TimeDistribution.svelte';
  import HRDistribution from '$lib/components/HRDistribution.svelte';
  import WeeklyChart from '$lib/components/WeeklyChart.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  const currentYear = new Date().getFullYear();
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
  let chartMetric = $state<'distance' | 'time' | 'elevation'>('distance');

  const YEAR_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];
  const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const sportColors: Record<string, string> = {
    ride: 'var(--sport-ride)',
    run: 'var(--sport-run)',
    swim: 'var(--sport-swim)',
    hike: 'var(--sport-hike)',
    walk: 'var(--sport-walk)',
    other: 'var(--sport-other)',
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
    return Math.round(m / 1000).toLocaleString();
  }

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function formatDurationLong(s: number): string {
    const w = Math.floor(s / 604800);
    const d = Math.floor((s % 604800) / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    const parts: string[] = [];
    if (w > 0) parts.push(`${w}w`);
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0 || parts.length === 0) parts.push(`${m}m`);
    return parts.join(' ');
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

  const metricConfig = {
    distance: { label: 'Distance', key: 'distance_m' as const, unit: 'km', format: (v: number) => `${formatKm(v)} km`, yFormat: (v: number) => `${Math.round(v)} km` },
    time: { label: 'Time', key: 'duration_s' as const, unit: 'h', format: (v: number) => formatDurationLong(v), yFormat: (v: number) => `${Math.round(v)}h` },
    elevation: { label: 'Elevation', key: 'elevation_m' as const, unit: 'm', format: (v: number) => `${Math.round(v).toLocaleString()} m`, yFormat: (v: number) => `${Math.round(v).toLocaleString()} m` },
  };

  const prConfig: Record<string, { label: string; icon: string; color: string; bg: string; unit: string; format: (v: number) => string }> = {
    longest_distance: { label: 'Longest distance', icon: 'distance', color: 'var(--primary)', bg: 'var(--primary-bg)', unit: 'km', format: (v) => `${formatKm(v)} km` },
    longest_duration: { label: 'Longest duration', icon: 'duration', color: 'var(--success)', bg: 'var(--success-bg)', unit: '', format: (v) => formatDuration(v) },
    highest_elevation: { label: 'Highest elevation', icon: 'elevationUp', color: 'var(--warning)', bg: 'var(--warning-bg)', unit: 'm', format: (v) => `${Math.round(v).toLocaleString()} m` },
    fastest_speed: { label: 'Fastest avg speed', icon: 'speed', color: 'var(--chart-2)', bg: 'color-mix(in srgb, var(--chart-2) 12%, transparent)', unit: 'km/h', format: formatSpeed },
    max_speed: { label: 'Top speed', icon: 'bolt', color: 'var(--chart-3)', bg: 'color-mix(in srgb, var(--chart-3) 12%, transparent)', unit: 'km/h', format: formatSpeed },
    highest_hr: { label: 'Highest avg HR', icon: 'heart', color: 'var(--danger)', bg: 'var(--danger-bg)', unit: 'bpm', format: (v) => `${Math.round(v)} bpm` },
  };

  interface YearData {
    year: number;
    months: { month: number; distance_m: number; duration_s: number; elevation_m: number; calories: number; count: number }[];
    total: { distance_m: number; duration_s: number; elevation_m: number; calories: number; count: number };
  }

  const yearlyData = $derived.by((): YearData[] => {
    if (!volume || volume.monthly.length === 0) return [];
    const byYear = new Map<number, YearData>();
    for (const m of volume.monthly) {
      const [y, mo] = m.month.split('-').map(Number);
      if (!byYear.has(y)) {
        byYear.set(y, { year: y, months: [], total: { distance_m: 0, duration_s: 0, elevation_m: 0, calories: 0, count: 0 } });
      }
      const yd = byYear.get(y)!;
      yd.months.push({ month: mo, distance_m: m.distance_m, duration_s: m.duration_s, elevation_m: m.elevation_m, calories: m.calories, count: m.count });
      yd.total.distance_m += m.distance_m;
      yd.total.duration_s += m.duration_s;
      yd.total.elevation_m += m.elevation_m;
      yd.total.calories += m.calories;
      yd.total.count += m.count;
    }
    return Array.from(byYear.values()).sort((a, b) => b.year - a.year);
  });

  function buildChart() {
    if (!chartContainer || yearlyData.length === 0) return;

    chart?.destroy();
    chart = null;

    const cfg = metricConfig[chartMetric];
    const years = yearlyData.map(y => y.year).sort((a, b) => a - b);
    const currentMonth = new Date().getMonth() + 1;

    const xVals = new Float64Array(MONTH_LABELS.map((_, i) => i));
    const seriesData: Float64Array[] = years.map(year => {
      const yd = yearlyData.find(y => y.year === year);
      const vals = new Float64Array(12);
      if (yd) {
        const maxMonth = year === currentYear ? currentMonth : 12;
        let cumulative = 0;
        for (let m = 0; m < maxMonth; m++) {
          const md = yd.months.find(x => x.month === m + 1);
          cumulative += md ? md[cfg.key] : 0;
          vals[m] = chartMetric === 'time' ? cumulative / 3600 : chartMetric === 'distance' ? cumulative / 1000 : cumulative;
        }
        for (let m = maxMonth; m < 12; m++) vals[m] = NaN;
      } else {
        vals.fill(NaN);
      }
      return vals;
    });

    const plotData: uPlot.AlignedData = [xVals, ...seriesData];

    const seriesColors = years.map((_, i) => YEAR_COLORS[i % YEAR_COLORS.length]);

    chart = new uPlot({
      width: chartContainer.clientWidth,
      height: 280,
      padding: [10, 10, 15, 0],
      cursor: {
        x: {
          formatter: (_u, val) => MONTH_LABELS[val] ?? '',
        },
        points: {
          size: 4,
          stroke: '#ffffff',
          width: 1.5,
        },
      },
      axes: [
        {
          stroke: '#888',
          grid: { show: false },
          values: (_u, ticks) => ticks.map(t => MONTH_LABELS[t] ?? ''),
        },
        {
          stroke: '#888',
          grid: { stroke: '#eee' },
          size: 60,
          values: (_u, ticks) => ticks.map(t => cfg.yFormat(t)),
        },
      ],
      series: [
        {},
        ...years.map((year, i) => ({
          stroke: seriesColors[i],
          width: 2,
          points: { size: 10, stroke: seriesColors[i], fill: '#fff', width: 1.5 },
          label: String(year),
        })),
      ],
      legend: {
        show: true,
        live: false,
      },
      hooks: {
        setCursor: [
          (u: uPlot) => {
            const idx = u.cursor.idx;
            if (idx != null && tooltipEl) {
              const monthLabel = MONTH_LABELS[idx] ?? '';
              let html = `<div style="font-weight:600;margin-bottom:4px">${monthLabel}</div>`;
              for (let si = 0; si < years.length; si++) {
                const val = u.data[si + 1]?.[idx] ?? 0;
                if (!isNaN(val) && val > 0) {
                  const color = seriesColors[si];
                  html += `<div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block"></span>${years[si]}: <strong>${cfg.yFormat(val)}</strong></div>`;
                }
              }
              tooltipEl.innerHTML = html;
              tooltipEl.style.display = 'block';
              let finalLeft = mouseX + 12;
              let finalTop = mouseY - 36;
              const tw = tooltipEl.offsetWidth;
              if (finalLeft + tw > window.innerWidth) finalLeft = mouseX - tw - 12;
              if (finalTop < 0) finalTop = mouseY + 12;
              tooltipEl.style.left = `${finalLeft}px`;
              tooltipEl.style.top = `${finalTop}px`;
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
        statsApi.volume(),
        statsApi.personalRecords(),
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
    if (chartContainer && yearlyData.length > 0 && !loading && chartContainer.clientWidth > 0) {
      buildChart();
      setupChartResize();
    } else if (chart && (yearlyData.length === 0 || loading)) {
      chart.destroy();
      chart = null;
    }
  });

  $effect(() => {
    void chartMetric;
    if (yearlyData.length > 0 && !loading) {
      buildChart();
    }
  });
</script>

<div class="page">
  <div class="page-header">
    <h1>Statistics</h1>
  </div>

  {#if loading}
    <LoadingSpinner />
  {:else if error}
    <ErrorBanner message={error} retry={loadStats} />
  {:else if !volume || (volume.monthly.length === 0 && volume.by_sport.length === 0)}
    <EmptyState icon="eddington" message="No statistics yet. Upload some activities to see your stats here." action="Upload" onAction={() => onNavigate?.('upload')} />
  {:else}
    {#if yearlyData.length > 0}
      <div class="dash-card">
        <div class="card-header">
          <h3>Yearly stats</h3>
          <div class="metric-btns">
            <button class="metric-btn" class:active={chartMetric === 'distance'} onclick={() => chartMetric = 'distance'}>
              <Icon name="distance" size={14} /> Distance
            </button>
            <button class="metric-btn" class:active={chartMetric === 'time'} onclick={() => chartMetric = 'time'}>
              <Icon name="duration" size={14} /> Time
            </button>
            <button class="metric-btn" class:active={chartMetric === 'elevation'} onclick={() => chartMetric = 'elevation'}>
              <Icon name="elevationUp" size={14} /> Elevation
            </button>
          </div>
        </div>
        <div bind:this={chartContainer} class="chart" role="presentation" onmousemove={handleChartMouseMove} onmouseleave={handleChartMouseLeave}></div>
        <div bind:this={tooltipEl} class="chart-tooltip" style="display: none;"></div>

        <div class="yt-table">
          <div class="yt-thead">
            <div class="yt-tr">
              <span class="yt-th">Year</span>
              <span class="yt-th yt-th-num">Dist.</span>
              <span class="yt-th yt-th-num">Prev year</span>
              <span class="yt-th yt-th-num">Elev.</span>
              <span class="yt-th yt-th-num">Prev year</span>
              <span class="yt-th yt-th-num">Moving Time</span>
              <span class="yt-th yt-th-num">Prev year</span>
              <span class="yt-th yt-th-num">Cal.</span>
            </div>
          </div>
          <div class="yt-tbody">
            {#each yearlyData as yd, i}
              {@const prev = yearlyData.find(y => y.year === yd.year - 1)}
              <div class="yt-tr">
                <span class="yt-td yt-td-year">{yd.year}</span>
                <span class="yt-td yt-td-num">{formatKm(yd.total.distance_m)} km</span>
                <span class="yt-td yt-td-num">
                  {#if prev}
                    {@const diff = yd.total.distance_m - prev.total.distance_m}
                    <span class="yt-delta" class:positive={diff >= 0} class:negative={diff < 0}>
                      {diff >= 0 ? '↑' : '↓'} {formatKm(Math.abs(diff))} km
                    </span>
                  {:else}
                    <span class="yt-dash">—</span>
                  {/if}
                </span>
                <span class="yt-td yt-td-num">{Math.round(yd.total.elevation_m).toLocaleString()} m</span>
                <span class="yt-td yt-td-num">
                  {#if prev}
                    {@const diff = yd.total.elevation_m - prev.total.elevation_m}
                    <span class="yt-delta" class:positive={diff >= 0} class:negative={diff < 0}>
                      {diff >= 0 ? '↑' : '↓'} {Math.round(Math.abs(diff)).toLocaleString()} m
                    </span>
                  {:else}
                    <span class="yt-dash">—</span>
                  {/if}
                </span>
                <span class="yt-td yt-td-num">{formatDurationLong(yd.total.duration_s)}</span>
                <span class="yt-td yt-td-num">
                  {#if prev}
                    {@const diff = yd.total.duration_s - prev.total.duration_s}
                    <span class="yt-delta" class:positive={diff >= 0} class:negative={diff < 0}>
                      {diff >= 0 ? '↑' : '↓'} {formatDurationLong(Math.abs(diff))}
                    </span>
                  {:else}
                    <span class="yt-dash">—</span>
                  {/if}
                </span>
                <span class="yt-td yt-td-num">{yd.total.calories.toLocaleString()} cal</span>
              </div>
            {/each}
          </div>
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

    <div class="td-row">
      <TimeDistribution groupBy="weekday" />
      <TimeDistribution groupBy="time_of_day" />
    </div>

    <div class="td-row">
      <HRDistribution />
      <WeeklyChart />
    </div>

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
                <div class="record-value">{meta.format(pr.value)}</div>
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
    width: 100%;
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

  .metric-btns {
    display: flex;
    gap: 4px;
    background: var(--bg, #f5f5f5);
    border-radius: var(--radius-md, 6px);
    padding: 3px;
  }
  .metric-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 12px;
    border: none;
    border-radius: 4px;
    font-family: var(--font-sans);
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
    background: transparent;
    color: var(--text-secondary);
    transition: all 0.15s ease;
  }
  .metric-btn.active {
    background: var(--card-bg, white);
    color: var(--text);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  }
  .metric-btn:hover:not(.active) {
    color: var(--text);
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
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .chart-tooltip :global(strong) {
    font-weight: 600;
    color: var(--text);
  }

  .dash-card {
    margin-bottom: 20px;
  }

  .yt-table {
    margin-top: 16px;
    width: 100%;
  }
  .yt-thead {
    border-bottom: 1px solid var(--border, rgba(0, 0, 0, 0.06));
    padding-bottom: 8px;
  }
  .yt-tr {
    display: grid;
    grid-template-columns: 0.6fr 1fr 1.2fr 1fr 1.2fr 1.1fr 1.3fr 0.9fr;
    align-items: center;
    padding: 6px 0;
    width: 100%;
  }
  .yt-th {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--primary, #3b82f6);
    border-bottom: 2px solid var(--primary, #3b82f6);
    padding-bottom: 4px;
    display: inline-block;
  }
  .yt-th-num {
    text-align: right;
  }
  .yt-tbody .yt-tr {
    border-bottom: 0.5px solid var(--border, rgba(0, 0, 0, 0.04));
  }
  .yt-tbody .yt-tr:last-child {
    border-bottom: none;
  }
  .yt-td {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-primary, var(--text));
  }
  .yt-td-year {
    font-weight: 600;
  }
  .yt-td-num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .yt-delta {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    white-space: nowrap;
  }
  .yt-delta.positive {
    color: #16a34a;
    background: rgba(22, 163, 74, 0.1);
  }
  .yt-delta.negative {
    color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
  }
  .yt-dash {
    color: var(--text-tertiary, #999);
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

  .td-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 28px;
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
  .record-source {
    font-size: 12px;
    font-weight: 400;
    color: var(--primary);
    margin-top: 4px;
  }

  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: var(--font-size-2xl, 22px); }
    .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
    .td-row { grid-template-columns: 1fr; }
    .pr-grid { grid-template-columns: repeat(2, 1fr); }
    .yt-tr { grid-template-columns: 0.5fr 1fr 1.2fr 1fr 1.2fr 1fr 1.3fr 0.8fr; font-size: 11px; }
    .metric-btns { flex-wrap: wrap; }
  }
</style>
