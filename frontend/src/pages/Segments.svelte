<script lang="ts">
  import { onMount } from 'svelte';
  import { segmentApi, statsApi } from '$lib/api/types';
  import type { SegmentListItem, Segment, SegmentEffort, SegmentPR, SegmentLeaderboardEntry, RouteItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import SegmentCreateModal from '$lib/components/SegmentCreateModal.svelte';

  interface Props {
  }

  let {}: Props = $props();

  let segments = $state<SegmentListItem[]>([]);
  let loading = $state(true);
  let error = $state('');
  let search = $state('');
  let sportFilter = $state('');
  let selectedSegment = $state<SegmentListItem | null>(null);
  let detailLoading = $state(false);
  let detailError = $state('');
  let segmentDetail = $state<Segment | null>(null);
  let segmentEfforts = $state<SegmentEffort[]>([]);
  let segmentPR = $state<SegmentPR | null>(null);
  let leaderboard = $state<SegmentLeaderboardEntry[]>([]);
  let showCreate = $state(false);
  let showDeleteConfirm = $state(false);
  let showEdit = $state(false);
  let editName = $state('');
  let editDescription = $state('');
  let editSportType = $state('');
  let editSaving = $state(false);
  let createRoutes = $state<RouteItem[]>([]);
  let routesLoading = $state(false);
  let matchingSegment = $state<number | null>(null);
  let matchResult = $state('');

  function formatDistance(m: number | null): string {
    if (m === null) return '-';
    return m >= 1000 ? (m / 1000).toFixed(1) + ' km' : Math.round(m) + ' m';
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

  async function load() {
    loading = true;
    error = '';
    try {
      segments = await segmentApi.list(sportFilter || undefined, search || undefined);
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load segments';
    } finally {
      loading = false;
    }
  }

  async function loadDetail(seg: SegmentListItem) {
    selectedSegment = seg;
    detailLoading = true;
    detailError = '';
    try {
      const [detail, efforts, pr, lb] = await Promise.all([
        segmentApi.get(seg.id),
        segmentApi.efforts(seg.id),
        segmentApi.pr(seg.id),
        segmentApi.leaderboard(seg.id, 10),
      ]);
      segmentDetail = detail;
      segmentEfforts = efforts;
      segmentPR = pr;
      leaderboard = lb;
    } catch (e: unknown) {
      detailError = e instanceof Error ? e.message : 'Failed to load segment detail';
    } finally {
      detailLoading = false;
    }
  }

  function closeDetail() {
    selectedSegment = null;
    segmentDetail = null;
    segmentEfforts = [];
    segmentPR = null;
    leaderboard = [];
  }

  async function handleDelete() {
    if (!selectedSegment) return;
    try {
      await segmentApi.delete(selectedSegment.id);
      closeDetail();
      await load();
    } catch (e: unknown) {
      detailError = e instanceof Error ? e.message : 'Failed to delete segment';
    } finally {
      showDeleteConfirm = false;
    }
  }

  function openEdit() {
    if (!segmentDetail) return;
    editName = segmentDetail.name;
    editDescription = segmentDetail.description ?? '';
    editSportType = segmentDetail.sport_type ?? '';
    showEdit = true;
  }

  async function saveEdit() {
    if (!segmentDetail) return;
    editSaving = true;
    try {
      await segmentApi.update(segmentDetail.id, {
        name: editName,
        description: editDescription || undefined,
        sport_type: editSportType || undefined,
      });
      segmentDetail = await segmentApi.get(segmentDetail.id);
      showEdit = false;
      await load();
    } catch (e: unknown) {
      detailError = e instanceof Error ? e.message : 'Failed to save';
    } finally {
      editSaving = false;
    }
  }

  async function handleDeleteEffort(effortId: number) {
    if (!selectedSegment) return;
    try {
      await segmentApi.deleteEffort(selectedSegment.id, effortId);
      segmentEfforts = await segmentApi.efforts(selectedSegment.id);
      segmentPR = await segmentApi.pr(selectedSegment.id);
      leaderboard = await segmentApi.leaderboard(selectedSegment.id, 10);
    } catch (e: unknown) {
      detailError = e instanceof Error ? e.message : 'Failed to delete effort';
    }
  }

  async function handleMatchActivities() {
    if (!selectedSegment) return;
    matchingSegment = selectedSegment.id;
    matchResult = '';
    try {
      const result = await segmentApi.matchActivities(selectedSegment.id);
      matchResult = `Found ${result.matched} new effort(s)`;
      segmentDetail?.effort_count !== undefined && (segmentDetail.effort_count += result.matched);
      const [efforts, pr, lb] = await Promise.all([
        segmentApi.efforts(selectedSegment.id),
        segmentApi.pr(selectedSegment.id),
        segmentApi.leaderboard(selectedSegment.id, 10),
      ]);
      segmentEfforts = efforts;
      segmentPR = pr;
      leaderboard = lb;
    } catch (e: unknown) {
      matchResult = e instanceof Error ? e.message : 'Match failed';
    } finally {
      matchingSegment = null;
    }
  }

  async function openCreate() {
    routesLoading = true;
    try {
      createRoutes = await statsApi.routes();
    } catch {
      createRoutes = [];
    } finally {
      routesLoading = false;
    }
    showCreate = true;
  }

  onMount(() => {
    load();
  });
</script>

<div class="page">
  <div class="top-bar">
    <h1>Segments</h1>
    <button class="btn btn-primary" onclick={openCreate}>
      <Icon name="plus" size={16} />
      Create Segment
    </button>
  </div>

  <div class="filters">
    <input
      type="text"
      class="search-input"
      placeholder="Search segments..."
      bind:value={search}
      oninput={() => load()}
    />
    <select class="sport-select" bind:value={sportFilter} onchange={() => load()}>
      <option value="">All sports</option>
      <option value="run">Run</option>
      <option value="ride">Ride</option>
      <option value="swim">Swim</option>
      <option value="hike">Hike</option>
      <option value="walk">Walk</option>
      <option value="other">Other</option>
    </select>
  </div>

  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if segments.length === 0}
    <div class="empty">
      <Icon name="segments" size={40} />
      <p>No segments yet.</p>
      <button class="btn btn-primary" onclick={openCreate}>Create your first segment</button>
    </div>
  {:else}
    <div class="segments-list">
      <table class="segments-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Sport</th>
            <th>Distance</th>
            <th>Best Time</th>
            <th>Efforts</th>
            <th>Creator</th>
          </tr>
        </thead>
        <tbody>
          {#each segments as seg}
            <tr class="segment-row" onclick={() => loadDetail(seg)}>
              <td class="segment-name">{seg.name}</td>
              <td>
                {#if seg.sport_type}
                  <span class="sport-badge" style="background: {sportColor(seg.sport_type)}20; color: {sportColor(seg.sport_type)}">
                    {seg.sport_type}
                  </span>
                {:else}
                  <span class="sport-badge" style="background: #64748b20; color: #64748b">Any</span>
                {/if}
              </td>
              <td>{formatDistance(seg.distance_m)}</td>
              <td>{seg.best_time ? formatTime(seg.best_time) : '-'}</td>
              <td>{seg.effort_count}</td>
              <td>{seg.creator_name ?? 'Unknown'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

{#if selectedSegment}
  <div class="detail-overlay" role="dialog" aria-modal="true" tabindex="-1" onclick={closeDetail}>
    <div class="detail-panel" onclick={(e) => e.stopPropagation()}>
      {#if detailLoading}
        <LoadingSpinner />
      {:else if detailError}
        <ErrorBanner message={detailError} retry={closeDetail} />
      {:else}
        <div class="detail-header">
          <div>
            <h2>{selectedSegment.name}</h2>
            {#if segmentDetail?.creator_name}
              <span class="creator">by {segmentDetail.creator_name}</span>
            {/if}
          </div>
          <div class="detail-actions">
            <button class="btn btn-secondary" onclick={handleMatchActivities} disabled={matchingSegment !== null}>
              {matchingSegment !== null ? 'Matching...' : 'Match Activities'}
            </button>
            <button class="btn btn-secondary" onclick={openEdit}>
              Edit
            </button>
            <button class="btn btn-danger" onclick={() => showDeleteConfirm = true}>
              <Icon name="logout" size={14} />
              Delete
            </button>
            <button class="btn btn-icon" onclick={closeDetail}>
              <Icon name="chevronRight" size={18} />
            </button>
          </div>
          {#if matchResult}
            <div class="match-result">{matchResult}</div>
          {/if}
        </div>

        {#if segmentDetail?.description}
          <p class="description">{segmentDetail.description}</p>
        {/if}

        <div class="detail-stats-row">
          {#if segmentDetail?.sport_type}
            <div class="detail-stat">
              <span class="detail-stat-label">Sport</span>
              <span class="detail-stat-value">
                <span class="sport-badge" style="background: {sportColor(segmentDetail.sport_type)}20; color: {sportColor(segmentDetail.sport_type)}">
                  {segmentDetail.sport_type}
                </span>
              </span>
            </div>
          {/if}
          <div class="detail-stat">
            <span class="detail-stat-label">Distance</span>
            <span class="detail-stat-value">{formatDistance(segmentDetail?.distance_m ?? null)}</span>
          </div>
          {#if segmentDetail?.elevation_gain_m}
            <div class="detail-stat">
              <span class="detail-stat-label">Elevation Gain</span>
              <span class="detail-stat-value">{Math.round(segmentDetail.elevation_gain_m)} m</span>
            </div>
          {/if}
          <div class="detail-stat">
            <span class="detail-stat-label">Total Efforts</span>
            <span class="detail-stat-value">{segmentDetail?.effort_count ?? 0}</span>
          </div>
        </div>

        {#if segmentPR && segmentPR.elapsed_time_s}
          <div class="pr-card">
            <span class="pr-label">Your Personal Record</span>
            <span class="pr-time">{formatTime(segmentPR.elapsed_time_s)}</span>
            {#if segmentPR.avg_speed}
              <span class="pr-detail">Avg Speed: {formatSpeed(segmentPR.avg_speed)}</span>
            {/if}
          </div>
        {/if}

        {#if leaderboard.length > 0}
          <div class="section">
            <h3>Leaderboard</h3>
            <table class="leaderboard-table">
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
        {/if}

        <div class="section">
          <h3>Effort History</h3>
          {#if segmentEfforts.length === 0}
            <p class="empty-text">No efforts recorded yet. Upload an activity that passes through this segment.</p>
          {:else}
            <table class="efforts-table">
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
                {#each segmentEfforts as effort}
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
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}

<SegmentCreateModal
  open={showCreate}
  routes={createRoutes}
  onClose={() => showCreate = false}
  onCreated={load}
/>

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
    <p>Are you sure you want to delete <strong>{selectedSegment?.name}</strong>?</p>
    <p class="warning">This will also delete all {selectedSegment?.effort_count ?? 0} effort(s) and cannot be undone.</p>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showDeleteConfirm = false}>Cancel</button>
      <button class="btn btn-danger" onclick={handleDelete}>Delete</button>
    </div>
  </div>
</Modal>

<style>
  .page {
    max-width: 900px;
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
  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  .filters {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }
  .search-input {
    flex: 1;
    padding: 10px 12px;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    background: var(--bg);
    color: var(--text);
  }
  .sport-select {
    padding: 10px 12px;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    background: var(--bg);
    color: var(--text);
    min-width: 120px;
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
  .btn-secondary {
    background: var(--surface);
    color: var(--text);
    border: 0.5px solid var(--border);
  }
  .btn-danger {
    background: #fee2e2;
    color: #dc2626;
    border: 0.5px solid #fecaca;
  }
  .btn-danger:hover { background: #fecaca; }
  .btn-icon {
    background: none;
    border: none;
    color: var(--text-secondary);
    padding: 6px;
    border-radius: 6px;
  }
  .btn-icon:hover { background: var(--hover); }
  .btn-danger-icon {
    color: #dc2626;
  }
  .btn-danger-icon:hover { background: #fee2e2; }
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 0;
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
  }
  .segments-list {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    overflow: hidden;
  }
  .segments-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-base, 13px);
  }
  .segments-table th {
    text-align: left;
    padding: 12px 16px;
    font-weight: var(--font-weight-medium, 500);
    font-size: var(--font-size-xs, 11px);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg);
    border-bottom: 0.5px solid var(--border);
  }
  .segments-table td {
    padding: 12px 16px;
    border-bottom: 0.5px solid var(--border);
  }
  .segment-row {
    cursor: pointer;
  }
  .segment-row:hover {
    background: var(--hover);
  }
  .segment-name {
    font-weight: var(--font-weight-medium, 500);
  }
  .sport-badge {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: var(--font-size-xs, 11px);
    text-transform: capitalize;
    font-weight: var(--font-weight-medium, 500);
  }
  .detail-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1000;
    display: flex;
    justify-content: flex-end;
  }
  .detail-panel {
    background: var(--card-bg, var(--surface));
    border-left: var(--card-border, 0.5px solid var(--border));
    width: 100%;
    max-width: 600px;
    height: 100vh;
    overflow: auto;
    padding: 24px;
    font-family: var(--font-sans);
  }
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }
  .detail-header h2 {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  .creator {
    color: var(--text-secondary);
    font-size: var(--font-size-sm, 12px);
  }
  .detail-actions {
    display: flex;
    gap: 8px;
  }
  .match-result {
    font-size: var(--font-size-base, 13px);
    color: var(--primary);
    margin-bottom: 12px;
    padding: 6px 10px;
    background: color-mix(in srgb, var(--primary) 8%, transparent);
    border-radius: 6px;
  }
  .description {
    font-size: var(--font-size-base, 13px);
    color: var(--text-secondary);
    margin-bottom: 16px;
  }
  .detail-stats-row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 24px;
  }
  .detail-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .detail-stat-label {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .detail-stat-value {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
  }
  .pr-card {
    background: color-mix(in srgb, var(--primary) 8%, transparent);
    border: 0.5px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .pr-label {
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .pr-time {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--primary);
  }
  .pr-detail {
    font-size: var(--font-size-sm, 12px);
    color: var(--text-secondary);
  }
  .section {
    margin-bottom: 24px;
  }
  .section h3 {
    font-size: var(--font-size-lg, 15px);
    font-weight: var(--font-weight-medium, 500);
    margin-bottom: 12px;
  }
  .leaderboard-table, .efforts-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm, 12px);
  }
  .leaderboard-table th, .efforts-table th {
    text-align: left;
    padding: 8px 12px;
    font-weight: var(--font-weight-medium, 500);
    font-size: var(--font-size-xs, 11px);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg);
    border-bottom: 0.5px solid var(--border);
  }
  .leaderboard-table td, .efforts-table td {
    padding: 8px 12px;
    border-bottom: 0.5px solid var(--border);
  }
  .is-pr {
    background: color-mix(in srgb, var(--primary) 8%, transparent);
  }
  .empty-text {
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
  }
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
    .page { padding: 16px; }
    .filters { flex-direction: column; }
    .detail-panel { max-width: 100%; }
    .detail-stats-row { gap: 12px; }
    .segments-table th, .segments-table td { padding: 8px 10px; }
  }
</style>
