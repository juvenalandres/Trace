<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import { statsApi } from '$lib/api/types';
  import type { RouteItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import TileSelector from '$lib/components/TileSelector.svelte';
  import { getSelectedTile, type TileProvider } from '$lib/map/tiles';

  let mapContainer: HTMLDivElement;
  let map: L.Map | null = null;
  let currentTileLayer: L.TileLayer | null = null;
  let routes = $state<RouteItem[]>([]);
  let loading = $state(true);
  let error = $state('');
  let sportFilter = $state('');
  let yearFilter = $state('');
  let layerGroup: L.LayerGroup | null = null;
  let availableYears = $state<number[]>([]);

  const sportColors: Record<string, string> = {
    run: '#22c55e',
    ride: '#3b82f6',
    walk: '#f59e0b',
    hike: '#f97316',
    swim: '#06b6d4',
    other: '#8b5cf6',
  };

  function decodePolyline(str: string): [number, number][] {
    const coords: [number, number][] = [];
    let lat = 0, lng = 0;
    let index = 0;
    while (index < str.length) {
      let b, shift = 0, result = 0;
      do {
        b = str.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      lat += (result & 1) ? ~(result >> 1) : (result >> 1);
      shift = 0;
      result = 0;
      do {
        b = str.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      lng += (result & 1) ? ~(result >> 1) : (result >> 1);
      coords.push([lat / 1e5, lng / 1e5]);
    }
    return coords;
  }

  async function loadRoutes() {
    loading = true;
    error = '';
    try {
      const year = yearFilter ? parseInt(yearFilter) : undefined;
      routes = await statsApi.routes(sportFilter || undefined, year);
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load routes';
      routes = [];
    } finally {
      loading = false;
    }
  }

  function renderRoutes() {
    if (!map || !layerGroup) return;
    layerGroup.clearLayers();

    if (routes.length === 0) return;

    const bounds = L.latLngBounds([]);
    for (const r of routes) {
      if (!r.polyline) continue;
      const coords = decodePolyline(r.polyline);
      if (coords.length < 2) continue;

      const color = sportColors[r.sport_type] ?? sportColors.other;
      const line = L.polyline(coords, {
        color,
        weight: 2.5,
        opacity: 0.7,
      });

      line.bindPopup(`<strong>${r.name}</strong><br>${r.sport_type} · ${(r.distance_m / 1000).toFixed(1)} km`);
      layerGroup.addLayer(line);
      bounds.extend(coords);
    }

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  }

  function addTileLayer(provider: TileProvider) {
    if (!map) return;
    currentTileLayer?.remove();
    currentTileLayer = L.tileLayer(provider.url, {
      attribution: provider.attribution,
      maxZoom: provider.maxZoom,
    }).addTo(map);
  }

  function handleTileChange(provider: TileProvider) {
    addTileLayer(provider);
  }

  onMount(async () => {
    if (!mapContainer) return;

    map = L.map(mapContainer, { scrollWheelZoom: true }).setView([0, 0], 2);
    const tile = getSelectedTile();
    currentTileLayer = L.tileLayer(tile.url, {
      attribution: tile.attribution,
      maxZoom: tile.maxZoom,
    }).addTo(map);

    layerGroup = L.layerGroup().addTo(map);

    try {
      availableYears = await statsApi.availableYears();
    } catch {
      availableYears = [];
    }

    await loadRoutes();
    renderRoutes();
  });

  onDestroy(() => {
    map?.remove();
  });

  async function applyFilters() {
    await loadRoutes();
    renderRoutes();
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Heatmap</h1>
    <div class="filters">
      <select bind:value={sportFilter} onchange={applyFilters}>
        <option value="">All sports</option>
        <option value="run">Run</option>
        <option value="ride">Ride</option>
        <option value="walk">Walk</option>
        <option value="hike">Hike</option>
        <option value="swim">Swim</option>
        <option value="other">Other</option>
      </select>
      <select bind:value={yearFilter} onchange={applyFilters}>
        <option value="">All years</option>
        {#each availableYears as y}
          <option value={y}>{y}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="map-container">
    <div bind:this={mapContainer} class="map"></div>
    <TileSelector onTileChange={handleTileChange} />
  </div>

  {#if loading}
    <LoadingSpinner />
  {:else if error}
    <ErrorBanner message={error} retry={() => { loadRoutes(); renderRoutes(); }} />
  {:else if routes.length === 0}
    <EmptyState icon="heatmap" message="No routes found. Upload some activities to see them here." />
  {:else}
    <div class="route-count">
      {routes.length} route{routes.length !== 1 ? 's' : ''} ·
      {(routes.reduce((s, r) => s + r.distance_m, 0) / 1000).toFixed(0)} km total
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
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    margin: 0;
  }
  .filters {
    display: flex;
    gap: 8px;
  }
  .filters select {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: var(--surface);
    color: var(--text);
  }
  .filters select:focus {
    outline: none;
    border-color: var(--primary);
  }
  .map-container {
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 12px;
  }
  .map {
    height: 600px;
  }
  .route-count {
    font-size: 14px;
    color: var(--text-secondary);
    text-align: center;
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: 22px; }
    .page-header { flex-direction: column; align-items: flex-start; }
    .filters { width: 100%; }
    .filters select { flex: 1; }
    .map { height: 350px; }
  }
</style>
