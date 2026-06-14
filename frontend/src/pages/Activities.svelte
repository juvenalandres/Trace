<script lang="ts">
  import { onMount } from 'svelte';
  import { activitiesApi } from '$lib/api/types';
  import type { ActivitySummary, ActivityFilters } from '$lib/api/types';
  import ActivityTable from '$lib/components/ActivityTable.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import Icon from '$lib/components/Icon.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  let activities = $state<ActivitySummary[]>([]);
  let total = $state(0);
  let page = $state(1);
  let loading = $state(true);
  let error = $state('');
  let showFilters = $state(false);

  let filters: ActivityFilters = $state({});
  let sportFilter = $state('');
  let sourceFilter = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let distanceMin = $state('');
  let distanceMax = $state('');
  let elevationMin = $state('');
  let elevationMax = $state('');

  function buildFilters(): ActivityFilters {
    const f: ActivityFilters = {};
    if (sportFilter) f.sport_type = sportFilter;
    if (sourceFilter) f.source = sourceFilter;
    if (dateFrom) f.date_from = dateFrom;
    if (dateTo) f.date_to = dateTo;
    if (distanceMin) f.distance_min = parseFloat(distanceMin) * 1000;
    if (distanceMax) f.distance_max = parseFloat(distanceMax) * 1000;
    if (elevationMin) f.elevation_min = parseFloat(elevationMin);
    if (elevationMax) f.elevation_max = parseFloat(elevationMax);
    return f;
  }

  async function load() {
    loading = true;
    try {
      const res = await activitiesApi.list(page, 20, buildFilters());
      activities = res.items;
      total = res.total;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      loading = false;
    }
  }

  function applyFilters() {
    page = 1;
    load();
  }

  function clearFilters() {
    sportFilter = '';
    sourceFilter = '';
    dateFrom = '';
    dateTo = '';
    distanceMin = '';
    distanceMax = '';
    elevationMin = '';
    elevationMax = '';
    page = 1;
    load();
  }

  function nextPage() {
    page++;
    load();
  }

  function prevPage() {
    page--;
    load();
  }

  const activeFilterCount = $derived(
    [sportFilter, sourceFilter, dateFrom, dateTo, distanceMin, distanceMax, elevationMin, elevationMax]
      .filter(v => v !== '').length
  );

  onMount(load);
</script>

<div class="page">
  <div class="page-header">
    <h1>Activities</h1>
    <button class="btn btn-primary" onclick={() => onNavigate?.('upload')}>
      <Icon name="elevationUp" size={16} />
      Upload
    </button>
  </div>

  <div class="toolbar">
    <button class="btn btn-outline" onclick={() => showFilters = !showFilters}>
      <Icon name="dashboard" size={16} />
      Filters
      {#if activeFilterCount > 0}
        <span class="badge">{activeFilterCount}</span>
      {/if}
    </button>
    <span class="total">{total} activities</span>
  </div>

  {#if showFilters}
    <div class="filter-panel">
      <div class="filter-row">
        <div class="filter-group">
          <label>Sport</label>
          <select bind:value={sportFilter}>
            <option value="">All sports</option>
            <option value="run">Run</option>
            <option value="ride">Ride</option>
            <option value="swim">Swim</option>
            <option value="hike">Hike</option>
            <option value="walk">Walk</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Source</label>
          <select bind:value={sourceFilter}>
            <option value="">All sources</option>
            <option value="gpx">GPX Upload</option>
            <option value="fit">FIT Upload</option>
            <option value="garmin">Garmin</option>
            <option value="manual">Manual</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Date from</label>
          <input type="date" bind:value={dateFrom} />
        </div>
        <div class="filter-group">
          <label>Date to</label>
          <input type="date" bind:value={dateTo} />
        </div>
      </div>
      <div class="filter-row">
        <div class="filter-group">
          <label>Distance min (km)</label>
          <input type="number" bind:value={distanceMin} placeholder="0" step="0.1" />
        </div>
        <div class="filter-group">
          <label>Distance max (km)</label>
          <input type="number" bind:value={distanceMax} placeholder="100" step="0.1" />
        </div>
        <div class="filter-group">
          <label>Elevation min (m)</label>
          <input type="number" bind:value={elevationMin} placeholder="0" />
        </div>
        <div class="filter-group">
          <label>Elevation max (m)</label>
          <input type="number" bind:value={elevationMax} placeholder="5000" />
        </div>
      </div>
      <div class="filter-actions">
        <button class="btn btn-primary" onclick={applyFilters}>Apply</button>
        <button class="btn btn-outline" onclick={clearFilters}>Clear</button>
      </div>
    </div>
  {/if}

  {#if loading}
    <LoadingSpinner />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if activities.length === 0 && activeFilterCount > 0}
    <EmptyState icon="activities" message="No activities match your filters. Try adjusting or clearing them." action="Clear Filters" onAction={clearFilters} />
  {:else if activities.length === 0}
    <EmptyState icon="activities" message="No activities yet. Upload a GPX file to get started." action="Upload" onAction={() => onNavigate?.('upload')} />
  {:else}
    <ActivityTable {activities} onRowClick={(id) => onNavigate?.('activity', id)} />

    <div class="pagination">
      <button class="btn btn-outline" disabled={page <= 1} onclick={prevPage}>Previous</button>
      <span>Page {page} of {Math.max(1, Math.ceil(total / 20))}</span>
      <button class="btn btn-outline" disabled={page * 20 >= total} onclick={nextPage}>Next</button>
    </div>
  {/if}
</div>

<style>
  .page {
    max-width: 1200px;
  }
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    margin: 0;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }
  .total {
    color: var(--text-secondary);
    font-size: 14px;
    margin-left: auto;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
  }
  .btn-primary {
    background: var(--primary);
    color: white;
  }
  .btn-primary:hover {
    opacity: 0.9;
  }
  .btn-outline {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .btn-outline:hover {
    background: var(--hover);
  }
  .btn-outline:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .badge {
    background: var(--primary);
    color: white;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 10px;
    margin-left: 4px;
  }
  .filter-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
  }
  .filter-row {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .filter-row:last-of-type {
    margin-bottom: 0;
  }
  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 140px;
    flex: 1;
  }
  .filter-group label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }
  .filter-group select,
  .filter-group input {
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 13px;
    background: var(--bg);
    color: var(--text);
  }
  .filter-group select:focus,
  .filter-group input:focus {
    outline: none;
    border-color: var(--primary);
  }
  .filter-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    margin-top: 20px;
    font-size: 14px;
    color: var(--text-secondary);
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: 22px; }
    .page-header { flex-wrap: wrap; gap: 12px; }
    .filter-row { flex-direction: column; gap: 12px; }
    .filter-group { min-width: 100%; }
    .toolbar { flex-wrap: wrap; }
  }
</style>
