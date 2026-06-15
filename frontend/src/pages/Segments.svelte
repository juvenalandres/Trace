<script lang="ts">
  import { onMount } from 'svelte';
  import { segmentApi, statsApi } from '$lib/api/types';
  import type { SegmentListItem, RouteItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import SegmentCreateModal from '$lib/components/SegmentCreateModal.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  let segments = $state<SegmentListItem[]>([]);
  let loading = $state(true);
  let error = $state('');
  let search = $state('');
  let sportFilter = $state('');
  let showCreate = $state(false);
  let createRoutes = $state<RouteItem[]>([]);
  let routesLoading = $state(false);

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
            <tr class="segment-row" onclick={() => onNavigate?.('segment-detail', seg.id)}>
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

<SegmentCreateModal
  open={showCreate}
  routes={createRoutes}
  onClose={() => showCreate = false}
  onCreated={load}
/>

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
  @media (max-width: 768px) {
    .page { padding: 16px; }
    .filters { flex-direction: column; }
    .segments-table th, .segments-table td { padding: 8px 10px; }
  }
</style>
