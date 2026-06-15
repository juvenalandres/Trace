<script lang="ts">
  import { onMount } from 'svelte';
  import { segmentApi, routeApi } from '$lib/api/types';
  import type { Segment, SegmentEffort, SegmentPR, SegmentLeaderboardEntry } from '$lib/api/types';
  import RouteChartPanel from '$lib/components/RouteChartPanel.svelte';

  interface TimePoint {
    d: number;
    ele: number | null;
    spd: number | null;
    pace: number | null;
    hr: number | null;
    pwr: number | null;
    cad: number | null;
    lat: number;
    lng: number;
  }
  import Modal from '$lib/components/Modal.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';

  interface Props {
    segmentId: number;
    onBack?: () => void;
  }

  let { segmentId, onBack }: Props = $props();

  let segment = $state<Segment | null>(null);
  let loading = $state(true);
  let error = $state('');
  let segmentEfforts = $state<SegmentEffort[]>([]);
  let segmentPR = $state<SegmentPR | null>(null);
  let leaderboard = $state<SegmentLeaderboardEntry[]>([]);
  let timeSeries = $state('');
  let elevationLoading = $state(false);
  let elevationError = $state('');

  let showEdit = $state(false);
  let editName = $state('');
  let editDescription = $state('');
  let editSportType = $state('');
  let editSaving = $state(false);

  let showDeleteConfirm = $state(false);

  let matching = $state(false);
  let matchResult = $state('');

  let effortPage = $state(0);
  const effortsPerPage = 10;

  let totalEffortPages = $derived(Math.ceil(segmentEfforts.length / effortsPerPage));
  let paginatedEfforts = $derived(
    segmentEfforts.slice(effortPage * effortsPerPage, (effortPage + 1) * effortsPerPage)
  );

  function formatDistance(m: number | null): string {
    if (m === null) return '-';
    return m >= 1000 ? (m / 1000).toFixed(2) + ' km' : Math.round(m) + ' m';
  }

  function formatTime(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  function formatSpeed(speed: number | null): string {
    if (speed === null) return '-';
    return (speed * 3.6).toFixed(1) + ' km/h';
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function sportColor(sport: string | null): string {
    const colors: Record<string, string> = {
      run: '#22c55e', ride: '#3b82f6', swim: '#06b6d4', hike: '#f59e0b', walk: '#a855f7', other: '#64748b'
    };
    return colors[sport ?? 'other'];
  }

  function decodePolyline(str: string): [number, number][] {
    const coords: [number, number][] = [];
    let lat = 0, lng = 0;
    let index = 0;
    while (index < str.length) {
      let b, shift = 0, result = 0;
      do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      lat += (result & 1) ? ~(result >> 1) : (result >> 1);
      shift = 0; result = 0;
      do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      lng += (result & 1) ? ~(result >> 1) : (result >> 1);
      coords.push([lat / 1e5, lng / 1e5]);
    }
    return coords;
  }

  function encodePolyline(coords: [number, number][]): string {
    let str = '';
    let prevLat = 0, prevLng = 0;
    for (const [lat, lng] of coords) {
      const latE5 = Math.round(lat * 1e5);
      const lngE5 = Math.round(lng * 1e5);
      const dLat = latE5 - prevLat;
      const dLng = lngE5 - prevLng;
      prevLat = latE5;
      prevLng = lngE5;
      for (const v of [dLat, dLng]) {
        const shifted = v << 1;
        const bits = v < 0 ? ~shifted : shifted;
        let chunk = bits & 0x1f;
        for (let remaining = bits >>> 5; remaining > 0; remaining >>>= 5) {
          str += String.fromCharCode((chunk | 0x20) + 63);
          chunk = remaining & 0x1f;
        }
        str += String.fromCharCode(chunk + 63);
      }
    }
    return str;
  }

  async function loadElevation(polyline: string) {
    elevationLoading = true;
    elevationError = '';
    try {
      const coords = decodePolyline(polyline);
      if (coords.length < 2) { elevationError = 'Segment too short'; return; }

      const step = Math.max(1, Math.floor(coords.length / 100));
      const sampled = coords.filter((_, i) => i % step === 0 || i === coords.length - 1);

      const resp = await routeApi.elevation(sampled.map(c => ({ lat: c[0], lng: c[1] })));
      if (resp.elevation_profile.length < 2) { elevationError = 'Not enough elevation data'; return; }

      const points: TimePoint[] = resp.elevation_profile.map((p, i) => ({
        d: p.distance,
        ele: p.elevation,
        spd: null,
        pace: null,
        hr: null,
        pwr: null,
        cad: null,
        lat: sampled[i][0],
        lng: sampled[i][1],
      }));
      timeSeries = JSON.stringify(points);
    } catch (e: unknown) {
      elevationError = e instanceof Error ? e.message : 'Failed to load elevation';
    } finally {
      elevationLoading = false;
    }
  }

  async function load() {
    loading = true;
    error = '';
    try {
      const [detail, efforts, pr, lb] = await Promise.all([
        segmentApi.get(segmentId),
        segmentApi.efforts(segmentId),
        segmentApi.pr(segmentId),
        segmentApi.leaderboard(segmentId, 10),
      ]);
      segment = detail;
      segmentEfforts = efforts;
      segmentPR = pr;
      leaderboard = lb;
      effortPage = 0;

      const polyline = detail.polyline ?? encodePolyline([[detail.start_lat, detail.start_lng], [detail.end_lat, detail.end_lng]]);
      if (polyline) {
        loadElevation(polyline);
      }
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load segment';
    } finally {
      loading = false;
    }
  }

  function openEdit() {
    if (!segment) return;
    editName = segment.name;
    editDescription = segment.description ?? '';
    editSportType = segment.sport_type ?? '';
    showEdit = true;
  }

  async function saveEdit() {
    if (!segment) return;
    editSaving = true;
    try {
      await segmentApi.update(segment.id, {
        name: editName,
        description: editDescription || undefined,
        sport_type: editSportType || undefined,
      });
      segment = await segmentApi.get(segment.id);
      showEdit = false;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save';
    } finally {
      editSaving = false;
    }
  }

  async function handleDelete() {
    if (!segment) return;
    try {
      await segmentApi.delete(segment.id);
      onBack?.();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete segment';
    } finally {
      showDeleteConfirm = false;
    }
  }

  async function handleDeleteEffort(effortId: number) {
    if (!segment) return;
    try {
      await segmentApi.deleteEffort(segment.id, effortId);
      segmentEfforts = await segmentApi.efforts(segment.id);
      segmentPR = await segmentApi.pr(segment.id);
      leaderboard = await segmentApi.leaderboard(segment.id, 10);
      if (segmentEfforts.length <= effortPage * effortsPerPage && effortPage > 0) {
        effortPage--;
      }
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete effort';
    }
  }

  async function handleMatchActivities() {
    if (!segment) return;
    matching = true;
    matchResult = '';
    try {
      const result = await segmentApi.matchActivities(segment.id);
      matchResult = `Found ${result.matched} new effort(s)`;
      const [efforts, pr, lb] = await Promise.all([
        segmentApi.efforts(segment.id),
        segmentApi.pr(segment.id),
        segmentApi.leaderboard(segment.id, 10),
      ]);
      segmentEfforts = efforts;
      segmentPR = pr;
      leaderboard = lb;
    } catch (e: unknown) {
      matchResult = e instanceof Error ? e.message : 'Match failed';
    } finally {
      matching = false;
    }
  }

  onMount(load);
</script>

<div class="segment-detail">
  <div class="top-bar">
    <button class="back-btn" onclick={onBack}>
      <Icon name="chevronLeft" size={16} />
      Back
    </button>
    {#if segment}
      <div class="actions">
        <button class="btn btn-outline" onclick={handleMatchActivities} disabled={matching}>
          {matching ? 'Matching...' : 'Match Activities'}
        </button>
        <button class="btn btn-outline" onclick={openEdit}>
          <Icon name="segments" size={16} />
          Edit
        </button>
        <button class="btn btn-danger" onclick={() => showDeleteConfirm = true}>
          <Icon name="logout" size={16} />
          Delete
        </button>
      </div>
    {/if}
  </div>

  {#if matchResult}
    <div class="match-banner">{matchResult}</div>
  {/if}

  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if segment}
    <div class="header">
      <div class="title-row">
        <span class="sport-icon" style="background: {sportColor(segment.sport_type)}20; color: {sportColor(segment.sport_type)}">
          <Icon name="segments" size={24} />
        </span>
        <h1>{segment.name}</h1>
      </div>
      <div class="meta">
        {#if segment.creator_name}by {segment.creator_name} · {/if}
        {#if segment.sport_type}
          <span class="sport-badge" style="background: {sportColor(segment.sport_type)}20; color: {sportColor(segment.sport_type)}">
            {segment.sport_type}
          </span>
        {/if}
      </div>
      {#if segment.description}
        <p class="description">{segment.description}</p>
      {/if}
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">Distance</div>
        <div class="stat-value">{formatDistance(segment.distance_m)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Elevation Gain</div>
        <div class="stat-value">{segment.elevation_gain_m != null ? Math.round(segment.elevation_gain_m) + ' m' : '-'}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Best Time</div>
        <div class="stat-value">{segment.best_time ? formatTime(segment.best_time) : '-'}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Efforts</div>
        <div class="stat-value">{segment.effort_count}</div>
      </div>
    </div>

    <div class="section">
      <h2>Route</h2>
      {#if elevationLoading}
        <div class="elevation-loading">Loading elevation data...</div>
      {:else if elevationError}
        <div class="elevation-error">{elevationError}</div>
      {:else if timeSeries}
        <RouteChartPanel
          polyline={segment.polyline ?? encodePolyline([[segment.start_lat, segment.start_lng], [segment.end_lat, segment.end_lng]])}
          timeSeries={timeSeries}
          sportType={segment.sport_type ?? ''}
        />
      {/if}
    </div>

    {#if segmentPR && segmentPR.elapsed_time_s}
      <div class="section">
        <h2>Personal Record</h2>
        <div class="pr-card">
          <div class="pr-main">
            <span class="pr-time">{formatTime(segmentPR.elapsed_time_s)}</span>
          </div>
          <div class="pr-details">
            {#if segmentPR.avg_speed}
              <span class="pr-detail">Avg Speed: {formatSpeed(segmentPR.avg_speed)}</span>
            {/if}
            {#if segmentPR.avg_hr}
              <span class="pr-detail">Avg HR: {Math.round(segmentPR.avg_hr)} bpm</span>
            {/if}
            {#if segmentPR.avg_power}
              <span class="pr-detail">Avg Power: {Math.round(segmentPR.avg_power)} W</span>
            {/if}
          </div>
        </div>
      </div>
    {/if}

    {#if leaderboard.length > 0}
      <div class="section">
        <h2>Leaderboard</h2>
        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Athlete</th>
                <th>Time</th>
                <th>Avg Speed</th>
              </tr>
            </thead>
            <tbody>
              {#each leaderboard as entry}
                <tr class:is-pr={segmentPR && segmentPR.elapsed_time_s === entry.elapsed_time_s}>
                  <td>{entry.rank}</td>
                  <td>{entry.user_name ?? 'Unknown'}</td>
                  <td>{formatTime(entry.elapsed_time_s)}</td>
                  <td>{formatSpeed(entry.avg_speed)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}

    <div class="section">
      <h2>Effort History</h2>
      {#if segmentEfforts.length === 0}
        <p class="empty-text">No efforts recorded yet. Upload an activity that passes through this segment.</p>
      {:else}
        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Athlete</th>
                <th>Time</th>
                <th>Avg Speed</th>
                <th>Avg HR</th>
                <th>Avg Power</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {#each paginatedEfforts as effort}
                <tr>
                  <td>{formatDate(effort.start_time)}</td>
                  <td>{effort.user_name ?? 'Unknown'}</td>
                  <td>{formatTime(effort.elapsed_time_s)}</td>
                  <td>{formatSpeed(effort.avg_speed)}</td>
                  <td>{effort.avg_hr ? Math.round(effort.avg_hr) : '--'}</td>
                  <td>{effort.avg_power ? Math.round(effort.avg_power) : '--'}</td>
                  <td>
                    <button class="btn btn-icon btn-danger-icon" onclick={() => handleDeleteEffort(effort.id)} title="Delete effort">
                      <Icon name="logout" size={14} />
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if totalEffortPages > 1}
          <div class="pagination">
            <button class="btn btn-sm" onclick={() => effortPage = Math.max(0, effortPage - 1)} disabled={effortPage === 0}>
              <Icon name="chevronLeft" size={14} />
              Previous
            </button>
            <span class="page-info">Page {effortPage + 1} of {totalEffortPages}</span>
            <button class="btn btn-sm" onclick={() => effortPage = Math.min(totalEffortPages - 1, effortPage + 1)} disabled={effortPage >= totalEffortPages - 1}>
              Next
              <Icon name="chevronRight" size={14} />
            </button>
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>

<Modal open={showEdit} title="Edit Segment" onClose={() => showEdit = false}>
  <div class="edit-form">
    <div class="field">
      <label for="edit-name">Name</label>
      <input id="edit-name" type="text" bind:value={editName} />
    </div>
    <div class="field">
      <label for="edit-sport">Sport Type</label>
      <select id="edit-sport" bind:value={editSportType}>
        <option value="">Any</option>
        <option value="run">Run</option>
        <option value="ride">Ride</option>
        <option value="swim">Swim</option>
        <option value="hike">Hike</option>
        <option value="walk">Walk</option>
        <option value="other">Other</option>
      </select>
    </div>
    <div class="field">
      <label for="edit-desc">Description</label>
      <textarea id="edit-desc" bind:value={editDescription} rows="2"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showEdit = false}>Cancel</button>
      <button class="btn btn-primary" onclick={saveEdit} disabled={editSaving}>
        {editSaving ? 'Saving...' : 'Save'}
      </button>
    </div>
  </div>
</Modal>

<Modal open={showDeleteConfirm} title="Delete Segment" onClose={() => showDeleteConfirm = false}>
  <div class="delete-confirm">
    <p>Are you sure you want to delete <strong>{segment?.name}</strong>?</p>
    <p class="warning">This will also delete all {segment?.effort_count ?? 0} effort(s) and cannot be undone.</p>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showDeleteConfirm = false}>Cancel</button>
      <button class="btn btn-danger" onclick={handleDelete}>Delete</button>
    </div>
  </div>
</Modal>

<style>
  .segment-detail {
    max-width: 960px;
    margin: 0 auto;
    padding: 24px;
    font-family: var(--font-sans);
  }
  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 8px 12px;
    border: none;
    background: none;
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    cursor: pointer;
    border-radius: 8px;
  }
  .back-btn:hover { background: var(--hover); color: var(--text); }
  .actions {
    display: flex;
    gap: 8px;
  }
  .match-banner {
    font-size: var(--font-size-base, 13px);
    color: var(--primary);
    margin-bottom: 16px;
    padding: 8px 12px;
    background: color-mix(in srgb, var(--primary) 8%, transparent);
    border-radius: 8px;
  }
  .header {
    margin-bottom: 24px;
  }
  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
  }
  .sport-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  .meta {
    font-size: var(--font-size-sm, 12px);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .sport-badge {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: var(--font-size-xs, 11px);
    text-transform: capitalize;
    font-weight: var(--font-weight-medium, 500);
  }
  .description {
    font-size: var(--font-size-base, 13px);
    color: var(--text-secondary);
    margin: 8px 0 0 0;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
  }
  .stat-label {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .stat-value {
    font-size: var(--font-size-lg, 15px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .section {
    margin-bottom: 28px;
  }
  .section h2 {
    font-size: var(--font-size-lg, 15px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0 0 12px 0;
  }
  .elevation-loading, .elevation-error {
    padding: 16px;
    font-size: var(--font-size-base, 13px);
    color: var(--text-secondary);
    text-align: center;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
  }
  .elevation-error { color: #dc2626; }
  .pr-card {
    background: color-mix(in srgb, var(--primary) 8%, transparent);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
  }
  .pr-main {
    margin-bottom: 6px;
  }
  .pr-time {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--primary);
  }
  .pr-details {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }
  .pr-detail {
    font-size: var(--font-size-sm, 12px);
    color: var(--text-secondary);
  }
  .table-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    overflow: hidden;
  }
  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm, 12px);
  }
  .data-table th {
    text-align: left;
    padding: 10px 14px;
    font-weight: var(--font-weight-medium, 500);
    font-size: var(--font-size-xs, 11px);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg);
    border-bottom: 0.5px solid var(--border);
  }
  .data-table td {
    padding: 10px 14px;
    border-bottom: 0.5px solid var(--border);
  }
  .is-pr {
    background: color-mix(in srgb, var(--primary) 8%, transparent);
  }
  .empty-text {
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
  }
  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 16px;
  }
  .page-info {
    font-size: var(--font-size-sm, 12px);
    color: var(--text-secondary);
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
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { opacity: 0.9; }
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
  .btn-sm { padding: 6px 10px; font-size: var(--font-size-xs, 11px); }
  .btn-icon {
    background: none;
    border: none;
    color: var(--text-secondary);
    padding: 6px;
    border-radius: 6px;
    cursor: pointer;
  }
  .btn-icon:hover { background: var(--hover); }
  .btn-danger-icon { color: #dc2626; }
  .btn-danger-icon:hover { background: #fee2e2; }
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
    color: var(--text);
  }
  .delete-confirm .warning {
    color: #dc2626;
    margin-bottom: 16px;
  }
  @media (max-width: 768px) {
    .segment-detail { padding: 16px; }
    .stat-grid { grid-template-columns: repeat(2, 1fr); }
    .actions { flex-wrap: wrap; }
    .data-table th, .data-table td { padding: 8px 10px; }
  }
</style>
