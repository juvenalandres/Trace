<script lang="ts">
  import Icon from '$lib/components/Icon.svelte';
  import type { Lap } from '$lib/api/types';

  let { laps, sport_type }: { laps: Lap[]; sport_type: string } = $props();

  interface Split {
    label: string;
    distance_km: number;
    duration_s: number;
    value: number;
    valueLabel: string;
  }

  const isRun = sport_type === 'run';
  const isRide = sport_type === 'ride';

  let groupSize = $state(5);
  let customGroupSize = $state('');

  function setGroupSize(size: number) {
    groupSize = size;
    customGroupSize = '';
  }

  function handleCustomInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    customGroupSize = val;
    const num = parseInt(val, 10);
    if (num >= 1 && num <= 100) {
      groupSize = num;
    }
  }

  const splits: Split[] = $derived.by(() => {
    if (!laps || laps.length === 0) return [];

    if (isRide) {
      const groups: Split[] = [];
      for (let i = 0; i < laps.length; i += groupSize) {
        const chunk = laps.slice(i, i + groupSize);
        const dist = chunk.reduce((s, l) => s + (l.distance_m ?? 0), 0);
        const dur = chunk.reduce((s, l) => s + (l.duration_s ?? 0), 0);
        const avgSpd = dist > 0 && dur > 0 ? dist / dur : 0;
        const from = i + 1;
        const to = Math.min(i + groupSize, laps.length);
        const label = from === to ? `${from} km` : `${from}–${to} km`;
        groups.push({
          label,
          distance_km: dist / 1000,
          duration_s: dur,
          value: avgSpd * 3.6,
          valueLabel: `${(avgSpd * 3.6).toFixed(1)} km/h`,
        });
      }
      return groups;
    }

    return laps.map((lap) => {
      const avgSpd = lap.avg_speed ?? 0;
      const pace = avgSpd > 0 ? 1000 / avgSpd / 60 : 0;
      const min = Math.floor(pace);
      const sec = Math.floor((pace - min) * 60);
      return {
        label: `Km ${lap.lap_index + 1}`,
        distance_km: (lap.distance_m ?? 0) / 1000,
        duration_s: lap.duration_s ?? 0,
        value: pace,
        valueLabel: `${min}:${sec.toString().padStart(2, '0')} min/km`,
      };
    });
  });

  const barWidths: number[] = $derived.by(() => {
    if (splits.length === 0) return [];
    const vals = splits.map((s) => s.value).filter((v) => v > 0);
    if (vals.length === 0) return splits.map(() => 0);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const range = max - min || 1;
    return splits.map((s) => (s.value > 0 ? ((s.value - min) / range) * 80 + 20 : 0));
  });

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  const headerLabel = $derived.by(() => {
    if (!isRide) return 'Km splits';
    return `${groupSize} km splits`;
  });
</script>

{#if splits.length > 0}
  <div class="split-card">
    <div class="split-header">
      <div class="split-title">
        <div class="split-icon">
          <Icon name="distance" size={15} />
        </div>
        <span class="split-label">{headerLabel}</span>
      </div>
      {#if isRide}
        <div class="split-group-btns">
          <button
            class="split-group-btn"
            class:active={groupSize === 5}
            onclick={() => setGroupSize(5)}
          >5 km</button>
          <button
            class="split-group-btn"
            class:active={groupSize === 10}
            onclick={() => setGroupSize(10)}
          >10 km</button>
          <div class="split-custom-input">
            <input
              type="number"
              min="1"
              max="100"
              placeholder="km"
              value={customGroupSize}
              oninput={handleCustomInput}
              class:active={groupSize !== 5 && groupSize !== 10}
            />
          </div>
        </div>
      {:else}
        <span class="split-unit">PACE</span>
      {/if}
    </div>

    <div class="split-table">
      <div class="split-row split-header-row">
        <span class="split-col-label"></span>
        <span class="split-col-label">Duration</span>
        <span class="split-col-label">{isRide ? 'Avg Speed' : 'Pace'}</span>
      </div>
      {#each splits as split, i}
        <div class="split-row" class:split-last={i === splits.length - 1}>
          <span class="split-col split-label">{split.label}</span>
          <span class="split-col split-duration">{formatDuration(split.duration_s)}</span>
          <span class="split-col split-bar-cell">
            <div class="split-bar-track">
              <div
                class="split-bar"
                class:bar-run={isRun}
                class:bar-ride={isRide}
                style="width: {barWidths[i]}%"
              ></div>
            </div>
            <span class="split-value">{split.valueLabel}</span>
          </span>
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .split-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .split-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .split-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .split-icon {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: var(--primary-bg, color-mix(in srgb, var(--primary) 10%, transparent));
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary);
  }
  .split-label {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-primary, var(--text));
  }
  .split-unit {
    font-size: var(--font-size-xs, 10px);
    font-weight: var(--font-weight-semibold, 600);
    color: var(--text-tertiary, #999);
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 6px;
    background: var(--bg, #f5f5f5);
  }

  .split-group-btns {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .split-group-btn {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary, #666);
    background: var(--bg, #f5f5f5);
    border: 0.5px solid var(--border, rgba(0, 0, 0, 0.06));
    border-radius: 6px;
    padding: 4px 10px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .split-group-btn:hover {
    background: var(--border, rgba(0, 0, 0, 0.08));
  }
  .split-group-btn.active {
    background: var(--primary, #3b82f6);
    color: white;
    border-color: var(--primary, #3b82f6);
  }
  .split-custom-input {
    position: relative;
  }
  .split-custom-input input {
    width: 52px;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary, #666);
    background: var(--bg, #f5f5f5);
    border: 0.5px solid var(--border, rgba(0, 0, 0, 0.06));
    border-radius: 6px;
    padding: 4px 6px;
    text-align: center;
    outline: none;
    transition: all 0.15s ease;
    -moz-appearance: textfield;
  }
  .split-custom-input input::-webkit-outer-spin-button,
  .split-custom-input input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  .split-custom-input input:focus,
  .split-custom-input input.active {
    border-color: var(--primary, #3b82f6);
    background: var(--card-bg, white);
    color: var(--text-primary, var(--text));
  }
  .split-custom-input input::placeholder {
    color: var(--text-tertiary, #999);
  }

  .split-table {
    display: flex;
    flex-direction: column;
  }
  .split-row {
    display: grid;
    grid-template-columns: 70px 60px 1fr;
    align-items: center;
    gap: 8px;
    padding: 7px 0;
    border-bottom: 0.5px solid var(--border, rgba(0, 0, 0, 0.06));
  }
  .split-header-row {
    padding-bottom: 6px;
  }
  .split-header-row .split-col-label {
    font-size: var(--font-size-xs, 10px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-tertiary, #999);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .split-last {
    border-bottom: none;
  }

  .split-col {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-primary, var(--text));
  }
  .split-label {
    font-weight: var(--font-weight-medium, 500);
    white-space: nowrap;
  }
  .split-duration {
    color: var(--text-secondary, #666);
    font-variant-numeric: tabular-nums;
  }

  .split-bar-cell {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .split-bar-track {
    flex: 1;
    height: 6px;
    border-radius: 3px;
    background: var(--bg, #f0f0f0);
    overflow: hidden;
  }
  .split-bar {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .bar-run {
    background: var(--primary, #3b82f6);
  }
  .bar-ride {
    background: var(--accent-teal, #14b8a6);
  }
  .split-value {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-primary, var(--text));
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    min-width: 85px;
    text-align: right;
  }
</style>
