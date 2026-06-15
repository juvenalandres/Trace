<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import { getSelectedTile } from '$lib/map/tiles';

  interface RouteOverlay {
    polyline: string;
    color?: string;
  }

  interface Props {
    polyline?: string;
    startCoord?: [number, number] | null;
    endCoord?: [number, number] | null;
    routes?: RouteOverlay[];
    onStartSelect?: (lat: number, lng: number) => void;
    onEndSelect?: (lat: number, lng: number) => void;
    onClear?: () => void;
  }

  let { polyline = '', startCoord = null, endCoord = null, routes = [], onStartSelect, onEndSelect, onClear }: Props = $props();

  let mapContainer: HTMLDivElement;
  let map: L.Map | null = null;
  let startMarker: L.Marker | null = null;
  let endMarker: L.Marker | null = null;
  let routePolyline: L.Polyline | null = null;
  let routeLayers: L.Polyline[] = [];
  let clickCount = 0;

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

  function createMarker(lat: number, lng: number, color: string): L.Marker {
    return L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'segment-marker',
        html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    });
  }

  function updateMarkers() {
    if (!map) return;
    if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
    if (endMarker) { map.removeLayer(endMarker); endMarker = null; }

    if (startCoord) {
      startMarker = createMarker(startCoord[0], startCoord[1], '#22c55e').addTo(map);
    }
    if (endCoord) {
      endMarker = createMarker(endCoord[0], endCoord[1], '#ef4444').addTo(map);
    }

    clickCount = startCoord ? (endCoord ? 2 : 1) : 0;
  }

  function drawRoutes() {
    if (!map) return;
    for (const layer of routeLayers) {
      map.removeLayer(layer);
    }
    routeLayers = [];

    for (const route of routes) {
      const coords = decodePolyline(route.polyline);
      if (coords.length === 0) continue;
      const layer = L.polyline(coords, {
        color: route.color ?? '#94a3b8',
        weight: 2,
        opacity: 0.4,
      }).addTo(map);
      routeLayers.push(layer);
    }
  }

  function fitAllBounds() {
    if (!map) return;
    const allCoords: [number, number][] = [];

    if (polyline) {
      allCoords.push(...decodePolyline(polyline));
    }
    for (const route of routes) {
      allCoords.push(...decodePolyline(route.polyline));
    }

    if (allCoords.length > 0) {
      map.fitBounds(L.latLngBounds(allCoords));
    }
  }

  onMount(() => {
    if (!mapContainer) return;

    map = L.map(mapContainer).setView([0, 0], 2);
    const tile = getSelectedTile();
    L.tileLayer(tile.url, { attribution: tile.attribution, maxZoom: tile.maxZoom }).addTo(map);

    if (polyline) {
      const coords = decodePolyline(polyline);
      if (coords.length > 0) {
        routePolyline = L.polyline(coords, { color: '#3b82f6', weight: 3 }).addTo(map);
      }
    }

    drawRoutes();
    fitAllBounds();

    map.on('click', (e: L.LeafletMouseEvent) => {
      const lat = Math.round(e.latlng.lat * 100000) / 100000;
      const lng = Math.round(e.latlng.lng * 100000) / 100000;
      if (clickCount === 0) {
        onStartSelect?.(lat, lng);
      } else {
        onEndSelect?.(lat, lng);
      }
    });

    updateMarkers();
  });

  onDestroy(() => {
    if (map) {
      if (startMarker) map.removeLayer(startMarker);
      if (endMarker) map.removeLayer(endMarker);
      if (routePolyline) map.removeLayer(routePolyline);
      for (const layer of routeLayers) {
        map.removeLayer(layer);
      }
      map.remove();
      map = null;
    }
  });

  $effect(() => {
    if (map) {
      updateMarkers();
    }
  });

  $effect(() => {
    if (map && routes.length > 0) {
      drawRoutes();
      fitAllBounds();
    }
  });
</script>

<div bind:this={mapContainer} class="picker-map"></div>

<style>
  .picker-map {
    width: 100%;
    height: 400px;
    border-radius: 8px;
    border: 0.5px solid var(--border);
    z-index: 0;
  }
</style>
