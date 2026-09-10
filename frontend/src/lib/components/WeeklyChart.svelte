<script lang="ts">
  import { onMount } from 'svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { statsApi, type WeeklyStatsItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';

  let chartContainer = $state<HTMLDivElement | null>(null);
  let chart: uPlot | null = null;
  let tooltipEl = $state<HTMLDivElement | null>(null);
  let mouseX = 0;
  let mouseY = 0;
  let resizeObserver: ResizeObserver | null = null;
  let weeklyData = $state<WeeklyStatsItem[]>([]);
  let loading = $state(true);

  let metric = $state<'distance' | 'time' | 'elevation'>('distance');

  const metricConfig: Record<string, { label: string; unit: string; key: keyof WeeklyStatsItem; yFormat: (v: number) => string }> = {
    distance: { label: 'Distance', unit: 'km', key: 'distance_m', yFormat: (v: number) => `${Math.round(v)} km` },
    time: { label: 'Time', unit: 'h', key: 'duration_s', yFormat: (v: number) => `${Math.round(v)}h` },
    elevation: { label: 'Elevation', unit: 'm', key: 'elevation_m', yFormat: (v: number) => `${Math.round(v)} m` },
  };

  const LINE_COLOR = '#ef4444';

  async function loadData() {
    loading = true;
    try {
      weeklyData = await statsApi.weeklyStats(16);
    } catch (e) {
      console.error('Failed to load weekly stats', e);
    } finally {
      loading = false;
    }
  }

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr + 'T00:00:00');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[d.getMonth()]} ${d.getDate()}`;
  }

  function formatShortLabel(dateStr: string): string {
    const d = new Date(dateStr + 'T00:00:00');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[d.getMonth()]} ${d.getDate()}`;
  }

  function buildChart() {
    if (!chartContainer || weeklyData.length === 0) return;

    chart?.destroy();
    chart = null;

    const cfg = metricConfig[metric];
    const xVals = new Float64Array(weeklyData.length);
    const vals = new Float64Array(weeklyData.length);
    const labels: string[] = [];

    for (let i = 0; i < weeklyData.length; i++) {
      xVals[i] = i;
      const raw = weeklyData[i][cfg.key] as number;
      vals[i] = metric === 'time' ? raw / 3600 : metric === 'distance' ? raw / 1000 : raw;
      labels.push(formatShortLabel(weeklyData[i].week_start));
    }

    const plotData: uPlot.AlignedData = [xVals, vals];

    chart = new uPlot({
      width: chartContainer.clientWidth,
      height: 280,
      padding: [10, 10, 15, 0],
      cursor: {
        x: {
          formatter: (_u, val) => labels[val] ?? '',
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
          values: (_u, ticks) => ticks.map(t => labels[t] ?? ''),
          size: 30,
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
        {
          stroke: LINE_COLOR,
          width: 2,
          points: { size: 5, stroke: LINE_COLOR, fill: '#fff', width: 1.5 },
          label: cfg.label,
        },
      ],
      legend: { show: false },
      hooks: {
        setCursor: [
          (u: uPlot) => {
            const idx = u.cursor.idx;
            if (idx != null && tooltipEl) {
              const weekLabel = labels[idx] ?? '';
              const val = u.data[1]?.[idx] ?? 0;
              if (!isNaN(val)) {
                tooltipEl.innerHTML = `<div style="font-weight:600;margin-bottom:2px">${weekLabel}</div><div>${cfg.yFormat(val)}</div>`;
                tooltipEl.style.display = 'block';
                let finalLeft = mouseX + 12;
                let finalTop = mouseY - 36;
                const tw = tooltipEl.offsetWidth;
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

  function handleMouseMove(e: MouseEvent) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }

  function handleMouseLeave() {
    if (tooltipEl) tooltipEl.style.display = 'none';
  }

  function setupResize() {
    if (!chartContainer) return;
    resizeObserver?.disconnect();
    resizeObserver = new ResizeObserver(() => {
      if (chart && chartContainer) {
        chart.setSize({ width: chartContainer.clientWidth, height: chart.height });
      }
    });
    resizeObserver.observe(chartContainer);
  }

  onMount(async () => {
    await loadData();
    return () => {
      resizeObserver?.disconnect();
      chart?.destroy();
    };
  });

  $effect(() => {
    if (chartContainer && weeklyData.length > 0 && !loading && chartContainer.clientWidth > 0) {
      buildChart();
      setupResize();
    }
  });

  $effect(() => {
    void metric;
    if (weeklyData.length > 0 && !loading) {
      buildChart();
    }
  });
</script>

{#if !loading && weeklyData.length > 0}
  <div class="wc-card">
    <div class="card-header">
      <h3>Weekly stats</h3>
      <div class="metric-btns">
        <button class="metric-btn" class:active={metric === 'distance'} onclick={() => metric = 'distance'}>
          <Icon name="distance" size={14} /> Distance
        </button>
        <button class="metric-btn" class:active={metric === 'time'} onclick={() => metric = 'time'}>
          <Icon name="duration" size={14} /> Time
        </button>
        <button class="metric-btn" class:active={metric === 'elevation'} onclick={() => metric = 'elevation'}>
          <Icon name="elevationUp" size={14} /> Elevation
        </button>
      </div>
    </div>
    <div class="wc-chart-wrap">
      <div bind:this={chartContainer} class="wc-chart" role="presentation" onmousemove={handleMouseMove} onmouseleave={handleMouseLeave}></div>
      <div bind:this={tooltipEl} class="wc-tooltip" style="display: none;"></div>
    </div>
  </div>
{/if}

<style>
  .wc-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 380px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }

  .card-header h3 {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    margin: 0;
  }

  .metric-btns {
    display: flex;
    gap: 4px;
    padding: 3px;
    border-radius: 8px;
    background: var(--bg, #f5f5f5);
  }

  .metric-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-secondary, #666);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .metric-btn.active {
    background: var(--card-bg, var(--surface));
    color: var(--text);
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }

  .metric-btn:hover:not(.active) {
    color: var(--text);
  }

  .wc-chart-wrap {
    position: relative;
    flex: 1;
  }

  .wc-chart {
    width: 100%;
    height: 280px;
  }

  .wc-tooltip {
    position: fixed;
    pointer-events: none;
    z-index: 1000;
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    font-size: 13px;
    color: var(--text);
  }
</style>
