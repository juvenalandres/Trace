<script lang="ts">
  import Icon from './Icon.svelte';

  interface TimePoint {
    pwr: number | null;
  }

  interface Props {
    avgPower: number | null;
    maxPower: number | null;
    timeSeries: string;
    zones?: { min: number; max: number }[];
  }

  let { avgPower, maxPower, timeSeries, zones }: Props = $props();

  const defaultZones = [
    { min: 0, max: 120 },
    { min: 120, max: 180 },
    { min: 180, max: 240 },
    { min: 240, max: 300 },
    { min: 300, max: 999 },
  ];

  const activeZones = zones ?? defaultZones;
  const zoneColors = ['#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8'];

  let zoneData = $state<{ label: string; percent: number; color: string }[]>([]);

  function calculateZones() {
    if (!timeSeries) return;

    const points: TimePoint[] = JSON.parse(timeSeries);
    const pwrPoints = points.filter(p => p.pwr !== null);

    if (pwrPoints.length === 0) return;

    const counts = new Array(activeZones.length).fill(0);

    for (const p of pwrPoints) {
      for (let i = 0; i < activeZones.length; i++) {
        if (p.pwr! >= activeZones[i].min && p.pwr! < activeZones[i].max) {
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
    }));
  }

  $effect(() => {
    calculateZones();
  });
</script>

<div class="pwr-card">
  <div class="pwr-header">
    <div class="pwr-title">
      <span class="pwr-icon"><Icon name="power" size={18} /></span>
      <span class="pwr-label">Power</span>
    </div>
    <span class="pwr-unit">WATTS</span>
  </div>

  <div class="pwr-summary">
    <div class="pwr-stat">
      <span class="pwr-stat-label">AVERAGE</span>
      <span class="pwr-stat-value">{avgPower ?? '-'}</span>
    </div>
    <div class="pwr-divider"></div>
    <div class="pwr-stat">
      <span class="pwr-stat-label">MAX</span>
      <span class="pwr-stat-value">{maxPower ?? '-'}</span>
    </div>
  </div>

  {#if zoneData.length > 0}
    <div class="pwr-zones">
      <div class="zones-header">TIME IN ZONE</div>
      <div class="zones-list">
        {#each zoneData as zone, i}
          <div class="zone-row">
            <span class="zone-label">{zone.label}</span>
            <div class="zone-bar-bg">
              <div
                class="zone-bar-fill"
                style="width: {zone.percent}%; background: {zone.color}"
              ></div>
            </div>
            <span class="zone-percent">{zone.percent.toFixed(1)}%</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .pwr-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .pwr-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
  }
  .pwr-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .pwr-icon {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: color-mix(in srgb, #3b82f6 12%, transparent);
    color: #3b82f6;
  }
  .pwr-label {
    font-size: 16px;
    font-weight: 700;
    color: var(--text);
  }
  .pwr-unit {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
  }
  .pwr-summary {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 16px 16px;
  }
  .pwr-stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    background: var(--bg);
    border-radius: 8px;
    padding: 12px;
  }
  .pwr-stat-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }
  .pwr-stat-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--text);
  }
  .pwr-zones {
    padding: 0 16px 16px;
  }
  .zones-header {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 12px;
  }
  .zones-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .zone-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .zone-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    width: 24px;
    flex-shrink: 0;
  }
  .zone-bar-bg {
    flex: 1;
    height: 12px;
    background: var(--bg);
    border-radius: 6px;
    overflow: hidden;
  }
  .zone-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.3s ease;
  }
  .zone-percent {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    width: 44px;
    text-align: right;
    flex-shrink: 0;
  }
</style>
