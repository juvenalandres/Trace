<script lang="ts">
  import Icon from './Icon.svelte';
  import type { ActivitySummary } from '../api/types';

  interface Props {
    activities: ActivitySummary[];
    onRowClick?: (id: number) => void;
  }

  let { activities, onRowClick }: Props = $props();

  function formatDistance(m: number | null): string {
    if (m === null) return '-';
    return (m / 1000).toFixed(1);
  }

  function formatDuration(s: number | null): string {
    if (s === null) return '-';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  function formatPace(speed: number | null): string {
    if (speed === null || speed === 0) return '-';
    const pace = 1000 / speed / 60;
    const min = Math.floor(pace);
    const sec = Math.floor((pace - min) * 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  }

  function sportIcon(type: string): string {
    const map: Record<string, string> = { run: 'activity', ride: 'ride', swim: 'swim', hike: 'hike', walk: 'activity' };
    return map[type] || 'activity';
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }
</script>

<div class="activity-table">
  <table>
    <thead>
      <tr>
        <th class="col-sport"></th>
        <th class="col-name">Activity</th>
        <th class="col-date">Date</th>
        <th class="col-num">Distance</th>
        <th class="col-num">Duration</th>
        <th class="col-num">Pace</th>
        <th class="col-num">Elevation</th>
      </tr>
    </thead>
    <tbody>
      {#each activities as a}
        <tr onclick={() => onRowClick?.(a.id)} class="clickable">
          <td class="col-sport">
            <span class="sport-badge">
              <Icon name={sportIcon(a.sport_type)} size={14} />
            </span>
          </td>
          <td class="col-name">
            <span class="name">{a.name}</span>
            <span class="sport-type">{a.sport_type}</span>
          </td>
          <td class="col-date">{formatDate(a.start_time)}</td>
          <td class="col-num">{formatDistance(a.distance_m)}<span class="unit">km</span></td>
          <td class="col-num">{formatDuration(a.duration_s)}</td>
          <td class="col-num">{formatPace(a.avg_speed)}<span class="unit">/km</span></td>
          <td class="col-num">{a.elevation_gain !== null ? a.elevation_gain : '-'}<span class="unit">m</span></td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .activity-table {
    overflow-x: auto;
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: var(--card-padding, 16px);
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th {
    text-align: left;
    padding: 8px 0;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 0.5px solid var(--border);
  }
  td {
    padding: 12px 0;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    border-bottom: 0.5px solid var(--border);
    vertical-align: middle;
  }
  tr:last-child td {
    border-bottom: none;
  }
  .clickable {
    cursor: pointer;
  }
  .clickable:hover {
    background: var(--hover);
  }
  .col-sport {
    width: 40px;
    text-align: center;
  }
  .sport-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--primary);
  }
  .col-name {
    min-width: 150px;
  }
  .name {
    display: block;
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
    line-height: 1.3;
  }
  .sport-type {
    display: block;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    text-transform: capitalize;
  }
  .col-date {
    color: var(--text-secondary);
    white-space: nowrap;
    text-align: right;
  }
  .col-num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  th.col-num {
    text-align: right;
  }
  .unit {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    margin-left: 3px;
    font-weight: var(--font-weight-regular, 400);
  }
</style>
