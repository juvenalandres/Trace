<script lang="ts">
  import type { SportBreakdown } from '../api/types';

  interface Props {
    data: SportBreakdown[];
  }

  let { data }: Props = $props();

  const maxDistance = $derived(Math.max(...data.map(d => d.distance_m), 1));

  function sportEmoji(type: string): string {
    const map: Record<string, string> = { run: '🏃', ride: '🚴', swim: '🏊', hike: '🥾', walk: '🚶' };
    return map[type] || '⚡';
  }

  function formatKm(m: number): string {
    return (m / 1000).toFixed(1);
  }

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }
</script>

<div class="sport-breakdown">
  {#each data as sport}
    <div class="sport-row">
      <div class="sport-label">
        <span class="emoji">{sportEmoji(sport.sport_type)}</span>
        <span class="name">{sport.sport_type}</span>
        <span class="count">{sport.activity_count}</span>
      </div>
      <div class="bar-container">
        <div class="bar" style="width: {(sport.distance_m / maxDistance) * 100}%"></div>
      </div>
      <div class="stats">
        <span>{formatKm(sport.distance_m)} km</span>
        <span class="duration">{formatDuration(sport.duration_s)}</span>
      </div>
    </div>
  {/each}
</div>

<style>
  .sport-breakdown {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-family: var(--font-sans);
  }
  .sport-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .sport-label {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 120px;
  }
  .emoji {
    font-size: 16px;
  }
  .name {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    text-transform: capitalize;
  }
  .count {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .bar-container {
    flex: 1;
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
  }
  .bar {
    height: 100%;
    background: var(--primary);
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .stats {
    display: flex;
    gap: 12px;
    min-width: 160px;
    justify-content: flex-end;
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .duration {
    color: var(--text-secondary);
  }
  @media (max-width: 768px) {
    .sport-row { flex-wrap: wrap; gap: 6px; }
    .sport-label { min-width: auto; flex: 1; }
    .bar-container { order: 3; flex-basis: 100%; }
    .stats { min-width: auto; gap: 8px; font-size: var(--font-size-xs, 11px); }
  }
</style>
