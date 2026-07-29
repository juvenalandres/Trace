<script lang="ts">
  import type { Workout, WorkoutStep, Duration, Distance } from '$lib/api/types';

  let { workout }: { workout: Workout | null } = $props();

  function durSec(d: Duration | null): number {
    if (!d) return 0;
    switch (d.unit) {
      case 's': return d.value;
      case 'min': return d.value * 60;
      case 'h': return d.value * 3600;
      default: return d.value * 60;
    }
  }

  function distKm(d: Distance | null): number {
    if (!d) return 0;
    switch (d.unit) {
      case 'km': return d.value;
      case 'm': return d.value / 1000;
      case 'mi': return d.value * 1.60934;
      default: return d.value;
    }
  }

  const stepColors: Record<string, string> = {
    warmup: '#3b82f6', interval: '#ef4444', recovery: '#22c55e',
    cooldown: '#3b82f6', rest: '#6b7280', other: '#8b5cf6',
  };

  interface Stats {
    totalSec: number;
    totalKm: number;
    stepCount: number;
    intervals: number;
    timeByType: Record<string, number>;
    stepsByType: Record<string, number>;
  }

  function compute(w: Workout | null): Stats | null {
    if (!w?.blocks.length) return null;
    const s: Stats = { totalSec: 0, totalKm: 0, stepCount: 0, intervals: 0, timeByType: {}, stepsByType: {} };

    function walk(steps: WorkoutStep[], mult: number) {
      for (const st of steps) {
        if (st.type === 'repeat' && st.steps) {
          walk(st.steps, mult * (st.repetitions ?? 1));
        } else {
          const d = durSec(st.duration);
          const km = distKm(st.distance);
          s.totalSec += d * mult;
          s.totalKm += km * mult;
          s.stepCount += mult;
          if (st.type === 'interval') s.intervals += mult;
          s.timeByType[st.type] = (s.timeByType[st.type] ?? 0) + d * mult;
          s.stepsByType[st.type] = (s.stepsByType[st.type] ?? 0) + mult;
        }
      }
    }

    for (const block of w.blocks) walk(block.steps, 1);
    return s;
  }

  let stats = $derived(compute(workout));

  function fmtTime(sec: number): string {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    if (h > 0) return `${h}h ${m}min`;
    return `${m} min`;
  }

  function fmtDist(km: number): string {
    if (km === 0) return '';
    if (km >= 10) return `${km.toFixed(1)} km`;
    if (km >= 1) return `${km.toFixed(2)} km`;
    return `${(km * 1000).toFixed(0)} m`;
  }

  const typeOrder = ['warmup', 'interval', 'recovery', 'cooldown', 'rest', 'other'];
  const typeLabel: Record<string, string> = {
    warmup: 'Warm-up', interval: 'Intervals', recovery: 'Recovery',
    cooldown: 'Cool-down', rest: 'Rest', other: 'Other',
  };
</script>

{#if stats}
  <div class="ws">
    <div class="ws-h">Summary</div>
    <div class="ws-grid">
      <div class="ws-stat">
        <span class="ws-v">{fmtTime(stats.totalSec)}</span>
        <span class="ws-l">Total time</span>
      </div>
      <div class="ws-stat">
        <span class="ws-v">{stats.stepCount}</span>
        <span class="ws-l">Steps</span>
      </div>
      {#if stats.totalKm > 0}
        <div class="ws-stat">
          <span class="ws-v">{fmtDist(stats.totalKm)}</span>
          <span class="ws-l">Distance</span>
        </div>
      {/if}
      {#if stats.intervals > 0}
        <div class="ws-stat">
          <span class="ws-v">{stats.intervals}</span>
          <span class="ws-l">Intervals</span>
        </div>
      {/if}
    </div>
    <div class="ws-bar-wrap">
      <div class="ws-bar">
        {#each typeOrder as t}
          {@const pct = stats.totalSec > 0 ? (stats.timeByType[t] ?? 0) / stats.totalSec * 100 : 0}
          {#if pct > 0}
            <div class="ws-bar-seg" style="width: {pct}%; background: {stepColors[t] ?? '#8b5cf6'}" title="{typeLabel[t]}: {fmtTime(stats.timeByType[t] ?? 0)}"></div>
          {/if}
        {/each}
      </div>
      <div class="ws-legend">
        {#each typeOrder as t}
          {@const tSec = stats.timeByType[t]}
          {#if tSec}
            <span class="ws-leg-item">
              <span class="ws-leg-dot" style="background: {stepColors[t] ?? '#8b5cf6'}"></span>
              {typeLabel[t]} {fmtTime(tSec)}
            </span>
          {/if}
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .ws { margin-top: 12px; padding: 12px 14px; background: var(--bg); border: 0.5px solid var(--border); border-radius: 8px; }
  .ws-h { font-size: var(--font-size-xs, 11px); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 8px; }
  .ws-grid { display: flex; flex-wrap: wrap; gap: 16px; }
  .ws-stat { display: flex; flex-direction: column; gap: 1px; }
  .ws-v { font-size: var(--font-size-lg, 16px); font-weight: 600; color: var(--text); line-height: 1.2; }
  .ws-l { font-size: var(--font-size-xs, 11px); color: var(--text-secondary); white-space: nowrap; }
  .ws-bar-wrap { margin-top: 10px; }
  .ws-bar { display: flex; height: 6px; border-radius: 3px; overflow: hidden; background: var(--border); }
  .ws-bar-seg { height: 100%; transition: width 0.2s; min-width: 2px; }
  .ws-legend { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 6px; }
  .ws-leg-item { font-size: var(--font-size-xs, 11px); color: var(--text-secondary); display: flex; align-items: center; gap: 4px; }
  .ws-leg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
