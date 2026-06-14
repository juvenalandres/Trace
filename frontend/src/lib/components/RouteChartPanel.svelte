<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import uPlot from 'uplot';
  import 'leaflet/dist/leaflet.css';
  import 'uplot/dist/uPlot.min.css';
  import { getSelectedTile } from '$lib/map/tiles';
  import { calculateSlope, formatSlope } from '$lib/chart/slope';

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

  interface MetricDef {
    key: string;
    label: string;
    unit: string;
    color: string;
    sports?: string[];
    factor?: number;
  }

  interface Props {
    polyline: string;
    timeSeries: string;
    sportType?: string;
    class?: string;
  }

  let { polyline, timeSeries, sportType = '', class: className = '' }: Props = $props();

  let mapContainer: HTMLDivElement;
  let chartsContainer: HTMLDivElement;
  let tooltipContainer: HTMLDivElement;

  let map: L.Map | null = null;
  let marker: L.Marker | null = null;
  let dotIcon: L.DivIcon | null = null;
  let charts: uPlot[] = [];
  let isMouseInCharts = false;
  let slopes: number[] = [];
  let points: TimePoint[] = [];
  let availableMetrics: MetricDef[] = [];
  let selectedMetrics: string[] = [];
  let mouseX = 0;
  let mouseY = 0;

  const allMetrics: MetricDef[] = [
    { key: 'ele', label: 'Elevation', unit: 'm', color: '#6b7280' },
    { key: 'hr', label: 'Heart Rate', unit: 'bpm', color: '#ef4444' },
    { key: 'spd', label: 'Speed', unit: 'km/h', color: '#22c55e', factor: 3.6 },
    { key: 'pace', label: 'Pace', unit: 'min/km', color: '#22c55e', sports: ['run', 'walk', 'hike', 'swim'] },
    { key: 'pwr', label: 'Power', unit: 'W', color: '#3b82f6' },
    { key: 'cad', label: 'Cadence', unit: 'spm', color: '#f97316' },
  ];

  function extractValue(p: TimePoint, key: string): number | null {
    const val = (p as Record<string, number | null>)[key] ?? null;
    if (val === null) return null;
    const metric = allMetrics.find(m => m.key === key);
    return metric?.factor ? val * metric.factor : val;
  }

  function detectAvailable() {
    if (points.length === 0) return;
    availableMetrics = allMetrics.filter(m => {
      if (m.sports && !m.sports.includes(sportType)) return false;
      return points.some(p => extractValue(p, m.key) !== null);
    });
    selectedMetrics = availableMetrics.slice(0, 3).map(m => m.key);
  }

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

  function updateMarker(idx: number) {
    if (!map || !points[idx]) return;
    const p = points[idx];
    if (marker) {
      marker.setLatLng([p.lat, p.lng]);
    } else {
      marker = L.marker([p.lat, p.lng], { icon: dotIcon! }).addTo(map);
    }
  }

  function destroyCharts() {
    charts.forEach(c => c.destroy());
    charts = [];
  }

  function buildCharts() {
    if (!chartsContainer || points.length === 0) return;

    destroyCharts();
    chartsContainer.innerHTML = '';

    // Calculate slopes for elevation data
    const elevations = points.map(p => p.ele ?? 0);
    const distancesM = points.map(p => p.d);
    slopes = calculateSlope(elevations, distancesM);

    const xData = points.map(p => p.d / 1000); // cumulative distance in km
    const active = availableMetrics.filter(m => selectedMetrics.includes(m.key));

    active.forEach((metric, idx) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'chart-wrapper';
      chartsContainer.appendChild(wrapper);

      const yData = points.map(p => extractValue(p, metric.key));
      const filled = yData.map(v => v ?? 0);
      const data: uPlot.AlignedData = [new Float64Array(xData), new Float64Array(filled)];

      const vals = yData.filter((v): v is number => v !== null);
      const scales: Record<string, { time?: boolean; range: (u: uPlot) => [number, number] }> = {};
      scales['x'] = { time: false };
      if (vals.length > 0) {
        const lo = Math.min(...vals);
        const hi = Math.max(...vals);
        const span = hi - lo || 1;
        scales['y'] = {
          range: () => [
            lo - span * 0.1,
            hi + span * 0.2,
          ],
        };
      }

      // Use requestAnimationFrame to ensure wrapper has correct width
      requestAnimationFrame(() => {
        const chartWidth = wrapper.clientWidth;
        if (chartWidth === 0) return;

        const chart = new uPlot({
          width: chartWidth,
          height: 100,
          padding: [4, 8, 0, 0],
          scales,
          axes: [
            { show: false },
            { stroke: '#888', grid: { stroke: '#eee' } },
          ],
          series: [
            {},
            {
              stroke: metric.color,
              width: 1.5,
              label: '',
              fill: metric.color + '1a',
              points: { show: false },
            },
          ],
          cursor: {
            drag: { x: false, y: false },
            sync: { key: 'route' },
            points: { show: false },
          },
          legend: { show: false },
          hooks: {
            setCursor: [
              (u: uPlot) => {
                const idx = u.cursor.idx;
                if (idx != null) {
                  updateMarker(idx);
                  showTooltip(idx, u);
                }
              },
            ],
          },
        }, data, wrapper);

        charts.push(chart);
      });
    });
  }

  function toggleMetric(key: string) {
    if (selectedMetrics.includes(key)) {
      if (selectedMetrics.length > 1) {
        selectedMetrics = selectedMetrics.filter(k => k !== key);
      }
    } else {
      selectedMetrics = [...selectedMetrics, key];
    }
    buildCharts();
  }

  function selectAll() {
    selectedMetrics = availableMetrics.map(m => m.key);
    buildCharts();
  }

  function selectNone() {
    selectedMetrics = [availableMetrics[0].key];
    buildCharts();
  }

  function showTooltip(idx: number, activeChart: uPlot) {
    if (!tooltipContainer || points.length === 0) return;

    const point = points[idx];
    if (!point) return;

    const active = availableMetrics.filter(m => selectedMetrics.includes(m.key));
    const dist = ((point.d / 1000) as number).toFixed(2);

    let html = `<div class="tooltip-distance">${dist} km</div>`;
    html += '<div class="tooltip-metrics">';

    active.forEach(metric => {
      const raw = (point as Record<string, number | null>)[metric.key];
      const val = raw !== null && raw !== undefined
        ? (metric.factor ? (raw * metric.factor).toFixed(1) : raw.toFixed(1))
        : '-';
      const isActive = activeChart.series[1]?.label?.includes(metric.label);
      const weight = isActive ? 'font-weight:600;' : '';
      html += `<div class="tooltip-row" style="${weight}"><span class="tooltip-dot" style="background:${metric.color}"></span>${metric.label}: ${val} ${metric.unit}</div>`;

      // Add slope row after elevation
      if (metric.key === 'ele' && slopes.length > idx) {
        const slopeFormatted = formatSlope(slopes[idx]);
        html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:${slopeFormatted.color}"></span>Slope: <span style="color:${slopeFormatted.color};font-weight:500">${slopeFormatted.text}</span> (${slopeFormatted.label})</div>`;
      }
    });

    html += '</div>';
    tooltipContainer.innerHTML = html;
    tooltipContainer.style.display = 'block';

    // Keep tooltip within viewport
    const tooltipWidth = tooltipContainer.offsetWidth;
    const tooltipHeight = tooltipContainer.offsetHeight;
    
    let finalLeft = mouseX + 15;
    let finalTop = mouseY - tooltipHeight - 10;
    
    // Adjust if going off right edge
    if (finalLeft + tooltipWidth > window.innerWidth) {
      finalLeft = mouseX - tooltipWidth - 15;
    }
    
    // Adjust if going off top
    if (finalTop < 0) {
      finalTop = mouseY + 15;
    }
    
    tooltipContainer.style.left = `${finalLeft}px`;
    tooltipContainer.style.top = `${finalTop}px`;
  }

  function hideTooltip() {
    isMouseInCharts = false;
    if (tooltipContainer) {
      tooltipContainer.style.display = 'none';
    }
  }

  function handleMouseMove(e: MouseEvent) {
    isMouseInCharts = true;
    mouseX = e.clientX;
    mouseY = e.clientY;
  }

  onMount(() => {
    if (!mapContainer || !polyline || !timeSeries) return;

    points = JSON.parse(timeSeries);
    if (points.length === 0) return;

    detectAvailable();

    const coords = decodePolyline(polyline);

    map = L.map(mapContainer, { scrollWheelZoom: false }).setView(coords[0], 14);
    const tile = getSelectedTile();
    L.tileLayer(tile.url, {
      attribution: tile.attribution,
      maxZoom: tile.maxZoom,
    }).addTo(map);

    dotIcon = L.divIcon({
      className: 'position-dot',
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });

    L.polyline(coords, { color: '#3b82f6', weight: 3 }).addTo(map);
    map.fitBounds(L.latLngBounds(coords));

    buildCharts();

    const observer = new ResizeObserver(() => {
      charts.forEach((c, i) => {
        const wrapper = chartsContainer?.children[i] as HTMLElement | undefined;
        if (wrapper) {
          const w = wrapper.clientWidth;
          if (w > 0) c.setSize({ width: w, height: 100 });
        }
      });
    });
    observer.observe(chartsContainer);

    return () => observer.disconnect();
  });

  onDestroy(() => {
    map?.remove();
    destroyCharts();
  });
</script>

<div class={className}>
  <div bind:this={mapContainer} class="map"></div>

  <div class="charts-card">
    <div class="charts-header">
      <div class="charts-title">Performance Data</div>
      {#if availableMetrics.length > 1}
        <div class="metric-actions">
          <button class="action-btn" onclick={selectAll}>All</button>
          <button class="action-btn" onclick={selectNone}>Reset</button>
        </div>
      {/if}
    </div>

    {#if availableMetrics.length > 1}
      <div class="metric-toggles">
        {#each availableMetrics as metric}
          <button
            class="toggle"
            class:active={selectedMetrics.includes(metric.key)}
            onclick={() => toggleMetric(metric.key)}
          >
            <span class="toggle-dot" style="background: {metric.color}"></span>
            {metric.label}
          </button>
        {/each}
      </div>
    {/if}

    <div bind:this={chartsContainer} class="charts" onmouseleave={hideTooltip} onmousemove={handleMouseMove}></div>
  </div>
  <div bind:this={tooltipContainer} class="chart-tooltip" style="display: none;"></div>
</div>

<style>
  .map {
    height: 400px;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 12px;
  }
  .charts-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .charts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
  }
  .charts-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text);
  }
  .metric-actions {
    display: flex;
    gap: 4px;
  }
  .action-btn {
    padding: 4px 10px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg);
    color: var(--text-secondary);
    font-size: 11px;
    cursor: pointer;
  }
  .action-btn:hover {
    background: var(--hover);
    color: var(--text);
  }
  .metric-toggles {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    padding: 0 16px 12px;
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }
  .toggle:hover {
    background: var(--hover);
    color: var(--text);
  }
  .toggle.active {
    border-color: var(--primary);
    background: var(--primary-light);
    color: var(--primary);
  }
  .toggle-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .charts {
    display: flex;
    flex-direction: column;
    padding: 0 16px 16px;
    position: relative;
    overflow-x: hidden;
  }
  .chart-wrapper {
    margin: 4px 0;
    width: 100%;
    overflow: hidden;
  }
  :global(.position-dot) {
    width: 12px;
    height: 12px;
    background: var(--primary);
    border: 2px solid white;
    border-radius: 50%;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }
  .chart-tooltip {
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
  :global(.tooltip-distance) {
    font-weight: 600;
    font-size: 13px;
    color: var(--text);
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border-light);
  }
  :global(.tooltip-metrics) {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  :global(.tooltip-row) {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text);
  }
  :global(.tooltip-dot) {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  @media (max-width: 768px) {
    .map { height: 250px; }
    .charts { padding: 0 8px 8px; }
    .metric-toggles { padding: 0 8px 8px; }
  }
</style>
