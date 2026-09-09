<script lang="ts">
  import { statsApi, type TimeDistributionItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';

  let { groupBy = 'weekday' }: { groupBy?: 'weekday' | 'time_of_day' } = $props();

  let data = $state<TimeDistributionItem[]>([]);
  let loading = $state(true);

  const PIE_COLORS = ['#3b82f6', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

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

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function formatKm(m: number): string {
    return (m / 1000).toFixed(1);
  }
</script>

{#if !loading && data.length > 0}
  <div class="td-card">
    <div class="td-header">
      <div class="td-title-row">
        <div class="td-icon">
          <Icon name="calendar" size={15} />
        </div>
        <span class="td-title">{groupBy === 'weekday' ? 'Weekday distribution' : 'Time of day distribution'}</span>
      </div>
      <span class="td-total">{total} workouts</span>
    </div>

    <div class="td-content">
      <div class="td-pie-wrapper">
        <div class="td-pie" style="background: {pieGradient}"></div>
        <div class="td-legend">
          {#each data as item, i}
            <div class="td-legend-item">
              <span class="td-legend-dot" style="background: {PIE_COLORS[i % PIE_COLORS.length]}"></span>
              <span class="td-legend-label">{item.group}</span>
              <span class="td-legend-value">{item.count}</span>
            </div>
          {/each}
        </div>
      </div>

      <div class="td-table">
        <div class="td-row td-header-row">
          <span class="td-col td-col-group"></span>
          <span class="td-col td-col-num">#</span>
          <span class="td-col td-col-num">Dist.</span>
          <span class="td-col td-col-num">Elev.</span>
          <span class="td-col td-col-num">Time</span>
        </div>
        {#each data as item, i}
          <div class="td-row" class:td-row-last={i === data.length - 1}>
            <span class="td-col td-col-group">
              <span class="td-dot" style="background: {PIE_COLORS[i % PIE_COLORS.length]}"></span>
              {item.group}
            </span>
            <span class="td-col td-col-num">{item.count}</span>
            <span class="td-col td-col-num">{formatKm(item.distance_m)} km</span>
            <span class="td-col td-col-num">{item.elevation_gain > 0 ? `${item.elevation_gain.toFixed(0)} m` : '-'}</span>
            <span class="td-col td-col-num">{formatDuration(item.duration_s)}</span>
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
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .td-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .td-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .td-icon {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: var(--primary-bg, color-mix(in srgb, var(--primary) 10%, transparent));
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary);
  }
  .td-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
  }
  .td-total {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-semibold, 600);
    color: var(--text-tertiary, #999);
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 6px;
    background: var(--bg, #f5f5f5);
  }

  .td-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .td-pie-wrapper {
    display: flex;
    align-items: center;
    gap: 24px;
  }
  .td-pie {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .td-legend {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .td-legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: var(--font-size-sm, 12px);
  }
  .td-legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .td-legend-label {
    color: var(--text-secondary, #666);
    min-width: 50px;
  }
  .td-legend-value {
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-primary, var(--text));
    font-variant-numeric: tabular-nums;
  }

  .td-table {
    display: flex;
    flex-direction: column;
  }
  .td-row {
    display: grid;
    grid-template-columns: 1fr 40px 70px 60px 70px;
    align-items: center;
    padding: 7px 0;
    border-bottom: 0.5px solid var(--border, rgba(0, 0, 0, 0.06));
  }
  .td-header-row {
    padding-bottom: 6px;
  }
  .td-header-row .td-col {
    font-size: var(--font-size-xs, 10px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-tertiary, #999);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .td-row-last {
    border-bottom: none;
  }

  .td-col {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-primary, var(--text));
  }
  .td-col-group {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: var(--font-weight-medium, 500);
  }
  .td-col-num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .td-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
</style>
