<script lang="ts">
  import { statsApi, type TimeDistributionItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';

  let { groupBy = 'weekday' }: { groupBy?: 'weekday' | 'time_of_day' } = $props();

  let data = $state<TimeDistributionItem[]>([]);
  let loading = $state(true);

  const PIE_COLORS = ['#3b82f6', '#8bc34a', '#ffc107', '#ef5350', '#26a69a', '#ab47bc', '#ec407a'];

  async function loadData() {
    loading = true;
    try {
      data = await statsApi.timeDistribution(groupBy);
    } catch (e) {
      console.error('Failed to load time distribution', e);
      data = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void groupBy;
    loadData();
  });

  const total = $derived(data.reduce((s, d) => s + d.count, 0));

  const slices = $derived.by(() => {
    if (data.length === 0 || total === 0) return [];
    const cx = 110, cy = 110, r = 100;
    let acc = 0;
    return data.map((item, i) => {
      const pct = (item.count / total) * 100;
      const startAngle = (acc / 100) * 2 * Math.PI - Math.PI / 2;
      acc += pct;
      const endAngle = (acc / 100) * 2 * Math.PI - Math.PI / 2;
      const largeArc = pct > 50 ? 1 : 0;
      const x1 = cx + r * Math.cos(startAngle);
      const y1 = cy + r * Math.sin(startAngle);
      const x2 = cx + r * Math.cos(endAngle);
      const y2 = cy + r * Math.sin(endAngle);
      const d = `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${largeArc},1 ${x2},${y2} Z`;
      return { ...item, d, pct, color: PIE_COLORS[i % PIE_COLORS.length] };
    });
  });

  let hoveredIdx = $state<number | null>(null);
  let tooltipX = $state(0);
  let tooltipY = $state(0);

  function handleMouseMove(e: MouseEvent) {
    tooltipX = e.clientX;
    tooltipY = e.clientY;
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

  function formatKm(m: number): string {
    return Math.round(m / 1000).toLocaleString();
  }
</script>

{#if !loading && data.length > 0}
  <div class="td-card">
    <div class="td-header">
      <span class="td-title">Stats per {groupBy === 'weekday' ? 'weekday' : 'time of day'}</span>
    </div>

    <div class="td-pie-section">
      <svg viewBox="0 0 220 220" class="td-pie-svg" onmousemove={handleMouseMove}>
        {#each slices as slice, i}
          <path
            d={slice.d}
            fill={slice.color}
            stroke="var(--card-bg, white)"
            stroke-width="2"
            class="td-pie-slice"
            class:hovered={hoveredIdx === i}
            onmouseenter={() => hoveredIdx = i}
            onmouseleave={() => hoveredIdx = null}
            onmousemove={handleMouseMove}
          />
        {/each}
      </svg>
    </div>

    {#if hoveredIdx !== null && slices[hoveredIdx]}
      <div class="td-tooltip" style="left: {tooltipX}px; top: {tooltipY}px">
        <span class="td-tooltip-name">{slices[hoveredIdx].group}</span>
        <span class="td-tooltip-pct">{slices[hoveredIdx].pct.toFixed(1)}%</span>
      </div>
    {/if}

    <div class="td-table">
      <div class="td-thead">
        <div class="td-tr">
          <span class="td-th td-th-day"></span>
          <span class="td-th td-th-num"># Workouts</span>
          <span class="td-th td-th-num">Dist.</span>
          <span class="td-th td-th-num">Elev.</span>
          <span class="td-th td-th-num">Moving Time</span>
        </div>
      </div>
      <div class="td-tbody">
        {#each data as item, i}
          <div class="td-tr">
            <span class="td-td td-td-day">
              <span class="td-color-dot" style="background: {PIE_COLORS[i % PIE_COLORS.length]}"></span>
              {item.group}.
            </span>
            <span class="td-td td-td-num">{item.count}</span>
            <span class="td-td td-td-num">
              {item.count > 0 ? Math.round(item.distance_m / item.count / 1000) : 0}km avg / {formatKm(item.distance_m)}km total
            </span>
            <span class="td-td td-td-num">{Math.round(item.elevation_gain).toLocaleString()} m</span>
            <span class="td-td td-td-num">{formatDurationLong(item.duration_s)}</span>
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .td-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .td-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .td-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text);
  }

  .td-pie-section {
    display: flex;
    justify-content: center;
    padding: 8px 0;
  }
  .td-pie-svg {
    width: 200px;
    height: 200px;
    cursor: pointer;
  }
  .td-pie-slice {
    transition: opacity 0.15s ease, transform 0.15s ease;
    transform-origin: 110px 110px;
  }
  .td-pie-slice:hover,
  .td-pie-slice.hovered {
    opacity: 0.85;
    transform: scale(1.03);
  }

  .td-tooltip {
    position: fixed;
    pointer-events: none;
    z-index: 1000;
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    display: flex;
    gap: 8px;
    align-items: center;
    transform: translate(12px, -50%);
    white-space: nowrap;
  }
  .td-tooltip-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }
  .td-tooltip-pct {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary, #666);
  }

  .td-table {
    display: flex;
    flex-direction: column;
  }
  .td-thead {
    border-bottom: 1px solid var(--border, rgba(0, 0, 0, 0.06));
    padding-bottom: 8px;
  }
  .td-tr {
    display: grid;
    grid-template-columns: 70px 80px 1fr 80px 120px;
    align-items: center;
    padding: 6px 0;
  }
  .td-th {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--primary, #3b82f6);
    border-bottom: 2px solid var(--primary, #3b82f6);
    padding-bottom: 4px;
    display: inline-block;
  }
  .td-th-num {
    text-align: right;
  }
  .td-tbody .td-tr {
    border-bottom: 0.5px solid var(--border, rgba(0, 0, 0, 0.04));
  }
  .td-tbody .td-tr:last-child {
    border-bottom: none;
  }

  .td-td {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-primary, var(--text));
  }
  .td-td-day {
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .td-td-num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .td-color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
</style>
