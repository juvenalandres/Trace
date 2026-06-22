<script lang="ts">
  import { onMount } from 'svelte';
  import { activitiesApi, zonesApi, gearApi } from '$lib/api/types';
  import type { Activity, UserZone, Gear } from '$lib/api/types';
  import StatCard from '$lib/components/StatCard.svelte';
  import StatRow from '$lib/components/StatRow.svelte';
  import RouteChartPanel from '$lib/components/RouteChartPanel.svelte';
  import HRZones from '$lib/components/HRZones.svelte';
  import PowerZones from '$lib/components/PowerZones.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import SegmentCreateModal from '$lib/components/SegmentCreateModal.svelte';

  interface Props {
    activityId: number;
    onBack?: () => void;
  }

  let { activityId, onBack }: Props = $props();

  let activity = $state<Activity | null>(null);
  let loading = $state(true);
  let error = $state('');

  let showEdit = $state(false);
  let showDelete = $state(false);
  let editName = $state('');
  let editSportType = $state('');
  let editNotes = $state('');
  let editRpe = $state('');
  let saving = $state(false);

  let hrZone = $state<UserZone | null>(null);
  let powerZone = $state<UserZone | null>(null);
  let gearList = $state<Gear[]>([]);
  let editGearId = $state<number | null>(null);
  let showSegmentModal = $state(false);

  function sportIcon(type: string): string {
    const map: Record<string, string> = { run: 'activity', ride: 'ride', swim: 'swim', hike: 'hike', walk: 'activity' };
    return map[type] || 'activity';
  }

  function zoneToRanges(zone: UserZone | null): { min: number; max: number }[] | undefined {
    if (!zone) return undefined;
    const ranges: { min: number; max: number }[] = [];
    for (let i = 1; i <= 5; i++) {
      const min = zone[`zone_${i}_min` as keyof UserZone] as number | null;
      const max = zone[`zone_${i}_max` as keyof UserZone] as number | null;
      if (min != null && max != null) {
        ranges.push({ min, max });
      }
    }
    return ranges.length > 0 ? ranges : undefined;
  }

  function formatKm(m: number | null): string {
    if (m === null) return '-';
    return (m / 1000).toFixed(2);
  }

  function formatDuration(s: number | null): string {
    if (s === null) return '-';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  function formatSpeed(speed: number | null): string {
    if (speed === null) return '-';
    return (speed * 3.6).toFixed(1);
  }

  function formatPace(speed: number | null): string {
    if (speed === null || speed === 0) return '-';
    const pace = 1000 / speed / 60;
    const min = Math.floor(pace);
    const sec = Math.floor((pace - min) * 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleString('en-GB', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  function openEdit() {
    if (!activity) return;
    editName = activity.name;
    editSportType = activity.sport_type;
    editNotes = activity.notes ?? '';
    editRpe = activity.rpe?.toString() ?? '';
    editGearId = activity.gear_id ?? null;
    showEdit = true;
    if (gearList.length === 0) {
      gearApi.list().then(all => { gearList = all.filter(g => !g.retired); }).catch(() => {});
    }
  }

  async function saveEdit() {
    if (!activity) return;
    saving = true;
    try {
      const update: Record<string, unknown> = {
        name: editName,
        sport_type: editSportType,
        notes: editNotes || undefined,
        rpe: editRpe ? parseInt(editRpe) : undefined,
      };
      if (editGearId !== (activity.gear_id ?? null)) {
        update.gear_id = editGearId;
      }
      await activitiesApi.update(activity.id, update as Parameters<typeof activitiesApi.update>[1]);
      activity = await activitiesApi.get(activityId);
      showEdit = false;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save';
    } finally {
      saving = false;
    }
  }

  async function deleteActivity() {
    if (!activity) return;
    try {
      await activitiesApi.delete(activity.id);
      onBack?.();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete';
    }
  }

  async function load() {
    loading = true;
    error = '';
    try {
      const [act, zones] = await Promise.all([
        activitiesApi.get(activityId),
        zonesApi.list().catch(() => []),
      ]);
      activity = act;
      hrZone = zones.find(z => z.zone_type === 'hr') ?? null;
      powerZone = zones.find(z => z.zone_type === 'power') ?? null;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load activity';
    } finally {
      loading = false;
    }
  }

  onMount(load);
</script>

<div class="activity-detail">
  <div class="top-bar">
    <button class="back-btn" onclick={onBack}>
      <Icon name="chevronLeft" size={16} />
      Back
    </button>
    {#if activity}
      <div class="actions">
        <button class="btn btn-outline" onclick={() => showSegmentModal = true} title="Create a segment from this activity's route">
          <Icon name="plus" size={16} />
          Create Segment
        </button>
        <button class="btn btn-outline" onclick={openEdit}>
          <Icon name="segments" size={16} />
          Edit
        </button>
        <button class="btn btn-danger" onclick={() => showDelete = true}>
          <Icon name="logout" size={16} />
          Delete
        </button>
      </div>
    {/if}
  </div>

  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if activity}
    <div class="header">
      <div class="title-row">
        <span class="sport-icon">
          <Icon name={sportIcon(activity.sport_type)} size={24} />
        </span>
        <h1>{activity.name}</h1>
      </div>
      <div class="meta">{formatDate(activity.start_time)} · {activity.sport_type}</div>
    </div>

    <div class="stat-grid">
      <StatCard label="Distance" value={formatKm(activity.stats?.distance_m ?? null)} unit="km" icon="distance" color="#3b82f6" bg="#3b82f620" />
      <StatCard label="Duration" value={formatDuration(activity.stats?.duration_s ?? null)} icon="duration" color="#14b8a6" bg="#14b8a620" />
      <StatCard label="Avg Speed" value={formatSpeed(activity.stats?.avg_speed ?? null)} unit="km/h" icon="speed" color="#f97316" bg="#f9731620" />
      <StatCard label="Elevation" value={activity.stats?.elevation_gain != null ? +activity.stats.elevation_gain.toFixed(1) : '-'} unit="m" icon="elevationUp" color="#f59e0b" bg="#f59e0b20" />
    </div>

    <div class="other-stats">
      <div class="stats-grid">
        <StatRow label="Max Speed" value={formatSpeed(activity.stats?.max_speed ?? null)} unit="km/h" />
        <StatRow label="Avg HR" value={activity.stats?.avg_hr ?? '-'} unit="bpm" />
        <StatRow label="Avg Power" value={activity.stats?.avg_power ?? '-'} unit="W" />
        <StatRow label="Avg Cadence" value={activity.stats?.avg_cadence ?? '-'} unit="spm" />
        <StatRow label="Calories" value={activity.stats?.calories ?? '-'} unit="kcal" />
        <StatRow label="Device" value={activity.source} />
      </div>
    </div>

    {#if activity.stats?.polyline && activity.stats?.simplified_time_series}
      <div class="section">
        <h2>Route</h2>
        <RouteChartPanel
          polyline={activity.stats.polyline}
          timeSeries={activity.stats.simplified_time_series}
          sportType={activity.sport_type}
        />
      </div>
    {/if}

    {#if activity.stats?.simplified_time_series}
      {@const hasHr = !!activity.stats.avg_hr}
      {@const hasPower = !!activity.stats.avg_power}
      {#if hasHr || hasPower}
        <div class="section">
          {#if hasHr && hasPower}
            <div class="zones-row">
              <div class="zones-col">
                <HRZones
                  avgHr={activity.stats.avg_hr}
                  maxHr={activity.stats.max_hr}
                  timeSeries={activity.stats.simplified_time_series}
                  zones={zoneToRanges(hrZone)}
                />
              </div>
              <div class="zones-col">
                <PowerZones
                  avgPower={activity.stats.avg_power}
                  maxPower={activity.stats.max_power}
                  timeSeries={activity.stats.simplified_time_series}
                  zones={zoneToRanges(powerZone)}
                />
              </div>
            </div>
          {:else if hasHr}
            <HRZones
              avgHr={activity.stats.avg_hr}
              maxHr={activity.stats.max_hr}
              timeSeries={activity.stats.simplified_time_series}
              zones={zoneToRanges(hrZone)}
            />
          {:else if hasPower}
            <PowerZones
              avgPower={activity.stats.avg_power}
              maxPower={activity.stats.max_power}
              timeSeries={activity.stats.simplified_time_series}
              zones={zoneToRanges(powerZone)}
            />
          {/if}
        </div>
      {/if}
    {/if}
  {/if}
</div>

<Modal open={showEdit} title="Edit Activity" onClose={() => showEdit = false}>
  <div class="edit-form">
    <div class="field">
      <label for="edit-name">Name</label>
      <input id="edit-name" type="text" bind:value={editName} />
    </div>
    <div class="field">
      <label for="edit-sport">Sport Type</label>
      <select id="edit-sport" bind:value={editSportType}>
        <option value="run">Run</option>
        <option value="ride">Ride</option>
        <option value="swim">Swim</option>
        <option value="hike">Hike</option>
        <option value="walk">Walk</option>
        <option value="other">Other</option>
      </select>
    </div>
    <div class="field">
      <label for="edit-notes">Notes</label>
      <textarea id="edit-notes" bind:value={editNotes} rows="3"></textarea>
    </div>
    <div class="field">
      <label for="edit-rpe">RPE (1-10)</label>
      <input id="edit-rpe" type="number" bind:value={editRpe} min="1" max="10" />
    </div>
    {#if gearList.length > 0}
      <div class="field">
        <label for="edit-gear">Gear</label>
        <select id="edit-gear" bind:value={editGearId}>
          <option value={null}>No gear</option>
          {#each gearList as g}
            <option value={g.id}>{g.name}</option>
          {/each}
        </select>
      </div>
    {/if}
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showEdit = false}>Cancel</button>
      <button class="btn btn-primary" onclick={saveEdit} disabled={saving}>
        {saving ? 'Saving...' : 'Save'}
      </button>
    </div>
  </div>
</Modal>

<Modal open={showDelete} title="Delete Activity" onClose={() => showDelete = false}>
  <div class="delete-confirm">
    <p>Are you sure you want to delete <strong>{activity?.name}</strong>?</p>
    <p class="warning">This action cannot be undone.</p>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showDelete = false}>Cancel</button>
      <button class="btn btn-danger" onclick={deleteActivity}>Delete</button>
    </div>
  </div>
</Modal>

<SegmentCreateModal
  open={showSegmentModal}
  activity={activity}
  onClose={() => showSegmentModal = false}
  onCreated={() => showSegmentModal = false}
/>

<style>
  .activity-detail {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
    font-family: var(--font-sans);
  }
  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: none;
    background: none;
    color: var(--primary);
    cursor: pointer;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    padding: 6px 10px;
    border-radius: 6px;
  }
  .back-btn:hover {
    background: var(--primary-light);
  }
  .actions {
    display: flex;
    gap: 8px;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border: none;
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
  }
  .btn-primary {
    background: var(--primary);
    color: white;
  }
  .btn-primary:hover { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-outline {
    background: var(--surface);
    color: var(--text);
    border: 0.5px solid var(--border);
  }
  .btn-outline:hover { background: var(--hover); }
  .btn-danger {
    background: #fee2e2;
    color: #dc2626;
    border: 0.5px solid #fecaca;
  }
  .btn-danger:hover { background: #fecaca; }
  .header { margin-bottom: 24px; }
  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .sport-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    background: color-mix(in srgb, var(--primary) 10%, transparent);
    color: var(--primary);
  }
  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  .meta {
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    margin-top: 4px;
    text-transform: capitalize;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .other-stats {
    margin-bottom: 32px;
  }
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 6px;
  }
  .section { margin-bottom: 32px; width: 100%; }
  .zones-row {
    display: flex;
    gap: 12px;
  }
  .zones-col {
    flex: 1;
    min-width: 0;
  }
  h2 {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    margin-bottom: 12px;
  }
  .laps-table-wrapper {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    overflow: hidden;
  }
  .laps-table {
    width: 100%;
    border-collapse: collapse;
  }
  .laps-table th, .laps-table td {
    padding: 10px 16px;
    text-align: left;
    border-bottom: 0.5px solid var(--border);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
  }
  .laps-table th {
    font-weight: var(--font-weight-medium, 500);
    font-size: var(--font-size-xs, 11px);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg);
    border-bottom: 0.5px solid var(--border);
  }
  .laps-table tr:last-child td { border-bottom: none; }
  .edit-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 320px;
    font-family: var(--font-sans);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
  }
  .field input, .field select, .field textarea {
    padding: 10px 12px;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    background: var(--bg);
    color: var(--text);
  }
  .field input:focus, .field select:focus, .field textarea:focus {
    outline: none;
    border-color: var(--primary);
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
  }
  .delete-confirm p {
    margin: 0 0 8px 0;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text);
  }
  .delete-confirm .warning {
    color: #dc2626;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    margin-bottom: 16px;
  }
  @media (max-width: 768px) {
    .activity-detail { padding: 16px; }
    h1 { font-size: var(--font-size-2xl, 22px); }
    .stat-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 4px; }
    .zones-row { flex-direction: column; }
    .top-bar { flex-wrap: wrap; gap: 8px; }
  }
</style>
