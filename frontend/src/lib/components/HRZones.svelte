<script lang="ts">
  import Icon from './Icon.svelte';

  interface TimePoint {
    hr: number | null;
  }

  interface Props {
    avgHr: number | null;
    maxHr: number | null;
    timeSeries: string;
    zones?: { min: number; max: number }[];
  }

  let { avgHr, maxHr, timeSeries, zones }: Props = $props();

  const defaultZones = [
    { min: 0, max: 115 },
    { min: 115, max: 130 },
    { min: 130, max: 150 },
    { min: 150, max: 165 },
    { min: 165, max: 300 },
  ];

  const activeZones = zones ?? defaultZones;
  const zoneColors = ['#F09595', '#E24B4A', '#A32D2D', '#791F1F', '#501313'];

  let zoneData = $state<{ label: string; percent: number; color: string; range: string }[]>([]);

  function formatRange(zone: { min: number; max: number }, index: number): string {
    if (index === 0) return `< ${zone.max} bpm`;
    if (index === activeZones.length - 1) return `> ${zone.min} bpm`;
    return `${zone.min}–${zone.max}`;
  }

  function calculateZones() {
    if (!timeSeries) return;

    const points: TimePoint[] = JSON.parse(timeSeries);
    const hrPoints = points.filter(p => p.hr !== null);

    if (hrPoints.length === 0) return;

    const counts = new Array(activeZones.length).fill(0);

    for (const p of hrPoints) {
      for (let i = 0; i < activeZones.length; i++) {
        if (p.hr! >= activeZones[i].min && p.hr! < activeZones[i].max) {
          counts[i]++;
          break;
        }
      }
    }

    const total = counts.reduce((a, b) => a + b, 0);
    zoneData = activeZones.map((z, i) => ({
      label: `Z${i + 1}`,
      percent: total > 0 ? (counts[i] / total) * 100 : 0,
      color: zoneColors[i],
      range: formatRange(z, i),
    }));
  }

  $effect(() => {
    calculateZones();
  });
</script>

<div class="hr-card">
  <div class="hr-header">
    <div class="hr-title">
      <div class="hr-icon">
        <Icon name="heart" size={15} />
      </div>
      <span class="hr-label">Heart rate</span>
    </div>
    <span class="hr-unit">BPM</span>
  </div>

  <div class="hr-stats">
    <div class="hr-stat">
      <span class="hr-stat-label">Average</span>
      <span class="hr-stat-value">{avgHr ?? '-'}<span class="hr-stat-unit">bpm</span></span>
    </div>
    <div class="hr-stat">
      <span class="hr-stat-label">Max</span>
      <span class="hr-stat-value">{maxHr ?? '-'}<span class="hr-stat-unit">bpm</span></span>
    </div>
  </div>

  {#if zoneData.length > 0}
    <div class="hr-zones">
      <div class="zones-header">Time in zone</div>
      <div class="zones-list">
        {#each zoneData as zone, i}
          <div class="zone-row" class:zone-last={i === zoneData.length - 1}>
            <span class="zone-label">{zone.label}</span>
            <div class="zone-bar-track">
              <div
                class="zone-bar-fill"
                style="width: {zone.percent}%; background: {zone.color}"
              ></div>
            </div>
            <span class="zone-percent">{zone.percent.toFixed(1)}%</span>
            <span class="zone-range">{zone.range}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .hr-card {
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
    width: 100%;
    box-sizing: border-box;
    display: block;
    min-width: 0;
  }

  .hr-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.1rem;
  }

  .hr-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .hr-icon {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    background: #FBEAF0;
    color: #993556;
  }

  .hr-label {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }

  .hr-unit {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    background: var(--bg);
    border: 0.5px solid var(--border);
    border-radius: 6px;
    padding: 3px 8px;
  }

  .hr-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 1.1rem;
  }

  .hr-stat {
    background: var(--bg);
    border-radius: 8px;
    padding: 0.85rem 1rem;
  }

  .hr-stat-label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }

  .hr-stat-value {
    font-size: 26px;
    font-weight: 500;
    color: var(--text);
  }

  .hr-stat-unit {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-left: 3px;
  }

  .hr-zones {
    margin-top: 10px;
  }

  .zones-header {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-bottom: 10px;
  }

  .zones-list {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }

  .zone-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .zone-row.zone-last {
    margin-bottom: 0;
  }

  .zone-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    width: 20px;
    flex-shrink: 0;
    text-align: right;
  }

  .zone-bar-track {
    flex: 1;
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
  }

  .zone-bar-fill {
    height: 6px;
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .zone-percent {
    font-size: 12px;
    font-weight: 400;
    color: var(--text-secondary);
    width: 38px;
    text-align: right;
    flex-shrink: 0;
  }

  .zone-range {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    width: 70px;
    text-align: right;
    flex-shrink: 0;
  }
</style>
