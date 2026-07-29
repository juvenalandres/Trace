<script lang="ts">
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import type { Workout, WorkoutStep, IntensityTarget } from '$lib/api/types';

  let { workout, height = 160 }: { workout: Workout | null; height?: number } = $props();

  let container: HTMLDivElement;
  let chart: uPlot | null = null;

  const zoneMid: Record<number, number> = { 1: 55, 2: 70, 3: 82, 4: 94, 5: 106 };

  const typeColor: Record<string, string> = {
    warmup: '#22c55e',
    interval: '#f97316',
    recovery: '#06b6d4',
    cooldown: '#a855f7',
    rest: '#6b7280',
  };

  function durSec(d: { value: number; unit: string } | null): number {
    if (!d) return 0;
    switch (d.unit) {
      case 's': return d.value;
      case 'min': return d.value * 60;
      case 'h': return d.value * 3600;
      default: return d.value * 60;
    }
  }

  function pct(t: IntensityTarget | null, stepType: string): number | null {
    if (!t) return stepType === 'rest' ? 0 : null;
    if (stepType === 'rest') return 0;
    switch (t.type) {
      case 'power_percent':
      case 'hr_percent':
        return typeof t.value === 'number' ? t.value : null;
      case 'power_zone':
      case 'hr_zone':
        return zoneMid[t.zone ?? -1] ?? null;
      default:
        return null;
    }
  }

  function expand(steps: WorkoutStep[]): { sec: number; pct: number | null; type: string }[] {
    const out: { sec: number; pct: number | null; type: string }[] = [];
    for (const s of steps) {
      if (s.type === 'repeat' && s.steps) {
        for (let r = 0; r < (s.repetitions ?? 1); r++) {
          out.push(...expand(s.steps));
        }
      } else {
        const d = s.duration ? durSec(s.duration) : 0;
        if (d > 0) out.push({ sec: d, pct: pct(s.target, s.type), type: s.type });
      }
    }
    return out;
  }

  let ro: ResizeObserver | null = null;

  function rebuild() {
    if (chart) { chart.destroy(); chart = null; }
    if (ro) { ro.disconnect(); ro = null; }
    if (!workout?.blocks.length || !container) return;

    const steps = expand(workout.blocks.flatMap(b => b.steps));
    if (!steps.length) return;

    const x: number[] = [];
    const y: (number | null)[] = [];
    const barTypes: string[] = [];
    let t = 0;
    for (const s of steps) {
      x.push(t);
      y.push(s.pct ?? 0);
      barTypes.push(s.type);
      t += s.sec;
    }
    x.push(t);
    y.push(null);
    barTypes.push('');
    if (t === 0) return;

    const opts = {
      width: container.clientWidth,
      height,
      padding: [4, 6, 16, 48],
      legend: { show: false },
      axes: [
        {
          stroke: '#888',
          grid: { show: false },
          ticks: { show: false },
          values: (_u: unknown, ticks: number[]) => ticks.map(t => {
            const m = Math.floor(t / 60);
            const s = Math.floor(t % 60);
            return `${m}:${s.toString().padStart(2, '0')}`;
          }),
          size: 32,
        },
        {
          stroke: '#888',
          grid: { stroke: 'rgba(128,128,128,0.12)' },
          ticks: { show: false },
          values: (_u: unknown, ticks: number[]) => ticks.map(v => `${v}%`),
          size: 40,
        },
      ],
      series: [
        {},
        {
          label: 'Intensity',
          paths: (u: uPlot, si: number) => {
            const xd = u.data[0] as Float64Array;
            const yd = u.data[si] as Float64Array;
            const len = xd.length;
            const fillMap = new Map<string, Path2D>();
            for (let i = 0; i < len - 1; i++) {
              const yv = yd[i];
              if (yv == null) continue;
              const color = typeColor[barTypes[i]] ?? '#ef4444';
              let p = fillMap.get(color);
              if (!p) { p = new Path2D(); fillMap.set(color, p); }
              const l = u.valToPos(xd[i], 'x');
              const r = u.valToPos(xd[i + 1], 'x');
              const t = u.valToPos(yv, 'y');
              const b = u.valToPos(0, 'y');
              const w = Math.max(r - l, 1);
              const h = Math.max(b - t, 1);
              if (w > 0 && h > 0) p.rect(l, t, w, h);
            }
            return { fill: fillMap, stroke: fillMap };
          },
          points: { show: false },
        },
      ],
      scales: {
        x: { time: false, range: [0, t] },
        y: { range: [0, 120] },
      },
    };

    const data: uPlot.AlignedData = [
      new Float64Array(x),
      new Float64Array(y.map(v => v ?? 0)),
    ];

    chart = new uPlot(opts as any, data, container);

    ro = new ResizeObserver(() => {
      if (chart && container) chart.setSize({ width: container.clientWidth, height });
    });
    ro.observe(container);
  }

  $effect(() => {
    workout;
    if (container) rebuild();
    return () => {
      if (chart) { chart.destroy(); chart = null; }
      if (ro) { ro.disconnect(); ro = null; }
    };
  });
</script>

<div bind:this={container} class="wpc"></div>

<style>
  .wpc { min-height: 160px; }
  .wpc :global(.u-title) { display: none; }
  .wpc :global(.u-cursor-x) { display: none; }
  .wpc :global(.u-cursor-y) { display: none; }
</style>
