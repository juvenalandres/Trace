<script lang="ts">
  import { onDestroy } from 'svelte';
  import Modal from '$lib/components/Modal.svelte';
  import SegmentPickerMap from '$lib/components/SegmentPickerMap.svelte';
  import { segmentApi, routeApi } from '$lib/api/types';
  import type { Activity, RouteItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { calculateSlope, formatSlope } from '$lib/chart/slope';

  interface Props {
    open: boolean;
    activity?: Activity | null;
    routes?: RouteItem[];
    onClose: () => void;
    onCreated?: () => void;
  }

  let { open, activity = null, routes = [], onClose, onCreated }: Props = $props();

  let name = $state('');
  let description = $state('');
  let startCoord = $state<[number, number] | null>(null);
  let endCoord = $state<[number, number] | null>(null);
  let distance = $state<number | null>(null);
  let saving = $state(false);
  let error = $state('');
  let elevationGain = $state<number | null>(null);
  let elevationLoading = $state(false);
  let elevationError = $state('');
  let elevationChartData = $state<{ dists: Float64Array; eles: Float64Array } | null>(null);
  let elevationChartContainer: HTMLDivElement;
  let elevationChart: uPlot | null = null;
  let tooltipEl: HTMLDivElement;
  let mouseX = 0;
  let mouseY = 0;
  let tooltipData: { dists: Float64Array; eles: Float64Array; slopes: number[] } | null = null;
  let segmentCoords = $state<[number, number][]>([]);

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

  function haversine(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function handleStartSelect(lat: number, lng: number) {
    startCoord = [lat, lng];
    endCoord = null;
    distance = null;
  }

  function handleEndSelect(lat: number, lng: number) {
    endCoord = [lat, lng];
  }

  function resetPoints() {
    startCoord = null;
    endCoord = null;
    distance = null;
    segmentCoords = [];
  }

  async function handleSubmit() {
    if (!startCoord || !endCoord || !name.trim()) return;

    saving = true;
    error = '';
    try {
      await segmentApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
        sport_type: activity?.sport_type,
        start_lat: startCoord[0],
        start_lng: startCoord[1],
        end_lat: endCoord[0],
        end_lng: endCoord[1],
        polyline: segmentCoords.length >= 2 ? encodePolyline(segmentCoords) : undefined,
        distance_m: distance ?? undefined,
        elevation_gain_m: elevationGain ?? undefined,
      });
      onCreated?.();
      onClose();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to create segment';
    } finally {
      saving = false;
    }
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

  function findClosestIdx(coords: [number, number][], target: [number, number]): number {
    let minDist = Infinity, minIdx = 0;
    for (let i = 0; i < coords.length; i++) {
      const dx = coords[i][0] - target[0], dy = coords[i][1] - target[1];
      const d = dx * dx + dy * dy;
      if (d < minDist) { minDist = d; minIdx = i; }
    }
    return minIdx;
  }

  function computeActivityElevation(
    start: [number, number],
    end: [number, number],
    polylineStr: string,
    profileStr: string,
  ): { dists: Float64Array; eles: Float64Array; gain: number; coords: [number, number][]; routeDistance: number } | null {
    const coords = decodePolyline(polylineStr);
    if (coords.length < 2) return null;

    const si = findClosestIdx(coords, start);
    const ei = findClosestIdx(coords, end);
    const lo = Math.min(si, ei), hi = Math.max(si, ei);

    const cumDists = new Float64Array(coords.length);
    for (let i = 1; i < coords.length; i++) {
      cumDists[i] = cumDists[i - 1] + haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1]);
    }
    const dStart = cumDists[lo], dEnd = cumDists[hi];
    if (dEnd - dStart < 1) return null;

    const profile: [number, number][] = JSON.parse(profileStr);
    const seg: { d: number; ele: number }[] = [];
    for (const [d, ele] of profile) {
      if (d >= dStart && d <= dEnd) {
        seg.push({ d: d - dStart, ele });
      }
    }
    if (seg.length < 2) return null;

    // Smooth elevation with centered moving average (window=5)
    const rawEles = seg.map(p => p.ele);
    const halfWin = 2;
    for (let i = 0; i < rawEles.length; i++) {
      let sum = 0, count = 0;
      for (let j = Math.max(0, i - halfWin); j <= Math.min(rawEles.length - 1, i + halfWin); j++) {
        sum += rawEles[j];
        count++;
      }
      seg[i].ele = sum / count;
    }

    let gain = 0;
    for (let i = 1; i < seg.length; i++) {
      const diff = seg[i].ele - seg[i - 1].ele;
      if (diff > 0) gain += diff;
    }

    return {
      dists: new Float64Array(seg.map(p => +(p.d / 1000).toFixed(3))),
      eles: new Float64Array(seg.map(p => p.ele)),
      gain,
      coords: coords.slice(lo, hi + 1),
      routeDistance: dEnd - dStart,
    };
  }

  async function loadRoutesElevation(start: [number, number], end: [number, number]) {
    elevationLoading = true;
    elevationError = '';
    distance = null;

    try {
      let bestPolyline = '';
      let bestSi = 0, bestEi = 0;
      let bestDist = Infinity;

      for (const route of routes) {
        const coords = decodePolyline(route.polyline);
        if (coords.length < 2) continue;

        const si = findClosestIdx(coords, start);
        const ei = findClosestIdx(coords, end);
        const sDist = (coords[si][0] - start[0]) ** 2 + (coords[si][1] - start[1]) ** 2;
        const eDist = (coords[ei][0] - end[0]) ** 2 + (coords[ei][1] - end[1]) ** 2;
        const avg = (sDist + eDist) / 2;

        if (avg < bestDist) {
          bestDist = avg;
          bestPolyline = route.polyline;
          bestSi = Math.min(si, ei);
          bestEi = Math.max(si, ei);
        }
      }

      if (!bestPolyline) { elevationError = 'Could not find matching route'; return; }

      const coords = decodePolyline(bestPolyline);
      const segCoords = coords.slice(bestSi, bestEi + 1);
      if (segCoords.length < 2) { elevationError = 'Segment too short'; return; }

      const step = Math.max(1, Math.floor(segCoords.length / 100));
      const sampled = segCoords.filter((_, i) => i % step === 0 || i === segCoords.length - 1);

      const resp = await routeApi.elevation(sampled.map(c => ({ lat: c[0], lng: c[1] })));
      if (resp.elevation_profile.length < 2) { elevationError = 'Not enough elevation data'; return; }

      elevationChartData = {
        dists: new Float64Array(resp.elevation_profile.map(p => +(p.distance / 1000).toFixed(3))),
        eles: new Float64Array(resp.elevation_profile.map(p => p.elevation)),
      };
      elevationGain = resp.elevation_gain_m;
      segmentCoords = segCoords;

      // Compute actual route distance along the segment coords
      let routeDist = 0;
      for (let i = 1; i < segCoords.length; i++) {
        routeDist += haversine(segCoords[i - 1][0], segCoords[i - 1][1], segCoords[i][0], segCoords[i][1]);
      }
      distance = Math.round(routeDist);
    } catch (e: unknown) {
      elevationError = e instanceof Error ? e.message : 'Failed to load elevation';
    } finally {
      elevationLoading = false;
    }
  }

  $effect(() => {
    const start = startCoord;
    const end = endCoord;

    if (!start || !end) {
      elevationChartData = null;
      elevationGain = null;
      elevationLoading = false;
      elevationError = '';
      segmentCoords = [];
      distance = null;
      return;
    }

    // Activity mode (sync — from cached elevation_profile)
    if (activity?.stats?.elevation_profile && activity?.stats?.polyline) {
      elevationLoading = false;
      elevationError = '';
      const result = computeActivityElevation(start, end, activity.stats.polyline, activity.stats.elevation_profile);
      elevationChartData = result ? { dists: result.dists, eles: result.eles } : null;
      elevationGain = result?.gain ?? null;
      segmentCoords = result?.coords ?? [];
      distance = result ? Math.round(result.routeDistance) : null;
      return;
    }

    // Routes mode (async — fetch elevation from API)
    if (routes.length > 0) {
      elevationChartData = null;
      elevationGain = null;
      loadRoutesElevation(start, end);
      return;
    }

    elevationChartData = null;
    elevationGain = null;
  });

  function showTooltip(idx: number) {
    if (!tooltipEl || !tooltipData) return;

    const d = tooltipData.dists[idx];
    const ele = tooltipData.eles[idx];
    const slope = tooltipData.slopes[idx];

    let html = `<div class="tooltip-distance">${d.toFixed(2)} km</div>`;
    html += '<div class="tooltip-metrics">';
    html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#6b7280"></span>Elevation: ${ele.toFixed(1)} m</div>`;
    if (slope !== undefined) {
      const sf = formatSlope(slope);
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:${sf.color}"></span>Slope: <span style="color:${sf.color};font-weight:500">${sf.text}</span> (${sf.label})</div>`;
    }
    html += '</div>';

    tooltipEl.innerHTML = html;
    tooltipEl.style.display = 'block';

    const tw = tooltipEl.offsetWidth;
    const th = tooltipEl.offsetHeight;
    let left = mouseX + 15;
    let top = mouseY - th - 10;
    if (left + tw > window.innerWidth) { left = mouseX - tw - 15; }
    if (top < 0) { top = mouseY + 15; }
    tooltipEl.style.left = `${left}px`;
    tooltipEl.style.top = `${top}px`;
  }

  function hideTooltip() {
    if (tooltipEl) tooltipEl.style.display = 'none';
  }

  function handleTooltipMove(e: MouseEvent) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }

  $effect(() => {
    const data = elevationChartData;
    const container = elevationChartContainer;

    if (elevationChart) { elevationChart.destroy(); elevationChart = null; }
    tooltipData = null;
    if (!data || !container) return;

    const w = container.clientWidth;
    if (w === 0) return;

    const distsKm = Array.from(data.dists);
    const elesArr = Array.from(data.eles);
    const slopes = calculateSlope(elesArr, distsKm.map(d => d * 1000));
    tooltipData = { dists: data.dists, eles: data.eles, slopes };

    const vals = elesArr;
    const loY = Math.min(...vals), hiY = Math.max(...vals);
    const span = hiY - loY || 1;

    elevationChart = new uPlot({
      width: w,
      height: 110,
      padding: [6, 8, 0, 0],
      scales: {
        x: { time: false },
        y: { range: () => [loY - span * 0.15, hiY + span * 0.25] },
      },
      axes: [
        {
          stroke: '#888', grid: { stroke: '#eee' },
          label: 'km', size: 36, font: '11px sans-serif',
          values: (self, ticks) => ticks.map(v => v.toFixed(1)),
        },
        {
          stroke: '#888', grid: { stroke: '#eee' },
          label: 'm', size: 36, font: '11px sans-serif',
        },
      ],
      series: [
        {},
        {
          stroke: '#6b7280', width: 1.5,
          fill: '#6b72801a',
          points: { show: false },
        },
      ],
      cursor: { drag: { x: false, y: false }, points: { show: false } },
      legend: { show: false },
      hooks: {
        setCursor: [
          (u: uPlot) => {
            const idx = u.cursor.idx;
            if (idx != null) showTooltip(idx);
          },
        ],
      },
    }, [data.dists, data.eles], container);
  });

  onDestroy(() => {
    if (elevationChart) { elevationChart.destroy(); elevationChart = null; }
  });

  function handleClose() {
    if (elevationChart) { elevationChart.destroy(); elevationChart = null; }
    name = '';
    description = '';
    startCoord = null;
    endCoord = null;
    distance = null;
    error = '';
    elevationGain = null;
    elevationChartData = null;
    elevationLoading = false;
    elevationError = '';
    onClose();
  }
</script>

<Modal open={open} title="Create Segment" onClose={handleClose}>
  <div class="segment-create">
    {#if error}
      <div class="segment-error">{error}</div>
    {/if}

    <div class="segment-instructions">
      {#if !startCoord}
        <p>Click on the map to set the <strong>start point</strong> of the segment.</p>
      {:else if !endCoord}
        <p>Click on the map to set the <strong>end point</strong> of the segment.</p>
      {:else}
        <p>Start and end points set. Name your segment and save.</p>
      {/if}
    </div>

    {#if activity?.stats?.polyline}
      <SegmentPickerMap
        polyline={activity.stats.polyline}
        {startCoord}
        {endCoord}
        onStartSelect={handleStartSelect}
        onEndSelect={handleEndSelect}
      />
    {:else if routes.length > 0}
      <SegmentPickerMap
        routes={routes.map(r => ({ polyline: r.polyline }))}
        {startCoord}
        {endCoord}
        onStartSelect={handleStartSelect}
        onEndSelect={handleEndSelect}
      />
    {:else}
      <div class="no-route-data">
        No route data available. Activities with GPS tracks are needed to create segments.
      </div>
    {/if}

    <div class="segment-coords">
      {#if startCoord}
        <span class="coord coord-start">Start: {startCoord[0].toFixed(5)}, {startCoord[1].toFixed(5)}</span>
      {/if}
      {#if endCoord}
        <span class="coord coord-end">End: {endCoord[0].toFixed(5)}, {endCoord[1].toFixed(5)}</span>
      {/if}
      {#if distance}
        <span class="coord-distance">Distance: {distance >= 1000 ? (distance / 1000).toFixed(1) + ' km' : distance + ' m'}</span>
      {/if}
    </div>

    {#if startCoord && endCoord}
      <button class="btn btn-outline btn-sm" onclick={resetPoints}>Reset Points</button>
    {/if}

    {#if startCoord && endCoord && (activity?.stats?.elevation_profile || elevationLoading || elevationChartData)}
      <div class="elevation-section">
        <div class="elevation-header">
          <span>Elevation Profile</span>
          {#if elevationLoading}
            <span class="elevation-gain">Loading elevation...</span>
          {:else if elevationGain !== null}
            <span class="elevation-gain">{Math.round(elevationGain)} m gain</span>
          {/if}
        </div>
        {#if elevationError}
          <div class="elevation-error">{elevationError}</div>
        {/if}
        <div bind:this={elevationChartContainer} class="elevation-chart" onmouseleave={hideTooltip} onmousemove={handleTooltipMove}></div>
      </div>
    {/if}
    <div bind:this={tooltipEl} class="elevation-tooltip" style="display:none"></div>

    <div class="field">
      <label for="seg-name">Segment Name *</label>
      <input id="seg-name" type="text" bind:value={name} maxlength="255" placeholder="e.g. Box Hill, Alpe d'Huez" />
    </div>
    <div class="field">
      <label for="seg-desc">Description</label>
      <textarea id="seg-desc" bind:value={description} maxlength="10000" rows="2" placeholder="Optional description"></textarea>
    </div>

    <div class="form-actions">
      <button class="btn btn-outline" onclick={handleClose}>Cancel</button>
      <button
        class="btn btn-primary"
        onclick={handleSubmit}
        disabled={saving || !startCoord || !endCoord || !name.trim()}
      >
        {saving ? 'Creating...' : 'Create Segment'}
      </button>
    </div>
  </div>
</Modal>

<style>
  .segment-create {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 500px;
    max-width: 800px;
    font-family: var(--font-sans);
  }
  .segment-error {
    background: #fee2e2;
    color: #dc2626;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: var(--font-size-base, 13px);
  }
  .segment-instructions p {
    margin: 0;
    font-size: var(--font-size-base, 13px);
    color: var(--text-secondary);
  }
  .segment-coords {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    font-size: var(--font-size-xs, 11px);
    color: var(--text-secondary);
  }
  .coord {
    font-family: monospace;
  }
  .coord-start {
    color: #22c55e;
  }
  .coord-end {
    color: #ef4444;
  }
  .coord-distance {
    font-weight: 500;
    color: var(--text);
  }
  .no-route-data {
    padding: 24px;
    text-align: center;
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    background: var(--bg);
    border-radius: 8px;
    border: 0.5px solid var(--border);
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
  .field input, .field textarea {
    padding: 10px 12px;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    background: var(--bg);
    color: var(--text);
  }
  .field input:focus, .field textarea:focus {
    outline: none;
    border-color: var(--primary);
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
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
  .btn-sm {
    padding: 4px 10px;
    font-size: var(--font-size-xs, 11px);
  }
  .elevation-section {
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .elevation-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px 0;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .elevation-gain {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .elevation-error {
    padding: 8px 12px;
    font-size: var(--font-size-xs, 11px);
    color: #dc2626;
  }
  .elevation-chart {
    width: 100%;
    height: 110px;
  }
  .elevation-tooltip {
    position: fixed;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    z-index: 1000;
    pointer-events: none;
    min-width: 140px;
  }
  :global(.elevation-tooltip .tooltip-distance) {
    font-weight: 600;
    font-size: 13px;
    color: var(--text);
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border-light);
  }
  :global(.elevation-tooltip .tooltip-metrics) {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  :global(.elevation-tooltip .tooltip-row) {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text);
  }
  :global(.elevation-tooltip .tooltip-dot) {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  @media (max-width: 768px) {
    .segment-create { min-width: auto; }
  }
</style>
