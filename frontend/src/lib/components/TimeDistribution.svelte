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

  const pieGradient = $derived.by(() => {
    if (data.length === 0 || total === 0) return '';
    let acc = 0;
    const stops: string[] = [];
    for (let i = 0; i < data.length; i++) {
      const pct = (data[i].count / total) * 100;
      const color = PIE_COLORS[i % PIE_COLORS.length];
      stops.push(`${color} ${acc}% ${acc + pct}%`);
      acc += pct;
    }
    return `conic-gradient(${stops.join(', ')})`;
  });

  const pieLabels = $derived.by(() => {
    if (data.length === 0 || total === 0) return [];
    let acc = 0;
    return data.map((item, i) => {
      const pct = (item.count / total) * 100;
      const midAngle = acc + (pct / 2);
      acc += pct;
      const rad = ((midAngle - 90) * Math.PI) / 180;
      const r = 47;
      const x = 50 + r * Math.cos(rad);
      const y = 50 + r * Math.sin(rad);
      return { ...item, x, y, pct, color: PIE_COLORS[i % PIE_COLORS.length] };
    });
  });

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
      <div class="td-pie-container">
        <div class="td-pie" style="background: {pieGradient}"></div>
        {#each pieLabels as label}
          <div
            class="td-pie-label"
            style="left: {label.x}%; top: {label.y}%; transform: translate(-50%, -50%)"
          >
            <span class="td-pie-label-name">{label.group}.</span>
            <span class="td-pie-label-pct">{label.pct.toFixed(2)}%</span>
          </div>
        {/each}
      </div>
    </div>

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
    padding: 24px 0 8px;
  }
  .td-pie-container {
    position: relative;
    width: 260px;
    height: 260px;
  }
  .td-pie {
    position: absolute;
    top: 20px;
    left: 20px;
    width: 220px;
    height: 220px;
    border-radius: 50%;
  }
  .td-pie-label {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
    pointer-events: none;
    white-space: nowrap;
    transform: translate(-50%, -50%);
  }
  .td-pie-label-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary, var(--text));
  }
  .td-pie-label-pct {
    font-size: 10px;
    font-weight: 400;
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
