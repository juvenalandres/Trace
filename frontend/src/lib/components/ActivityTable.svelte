<script lang="ts">
  import type { ActivitySummary } from '../api/types';

  interface Props {
    activities: ActivitySummary[];
    onRowClick?: (id: number) => void;
  }

  let { activities, onRowClick }: Props = $props();

  type SortKey = 'name' | 'date' | 'sport' | 'distance' | 'duration' | 'pace' | 'elevation';
  let sortKey = $state<SortKey>('date');
  let sortDir = $state<'asc' | 'desc'>('desc');

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortKey = key;
      sortDir = key === 'date' ? 'desc' : 'asc';
    }
  }

  function sortVal(a: ActivitySummary, key: SortKey): number | string {
    switch (key) {
      case 'name': return a.name?.toLowerCase() ?? '';
      case 'date': return a.start_time;
      case 'sport': return a.sport_type ?? '';
      case 'distance': return a.distance_m ?? 0;
      case 'duration': return a.duration_s ?? 0;
      case 'pace': return a.avg_speed ?? 0;
      case 'elevation': return a.elevation_gain ?? -1;
    }
  }

  let sorted = $derived([...activities].sort((a, b) => {
    const va = sortVal(a, sortKey);
    const vb = sortVal(b, sortKey);
    const cmp = va < vb ? -1 : va > vb ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  }));

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

  function formatSpeed(speed: number | null): string {
    if (speed === null) return '-';
    return (speed * 3.6).toFixed(1);
  }

  function relativeDate(iso: string): string {
    const d = new Date(iso);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const diff = Math.round((today.getTime() - target.getTime()) / 86400000);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Yesterday';
    if (diff < 7) return d.toLocaleDateString('en-GB', { weekday: 'long' });
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  }

  function fullDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  }

  function timeOfDay(iso: string): string {
    return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  }

  let allRuns = $derived(activities.length > 0 && activities.every(a => a.sport_type === 'run'));
  let paceHeader = $derived(allRuns ? 'Pace' : 'Speed');

  const sportMeta: Record<string, { label: string; color: string }> = {
    run:  { label: 'Run',  color: '#22c55e' },
    ride: { label: 'Ride', color: '#3b82f6' },
    swim: { label: 'Swim', color: '#06b6d4' },
    hike: { label: 'Hike', color: '#f97316' },
    walk: { label: 'Walk', color: '#f59e0b' },
  };

  let columns = $derived<{ key: SortKey; label: string; sortable: boolean }[]>([
    { key: 'sport', label: '', sortable: true },
    { key: 'name', label: 'Activity', sortable: true },
    { key: 'date', label: 'Date', sortable: true },
    { key: 'distance', label: 'Distance', sortable: true },
    { key: 'duration', label: 'Duration', sortable: true },
    { key: 'pace', label: paceHeader, sortable: true },
    { key: 'elevation', label: 'Elevation', sortable: true },
  ]);
</script>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        {#each columns as col (col.key)}
          <th
            class="col-{col.key}"
            class:sortable={col.sortable}
            class:active={sortKey === col.key}
            class:asc={sortKey === col.key && sortDir === 'asc'}
            onclick={() => toggleSort(col.key)}
          >
            {col.label}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each sorted as a (a.id)}
        {@const meta = sportMeta[a.sport_type] ?? { label: a.sport_type, color: '#8b5cf6' }}
        <tr onclick={() => onRowClick?.(a.id)} class="clickable">
          <td class="col-sport">
            <span class="sport-pill" style="background: {meta.color}18; color: {meta.color};">
              {meta.label}
            </span>
          </td>
          <td class="col-name">
            <span class="name">{a.name}</span>
            <span class="time">{timeOfDay(a.start_time)}</span>
          </td>
          <td class="col-date" title={fullDate(a.start_time)}>{relativeDate(a.start_time)}</td>
          <td class="col-num">{formatDistance(a.distance_m)}<span class="unit">km</span></td>
          <td class="col-num">{formatDuration(a.duration_s)}</td>
          <td class="col-num">{a.sport_type === 'run' ? formatPace(a.avg_speed) : formatSpeed(a.avg_speed)}<span class="unit">{a.sport_type === 'run' ? '/km' : 'km/h'}</span></td>
          <td class="col-num">{a.elevation_gain !== null ? a.elevation_gain : '-'}<span class="unit">m</span></td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .table-wrap {
    overflow-x: auto;
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  thead {
    position: sticky;
    top: 0;
    z-index: 1;
  }
  th {
    text-align: left;
    padding: 10px 16px;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-semibold, 600);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    user-select: none;
    white-space: nowrap;
  }
  th.sortable { cursor: pointer; transition: color .15s; }
  th.sortable:hover { color: var(--text); }
  th.active { color: var(--text); }
  th.sortable::after {
    content: '';
    display: inline-block;
    width: 0; height: 0;
    margin-left: 5px;
    vertical-align: middle;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid var(--border);
    opacity: 0;
    transition: opacity .15s;
  }
  th.sortable:hover::after { opacity: 0.5; }
  th.active::after { opacity: 1; }
  th.asc::after {
    border-top: none;
    border-bottom: 5px solid var(--text);
  }
  th.desc::after {
    border-bottom: none;
    border-top: 5px solid var(--text);
  }
  td {
    padding: 14px 16px;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    border-bottom: 0.5px solid var(--border);
    vertical-align: middle;
  }
  tbody tr:last-child td {
    border-bottom: none;
  }
  .clickable {
    cursor: pointer;
    transition: background .12s ease;
  }
  .clickable:hover td {
    background: var(--hover);
  }

  .col-sport {
    width: 72px;
    padding-right: 0;
  }
  .sport-pill {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.02em;
    line-height: 1.3;
  }
  .col-name {
    min-width: 160px;
  }
  .name {
    display: block;
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
    line-height: 1.3;
  }
  .time {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    font-weight: var(--font-weight-regular, 400);
  }
  .col-date {
    color: var(--text-secondary);
    white-space: nowrap;
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

  @media (max-width: 640px) {
    .sport-pill { font-size: 10px; padding: 2px 8px; }
    th, td { padding: 10px 10px; }
    .col-date { display: none; }
  }
</style>
