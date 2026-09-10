<script lang="ts">
  import { onMount } from 'svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { statsApi } from '$lib/api/types';
  import type { VolumeResponse } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';

  let chartContainer = $state<HTMLDivElement | null>(null);
  let chart: uPlot | null = null;
  let tooltipEl = $state<HTMLDivElement | null>(null);
  let mouseX = 0;
  let mouseY = 0;
  let resizeObserver: ResizeObserver | null = null;
  let volume = $state<VolumeResponse | null>(null);
  let loading = $state(true);

  let metric = $state<'distance' | 'time' | 'elevation'>('distance');

  const metricConfig: Record<string, { label: string; unit: string; key: string; yFormat: (v: number) => string }> = {
    distance: { label: 'Distance', unit: 'km', key: 'distance_m', yFormat: (v: number) => `${Math.round(v)} km` },
    time: { label: 'Time', unit: 'h', key: 'duration_s', yFormat: (v: number) => `${Math.round(v)}h` },
    elevation: { label: 'Elevation', unit: 'm', key: 'elevation_m', yFormat: (v: number) => `${Math.round(v)} m` },
  };

  const LINE_COLOR = '#ef4444';

  async function loadData() {
    loading = true;
    try {
      volume = await statsApi.volume();
    } catch (e) {
      console.error('Failed to load volume data', e);
    } finally {
      loading = false;
    }
  }

  function buildChart() {
    if (!chartContainer || !volume || volume.monthly.length === 0) return;

    chart?.destroy();
    chart = null;

    const cfg = metricConfig[metric];
    const sorted = [...volume.monthly].sort((a, b) => a.month.localeCompare(b.month));
    const last12 = sorted.slice(-12);

    const xVals = new Float64Array(last12.length);
    const vals = new Float64Array(last12.length);
    const labels: string[] = [];

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    for (let i = 0; i < last12.length; i++) {
      xVals[i] = i;
      const raw = (last12[i] as Record<string, number>)[cfg.key] ?? 0;
      vals[i] = metric === 'time' ? raw / 3600 : metric === 'distance' ? raw / 1000 : raw;
      const [y, m] = last12[i].month.split('-').map(Number);
      labels.push(`${months[m - 1]} ${y}`);
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
          size: 40,
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
              const monthLabel = labels[idx] ?? '';
              const val = u.data[1]?.[idx] ?? 0;
              if (!isNaN(val)) {
                tooltipEl.innerHTML = `<div style="font-weight:600;margin-bottom:2px">${monthLabel}</div><div>${cfg.yFormat(val)}</div>`;
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
    if (chartContainer && volume && volume.monthly.length > 0 && !loading && chartContainer.clientWidth > 0) {
      buildChart();
      setupResize();
    }
  });

  $effect(() => {
    void metric;
    if (volume && volume.monthly.length > 0 && !loading) {
      buildChart();
    }
  });
</script>

{#if !loading && volume && volume.monthly.length > 0}
  <div class="mc-card">
    <div class="card-header">
      <h3>Monthly stats</h3>
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
    <div class="mc-chart-wrap">
      <div bind:this={chartContainer} class="mc-chart" role="presentation" onmousemove={handleMouseMove} onmouseleave={handleMouseLeave}></div>
      <div bind:this={tooltipEl} class="mc-tooltip" style="display: none;"></div>
    </div>
  </div>
{/if}

<style>
  .mc-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
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

  .mc-chart-wrap {
    position: relative;
  }

  .mc-chart {
    width: 100%;
    height: 280px;
  }

  .mc-tooltip {
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
