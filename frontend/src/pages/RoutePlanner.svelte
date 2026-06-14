<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { routeApi } from '$lib/api/types';
  import type { Route, Waypoint, ElevationPoint } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import TileSelector from '$lib/components/TileSelector.svelte';
  import { getSelectedTile, type TileProvider } from '$lib/map/tiles';
  import { calculateSlope, formatSlope } from '$lib/chart/slope';

  let mapContainer: HTMLDivElement;
  let map: L.Map | null = null;
  let currentTileLayer: L.TileLayer | null = null;
  let chartContainer: HTMLDivElement;
  let chart: uPlot | null = null;
  let tooltipEl: HTMLDivElement;

  let waypoints = $state<Waypoint[]>([]);
  let routePolyline = $state<string | null>(null);
  let routeCoords = $state<[number, number][]>([]);
  let distanceM = $state(0);
  let elevationProfile = $state<ElevationPoint[]>([]);
  let elevationGain = $state(0);
  let elevationLoss = $state(0);

  let markers: L.Marker[] = [];
  let routeLine: L.Polyline | null = null;
  let cursorMarker: L.Marker | null = null;
  let sampledIndices: number[] = [];

  let loading = $state(false);
  let planning = $state(false);
  let error = $state('');
  let showSaveModal = $state(false);
  let showLoadModal = $state(false);
  let routeName = $state('');
  let savedRoutes = $state<Route[]>([]);

  const waypointIcon = L.divIcon({
    className: 'waypoint-marker',
    html: '<div class="waypoint-dot"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

  const startIcon = L.divIcon({
    className: 'waypoint-marker start',
    html: '<div class="waypoint-dot start"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });

  const endIcon = L.divIcon({
    className: 'waypoint-marker end',
    html: '<div class="waypoint-dot end"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });

  const cursorDotIcon = L.divIcon({
    className: 'cursor-marker',
    html: '<div class="cursor-dot"></div>',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

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

  function formatDistance(m: number): string {
    return (m / 1000).toFixed(1);
  }

  function formatElevation(m: number): string {
    return Math.round(m).toString();
  }

  function getMarkerIcon(index: number, total: number): L.DivIcon {
    if (index === 0) return startIcon;
    if (index === total - 1) return endIcon;
    return waypointIcon;
  }

  function addMarker(latlng: L.LatLng, index: number) {
    if (!map) return;
    const icon = getMarkerIcon(index, waypoints.length);
    const marker = L.marker(latlng, { icon, draggable: true }).addTo(map);

    marker.on('dragend', () => {
      const pos = marker.getLatLng();
      waypoints[index] = { lat: pos.lat, lng: pos.lng };
      planRoute();
    });

    marker.on('contextmenu', () => {
      removeWaypoint(index);
    });

    markers.push(marker);
  }

  function clearMarkers() {
    markers.forEach(m => m?.remove());
    markers = [];
  }

  function redrawMarkers() {
    clearMarkers();
    waypoints.forEach((wp, i) => {
      addMarker(L.latLng(wp.lat, wp.lng), i);
    });
  }

  function removeWaypoint(index: number) {
    waypoints = waypoints.filter((_, i) => i !== index);
    redrawMarkers();
    if (waypoints.length >= 2) {
      planRoute();
    } else {
      clearRoute();
    }
  }

  function clearRoute() {
    routePolyline = null;
    routeCoords = [];
    distanceM = 0;
    elevationProfile = [];
    elevationGain = 0;
    elevationLoss = 0;
    routeLine?.remove();
    routeLine = null;
    cursorMarker?.remove();
    cursorMarker = null;
    sampledIndices = [];
    chart?.destroy();
    chart = null;
  }

  function hideCursorMarker() {
    if (tooltipEl) tooltipEl.style.display = 'none';
    if (cursorMarker) {
      cursorMarker.remove();
      cursorMarker = null;
    }
  }

  function newRoute() {
    waypoints = [];
    clearMarkers();
    clearRoute();
    routeName = '';
  }

  async function planRoute() {
    if (waypoints.length < 2) return;

    planning = true;
    error = '';
    try {
      const result = await routeApi.plan(waypoints);
      routePolyline = result.polyline;
      distanceM = result.distance_m;
      routeCoords = decodePolyline(result.polyline);

      if (routeLine) routeLine.remove();
      if (map && routeCoords.length > 1) {
        routeLine = L.polyline(routeCoords, {
          color: '#3b82f6',
          weight: 4,
          opacity: 0.8,
        }).addTo(map);
      }

      await fetchElevation();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to plan route';
    } finally {
      planning = false;
    }
  }

  async function fetchElevation() {
    if (routeCoords.length < 2) return;

    const step = Math.max(1, Math.floor(routeCoords.length / 100));
    const sampled: Waypoint[] = [];
    sampledIndices = [];
    for (let i = 0; i < routeCoords.length; i += step) {
      sampled.push({ lat: routeCoords[i][0], lng: routeCoords[i][1] });
      sampledIndices.push(i);
    }
    if (sampled.length > 0 && (sampled[sampled.length - 1].lat !== routeCoords[routeCoords.length - 1][0] || sampled[sampled.length - 1].lng !== routeCoords[routeCoords.length - 1][1])) {
      sampled.push({ lat: routeCoords[routeCoords.length - 1][0], lng: routeCoords[routeCoords.length - 1][1] });
      sampledIndices.push(routeCoords.length - 1);
    }

    try {
      const result = await routeApi.elevation(sampled.slice(0, 100));
      elevationProfile = result.elevation_profile;
      elevationGain = result.elevation_gain_m;
      elevationLoss = result.elevation_loss_m;
      setTimeout(() => buildChart(), 50);
    } catch (e: unknown) {
      console.error('Failed to fetch elevation:', e);
    }
  }

  function buildChart() {
    if (!chartContainer || elevationProfile.length < 2) return;

    chart?.destroy();
    cursorMarker?.remove();
    cursorMarker = null;

    const distances = elevationProfile.map(p => p.distance / 1000);
    const elevations = elevationProfile.map(p => p.elevation);
    const distancesM = elevationProfile.map(p => p.distance);
    const slopes = calculateSlope(elevations, distancesM);

    const plotData: uPlot.AlignedData = [
      new Float64Array(distances),
      new Float64Array(elevations),
    ];

    chart = new uPlot({
      width: chartContainer.clientWidth,
      height: 160,
      padding: [10, 40, 15, 0],
      cursor: {
        x: {
          formatter: (_u, val) => `${val.toFixed(1)} km`,
        },
        points: {
          size: 4,
          fill: '#3b82f6',
          stroke: '#fff',
          width: 1.5,
        },
      },
      axes: [
        {
          stroke: '#888',
          grid: { show: false },
          values: (_u, ticks) => ticks.map(t => `${t.toFixed(1)} km`),
        },
        {
          stroke: '#888',
          grid: { stroke: '#eee' },
          values: (_u, ticks) => ticks.map(t => `${Math.round(t)} m`),
        },
      ],
      series: [
        {},
        {
          stroke: '#3b82f6',
          fill: '#3b82f620',
          width: 1.5,
          points: { show: false },
          spline: 0.3,
        },
      ],
      legend: { show: false },
      hooks: {
        setCursor: [
          (u: uPlot) => {
            const idx = u.cursor.idx;
            if (idx != null && tooltipEl) {
              const dist = distances[idx];
              const ele = elevations[idx];
              const slope = slopes[idx];
              if (dist != null && ele != null) {
                const slopeFormatted = formatSlope(slope);
                tooltipEl.innerHTML = `${dist.toFixed(1)} km · <strong>${Math.round(ele)} m</strong> · <span style="color:${slopeFormatted.color}">${slopeFormatted.text}</span>`;
                tooltipEl.style.display = 'block';
                const rect = chartContainer.getBoundingClientRect();
                const left = u.cursor.left ?? 0;
                tooltipEl.style.left = `${Math.min(left + 12, rect.width - 140)}px`;
                tooltipEl.style.top = '4px';
              }

              // Update cursor marker on map
              if (map && sampledIndices.length > idx) {
                const coordIdx = sampledIndices[idx];
                if (coordIdx < routeCoords.length) {
                  const latlng = L.latLng(routeCoords[coordIdx][0], routeCoords[coordIdx][1]);
                  if (cursorMarker) {
                    cursorMarker.setLatLng(latlng);
                  } else {
                    cursorMarker = L.marker(latlng, { icon: cursorDotIcon, interactive: false }).addTo(map);
                  }
                }
              }
            }
          },
        ],
      },
    }, plotData, chartContainer);

    const resizeObserver = new ResizeObserver(() => {
      if (chart && chartContainer) {
        chart.setSize({ width: chartContainer.clientWidth, height: 160 });
      }
    });
    resizeObserver.observe(chartContainer);
  }

  function handleMapClick(e: L.LeafletMouseEvent) {
    if (planning) return;
    const wp: Waypoint = { lat: e.latlng.lat, lng: e.latlng.lng };
    waypoints = [...waypoints, wp];
    addMarker(e.latlng, waypoints.length - 1);
    if (waypoints.length >= 2) {
      planRoute();
    }
  }

  function haversineDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const toRad = (d: number) => d * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLng = toRad(lng2 - lng1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
    return 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function interpolateElevation(targetDist: number): number | null {
    if (elevationProfile.length < 2) return null;
    if (targetDist <= elevationProfile[0].distance) return elevationProfile[0].elevation;
    if (targetDist >= elevationProfile[elevationProfile.length - 1].distance) return elevationProfile[elevationProfile.length - 1].elevation;
    for (let i = 0; i < elevationProfile.length - 1; i++) {
      const d0 = elevationProfile[i].distance;
      const d1 = elevationProfile[i + 1].distance;
      if (targetDist >= d0 && targetDist <= d1) {
        const t = (targetDist - d0) / (d1 - d0);
        return elevationProfile[i].elevation + t * (elevationProfile[i + 1].elevation - elevationProfile[i].elevation);
      }
    }
    return elevationProfile[elevationProfile.length - 1].elevation;
  }

  function generateGpx(): string {
    const name = routeName || 'Route';

    const wpts = waypoints.map((wp) => {
      let ele = '';
      if (elevationProfile.length > 0) {
        let bestDist = Infinity;
        let bestEle = 0;
        for (const p of elevationProfile) {
          const d = haversineDistance(wp.lat, wp.lng, 0, 0);
          if (Math.abs(p.distance - d) < bestDist) {
            bestDist = Math.abs(p.distance - d);
            bestEle = p.elevation;
          }
        }
        ele = Math.round(bestEle).toString();
      }
      return `  <wpt lat="${wp.lat}" lon="${wp.lng}">${ele ? `\n    <ele>${ele}</ele>` : ''}\n  </wpt>`;
    }).join('\n');

    let cumulativeDist = 0;
    const trkpts = routeCoords.map((coord, i) => {
      if (i > 0) {
        const prev = routeCoords[i - 1];
        cumulativeDist += haversineDistance(prev[0], prev[1], coord[0], coord[1]);
      }
      const eleVal = interpolateElevation(cumulativeDist);
      const ele = eleVal !== null ? Math.round(eleVal).toString() : '';
      return `    <trkpt lat="${coord[0]}" lon="${coord[1]}">${ele ? `<ele>${ele}</ele>` : ''}</trkpt>`;
    }).join('\n');

    return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Trace">
  <name>${name}</name>
${wpts}
  <trk>
    <name>${name}</name>
    <trkseg>
${trkpts}
    </trkseg>
  </trk>
</gpx>`;
  }

  async function saveRoute() {
    if (!routeName.trim() || waypoints.length < 2) return;

    try {
      const gpxContent = generateGpx();
      await routeApi.create({
        name: routeName.trim(),
        waypoints,
        route_polyline: routePolyline ?? undefined,
        distance_m: distanceM,
        elevation_gain_m: elevationGain || undefined,
        elevation_loss_m: elevationLoss || undefined,
        elevation_profile: elevationProfile.length > 0 ? elevationProfile : undefined,
      });
      showSaveModal = false;
      routeName = '';
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save route';
    }
  }

  async function loadRoutes() {
    try {
      savedRoutes = await routeApi.list();
    } catch {
      savedRoutes = [];
    }
  }

  function loadRoute(route: Route) {
    waypoints = route.waypoints;
    routePolyline = route.route_polyline;
    distanceM = route.distance_m;
    elevationProfile = route.elevation_profile;
    elevationGain = route.elevation_gain_m ?? 0;
    elevationLoss = route.elevation_loss_m ?? 0;
    routeName = route.name;

    if (routePolyline) {
      routeCoords = decodePolyline(routePolyline);
    }

    // Generate sampledIndices from routeCoords and elevationProfile
    sampledIndices = [];
    if (routeCoords.length > 0 && elevationProfile.length > 0) {
      const step = Math.max(1, Math.floor(routeCoords.length / elevationProfile.length));
      for (let i = 0; i < elevationProfile.length; i++) {
        const idx = Math.min(i * step, routeCoords.length - 1);
        sampledIndices.push(idx);
      }
    }

    redrawMarkers();
    if (routeLine) routeLine.remove();
    if (map && routeCoords.length > 1) {
      routeLine = L.polyline(routeCoords, {
        color: '#3b82f6',
        weight: 4,
        opacity: 0.8,
      }).addTo(map);

      const bounds = L.latLngBounds(routeCoords);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
    showLoadModal = false;
    setTimeout(() => buildChart(), 50);
  }

  async function deleteRoute(id: number) {
    try {
      await routeApi.delete(id);
      await loadRoutes();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete route';
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

  onMount(() => {
    if (!mapContainer) return;

    map = L.map(mapContainer, { scrollWheelZoom: true }).setView([40.0, -3.7], 5);
    const tile = getSelectedTile();
    currentTileLayer = L.tileLayer(tile.url, {
      attribution: tile.attribution,
      maxZoom: tile.maxZoom,
    }).addTo(map);

    map.on('click', handleMapClick);

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          map?.setView([latitude, longitude], 13);
        },
        () => {
          // Permission denied or error - keep default view
        }
      );
    }

    loadRoutes();
  });

  onDestroy(() => {
    map?.off('click', handleMapClick);
    map?.remove();
    chart?.destroy();
  });
</script>

<div class="page">
  <div class="page-header">
    <h1>Route Planner</h1>
    <div class="header-actions">
      <button class="btn btn-outline" onclick={newRoute}>
        <Icon name="plus" size={16} />
        New
      </button>
      <button class="btn btn-outline" onclick={() => { loadRoutes(); showLoadModal = true; }}>
        <Icon name="upload" size={16} />
        Load
      </button>
      {#if waypoints.length >= 2}
        <button class="btn btn-primary" onclick={() => { routeName = routeName || 'My Route'; showSaveModal = true; }}>
          <Icon name="save" size={16} />
          Save
        </button>
      {/if}
    </div>
  </div>

  {#if error}
    <ErrorBanner message={error} />
  {/if}

  <div class="map-container">
    <div bind:this={mapContainer} class="map"></div>
    <TileSelector onTileChange={handleTileChange} />
    {#if planning}
      <div class="planning-overlay">
        <LoadingSpinner size="sm" />
        <span>Planning route...</span>
      </div>
    {/if}
  </div>

  {#if distanceM > 0}
    <div class="route-bar">
      <div class="route-stat">
        <span class="stat-value">{formatDistance(distanceM)} km</span>
        <span class="stat-label">Distance</span>
      </div>
      {#if elevationGain > 0}
        <div class="route-stat">
          <span class="stat-value elev-up">+{formatElevation(elevationGain)} m</span>
          <span class="stat-label">Elevation</span>
        </div>
      {/if}
      {#if elevationLoss > 0}
        <div class="route-stat">
          <span class="stat-value elev-down">-{formatElevation(elevationLoss)} m</span>
          <span class="stat-label">Descent</span>
        </div>
      {/if}
      <div class="route-stat">
        <span class="stat-value">{waypoints.length}</span>
        <span class="stat-label">Waypoints</span>
      </div>
      <div class="route-actions">
        <a class="btn btn-outline btn-sm" href={routePolyline ? `data:application/gpx+xml,${encodeURIComponent(generateGpx())}` : '#'} download="{routeName || 'route'}.gpx">
          <Icon name="download" size={14} />
          Export GPX
        </a>
      </div>
    </div>
  {/if}

  {#if elevationProfile.length > 1}
    <div class="elevation-card dash-card">
      <div class="card-header">
        <h3>Elevation Profile</h3>
      </div>
      <div class="chart-wrapper" onmouseleave={hideCursorMarker}>
        <div bind:this={chartContainer} class="chart-container"></div>
        <div bind:this={tooltipEl} class="chart-tooltip" style="display:none"></div>
      </div>
    </div>
  {/if}
</div>

<Modal open={showSaveModal} onClose={() => showSaveModal = false}>
  <div class="modal-content">
    <h3>Save Route</h3>
    <label>
      <span>Route Name</span>
      <input type="text" bind:value={routeName} placeholder="My route" />
    </label>
    <div class="modal-actions">
      <button class="btn btn-primary" onclick={saveRoute} disabled={!routeName.trim()}>Save</button>
      <button class="btn btn-outline" onclick={() => showSaveModal = false}>Cancel</button>
    </div>
  </div>
</Modal>

<Modal open={showLoadModal} onClose={() => showLoadModal = false}>
  <div class="modal-content">
    <h3>Load Route</h3>
    {#if savedRoutes.length === 0}
      <p class="empty-text">No saved routes</p>
    {:else}
      <div class="route-list">
        {#each savedRoutes as route}
          <div class="route-item">
            <button class="route-item-btn" onclick={() => loadRoute(route)}>
              <span class="route-item-name">{route.name}</span>
              <span class="route-item-meta">{formatDistance(route.distance_m)} km</span>
            </button>
            <button class="btn-icon" onclick={() => deleteRoute(route.id)} title="Delete">
              <Icon name="close" size={14} />
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</Modal>

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  h1 {
    font-size: 22px;
    font-weight: 500;
    margin: 0;
  }
  .header-actions {
    display: flex;
    gap: 8px;
  }
  .map-container {
    position: relative;
    border-radius: 10px;
    overflow: hidden;
    border: 0.5px solid var(--border);
  }
  .map {
    height: 650px;
    width: 100%;
  }
  .planning-overlay {
    position: absolute;
    top: 12px;
    right: 12px;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-secondary);
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    z-index: 1000;
  }
  .route-bar {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 12px 16px;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    margin-top: 12px;
  }
  .route-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .stat-value {
    font-size: 16px;
    font-weight: 500;
    color: var(--text);
  }
  .stat-label {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .elev-up {
    color: #22c55e;
  }
  .elev-down {
    color: #ef4444;
  }
  .route-actions {
    margin-left: auto;
  }
  .elevation-card {
    margin-top: 12px;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  .card-header h3 {
    font-size: 14px;
    font-weight: 600;
    margin: 0;
    color: var(--text);
  }
  .chart-wrapper {
    position: relative;
  }
  .chart-container {
    width: 100%;
  }
  .chart-tooltip {
    position: absolute;
    top: 4px;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    color: var(--text);
    pointer-events: none;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    z-index: 10;
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
  .btn-sm {
    padding: 6px 12px;
    font-size: 13px;
  }
  .btn-primary {
    background: #3b82f6;
    color: white;
  }
  .btn-primary:hover {
    background: #2563eb;
  }
  .btn-primary:disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }
  .btn-outline {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
  }
  .btn-outline:hover {
    background: var(--hover);
  }
  .modal-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 300px;
  }
  .modal-content h3 {
    font-size: 16px;
    font-weight: 600;
    margin: 0;
  }
  .modal-content label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .modal-content label span {
    font-size: 13px;
    color: var(--text-secondary);
  }
  .modal-content input {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    font-family: var(--font-sans);
    background: var(--bg);
    color: var(--text);
  }
  .modal-content input:focus {
    outline: none;
    border-color: #3b82f6;
  }
  .modal-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
  .empty-text {
    font-size: 13px;
    color: var(--text-secondary);
    margin: 0;
  }
  .route-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 300px;
    overflow-y: auto;
  }
  .route-item {
    display: flex;
    align-items: center;
    gap: 8px;
    border-radius: 8px;
    background: var(--bg);
  }
  .route-item-btn {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 12px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
  }
  .route-item-btn:hover {
    background: var(--hover);
    border-radius: 8px;
  }
  .route-item-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }
  .route-item-meta {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .btn-icon {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
  }
  .btn-icon:hover {
    background: var(--hover);
    color: var(--text);
  }

  @media (max-width: 768px) {
    .page-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }
    .header-actions {
      width: 100%;
      flex-wrap: wrap;
    }
    .map {
      height: 400px;
    }
    .route-bar {
      flex-wrap: wrap;
      gap: 16px;
    }
  }

  :global(.waypoint-marker) {
    background: none !important;
    border: none !important;
  }
  :global(.waypoint-dot) {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #3b82f6;
    border: 2px solid white;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }
  :global(.waypoint-dot.start) {
    width: 16px;
    height: 16px;
    background: #22c55e;
  }
  :global(.waypoint-dot.end) {
    width: 16px;
    height: 16px;
    background: #ef4444;
  }
  :global(.cursor-marker) {
    background: none !important;
    border: none !important;
  }
  :global(.cursor-dot) {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #3b82f6;
    border: 2px solid white;
    box-shadow: 0 0 6px 2px rgba(59, 130, 246, 0.5);
  }
</style>
