<script lang="ts">
  import type { Workout, WorkoutStep, IntensityTarget, Duration, Distance } from '$lib/api/types';
  import WorkoutPreviewChart from './WorkoutPreviewChart.svelte';
  import WorkoutSummary from './WorkoutSummary.svelte';

  let { json = $bindable('') }: { json?: string } = $props();
  let showPreview = $state(false);

  let workout = $state<Workout>({ blocks: [] });

  $effect(() => {
    if (!json) { workout = { blocks: [] }; return; }
    try {
      const p = JSON.parse(json);
      if (p?.blocks) { workout = p; return; }
    } catch { /* */ }
    workout = { blocks: [] };
  });

  function emit() {
    json = JSON.stringify(workout);
  }

  function addBlock(name?: string) {
    workout = { ...workout, blocks: [...workout.blocks, { name: name ?? null, steps: [] }] };
    emit();
  }

  function remBlock(i: number) {
    workout = { ...workout, blocks: workout.blocks.filter((_, j) => j !== i) };
    emit();
  }

  function setName(i: number, name: string) {
    const b = [...workout.blocks]; b[i] = { ...b[i], name: name || null };
    workout = { ...workout, blocks: b }; emit();
  }

  function addStep(bi: number, type = 'interval') {
    const b = [...workout.blocks]; const bl = { ...b[bi] };
    bl.steps = [...bl.steps, { type, name: null, duration: null, distance: null, target: null, repetitions: null, steps: null, notes: null }];
    b[bi] = bl; workout = { ...workout, blocks: b }; emit();
  }

  function remStep(bi: number, si: number) {
    const b = [...workout.blocks]; const bl = { ...b[bi] };
    bl.steps = bl.steps.filter((_, j) => j !== si);
    b[bi] = bl; workout = { ...workout, blocks: b }; emit();
  }

  function patchStep(bi: number, si: number, p: Partial<WorkoutStep>) {
    const b = [...workout.blocks]; const bl = { ...b[bi] };
    bl.steps = bl.steps.map((s, j) => j === si ? { ...s, ...p } as WorkoutStep : s);
    b[bi] = bl; workout = { ...workout, blocks: b }; emit();
  }

  function patchSteps(bi: number, si: number, ss: WorkoutStep[]) {
    patchStep(bi, si, { steps: ss.length ? ss : null });
  }

  function wrapRepeat(bi: number, si: number) {
    const s = workout.blocks[bi]?.steps[si]; if (!s) return;
    patchStep(bi, si, { type: 'repeat', repetitions: 1, steps: [{ ...s, repetitions: null, steps: null }], duration: null, distance: null, target: null });
  }

  function unwrapRepeat(bi: number, si: number) {
    const s = workout.blocks[bi]?.steps[si];
    if (s?.type !== 'repeat' || !s?.steps?.[0]) return;
    patchStep(bi, si, { ...s.steps[0] });
  }

  function moveStep(bi: number, fi: number, ti: number) {
    if (fi === ti) return;
    const bl = { ...workout.blocks[bi] }; const st = [...bl.steps];
    const [m] = st.splice(fi, 1); st.splice(ti, 0, m); bl.steps = st;
    const b = [...workout.blocks]; b[bi] = bl; workout = { ...workout, blocks: b }; emit();
  }

  function targetInit(type: string): IntensityTarget {
    switch (type) {
      case 'power_percent': return { type, value: null, unit: '%', of: 'ftp', zone: null };
      case 'hr_percent': return { type, value: null, unit: '%', of: 'max_hr', zone: null };
      case 'power_zone': return { type, value: null, unit: 'zone', of: null, zone: 2 };
      case 'hr_zone': return { type, value: null, unit: 'zone', of: null, zone: 2 };
      case 'pace': return { type, value: null, unit: 'min/km', of: null, zone: null };
      case 'power': return { type, value: null, unit: 'watts', of: null, zone: null };
      case 'hr': return { type, value: null, unit: 'bpm', of: null, zone: null };
      case 'rpe': return { type, value: 7, unit: null, of: null, zone: null };
      default: return { type: 'free', value: null, unit: null, of: null, zone: null };
    }
  }

  const stepTypes = [
    { v: 'warmup', l: 'Warm-up' },
    { v: 'interval', l: 'Interval' },
    { v: 'recovery', l: 'Recovery' },
    { v: 'cooldown', l: 'Cool-down' },
    { v: 'rest', l: 'Rest' },
    { v: 'other', l: 'Other' },
  ];

  function si(t: string) { return stepTypes.find(s => s.v === t) ?? { l: t }; }

  function targetLabel(t: IntensityTarget): string {
    if (t.zone != null) return `Z${t.zone}`;
    if (t.value != null && t.of) return `${t.value}% ${t.of.toUpperCase()}`;
    if (t.value != null && t.unit) return `${t.value} ${t.unit}`;
    if (t.value != null) return `${t.value}`;
    return t.type;
  }

  function durVal(d: Duration | null): string { return d?.value?.toString() ?? ''; }
  function durUnit(d: Duration | null): string { return d?.unit ?? 'min'; }
  function distVal(d: Distance | null): string { return d?.value?.toString() ?? ''; }
  function distUnit(d: Distance | null): string { return d?.unit ?? 'km'; }

  function onDuration(value: string, prev: Duration | null, onSet: (d: Duration | null) => void) {
    const v = parseFloat(value);
    onSet(v && v > 0 ? { value: v, unit: prev?.unit ?? 'min' } : null);
  }

  function onDurationUnit(unit: string, prev: Duration | null, onSet: (d: Duration | null) => void) {
    const v = prev?.value;
    onSet(v && v > 0 ? { value: v, unit } : null);
  }

  function onDistance(value: string, prev: Distance | null, onSet: (d: Distance | null) => void) {
    const v = parseFloat(value);
    onSet(v && v > 0 ? { value: v, unit: prev?.unit ?? 'km' } : null);
  }

  function onDistanceUnit(unit: string, prev: Distance | null, onSet: (d: Distance | null) => void) {
    const v = prev?.value;
    onSet(v && v > 0 ? { value: v, unit } : null);
  }

  function patchNested(bi: number, si: number, ni: number, p: Partial<WorkoutStep>) {
    const bl = { ...workout.blocks[bi] };
    const s = { ...bl.steps[si] } as WorkoutStep;
    const ss = [...(s.steps ?? [])];
    ss[ni] = { ...ss[ni], ...p } as WorkoutStep;
    s.steps = ss;
    bl.steps = bl.steps.map((it, j) => j === si ? s : it);
    const b = [...workout.blocks]; b[bi] = bl;
    workout = { ...workout, blocks: b }; emit();
  }

  let dragItem = $state<{ bi: number; si: number } | null>(null);
  let clipboard = $state<{ type: 'step'; data: WorkoutStep } | { type: 'block'; data: string } | null>(null);

  function copyStep(bi: number, si: number) {
    clipboard = { type: 'step', data: JSON.parse(JSON.stringify(workout.blocks[bi].steps[si])) };
  }

  function pasteStep(bi: number, si: number) {
    if (clipboard?.type !== 'step') return;
    const n = JSON.parse(JSON.stringify(clipboard.data)) as WorkoutStep;
    const b = [...workout.blocks]; const bl = { ...b[bi] };
    bl.steps = [...bl.steps.slice(0, si + 1), n, ...bl.steps.slice(si + 1)];
    b[bi] = bl; workout = { ...workout, blocks: b }; emit();
  }

  function pasteStepEnd(bi: number) {
    if (clipboard?.type !== 'step') return;
    pasteStep(bi, workout.blocks[bi].steps.length - 1);
  }

  function copyBlock(bi: number) {
    clipboard = { type: 'block', data: JSON.parse(JSON.stringify(workout.blocks[bi].name)) };
  }

  function pasteBlock(bi: number) {
    if (clipboard?.type !== 'block') return;
    const n = JSON.parse(JSON.stringify(clipboard.data)) as string | null;
    const b = [...workout.blocks];
    b.splice(bi + 1, 0, { name: n, steps: [] });
    workout = { ...workout, blocks: b }; emit();
  }
</script>

<div class="we">
  {#if workout.blocks.length === 0}
    <div class="we-empty">
      <button class="btn btn-primary btn-sm" onclick={() => addBlock('Warm-up')}>+ Warm-up</button>
      <button class="btn btn-primary btn-sm" onclick={() => addBlock('Main Set')}>+ Main Set</button>
      <button class="btn btn-primary btn-sm" onclick={() => addBlock('Cool-down')}>+ Cool-down</button>
      <button class="btn btn-outline btn-sm" onclick={() => addBlock('')}>+ Custom Block</button>
    </div>
  {:else}
    <div class="we-blocks">
      {#each workout.blocks as block, bi}
        <div class="we-block">
          <div class="we-bh">
            <input class="we-bn" value={block.name ?? ''} oninput={(e) => setName(bi, (e.target as HTMLInputElement).value)} placeholder="Block name" />
            <div class="we-ba-acts">
              <button class="icn" onclick={() => copyBlock(bi)} title="Copy block">⧉</button>
              <button class="icn dn" onclick={() => remBlock(bi)}>✕</button>
            </div>
          </div>
          <div class="we-steps">
            {#each block.steps as step, si}
              {@const colors = { warmup: '#3b82f6', interval: '#ef4444', recovery: '#22c55e', cooldown: '#3b82f6', rest: '#6b7280', other: '#8b5cf6', repeat: '#f59e0b' } as Record<string,string>}
              {@const sc = colors[step.type] ?? '#8b5cf6'}
              <div class="we-step" draggable="true" style="--sc: {sc}"
                ondragstart={() => dragItem = { bi, si }}
                ondragover={(e) => e.preventDefault()}
                ondrop={() => { if (dragItem?.bi === bi) moveStep(bi, dragItem.si, si); dragItem = null; }}>
                <div class="we-sh">
                  <span class="we-drag">⠿</span>
                  <select class="we-sel" value={step.type} onchange={(e) => patchStep(bi, si, { type: (e.target as HTMLSelectElement).value })}>
                    {#each stepTypes as st}<option value={st.v}>{st.l}</option>{/each}
                    <option value="repeat">Repeat</option>
                  </select>
                  {#if step.type !== 'repeat'}
                    <button class="we-sbtn" onclick={() => wrapRepeat(bi, si)}>↻ Repeat</button>
                  {:else}
                    <span class="we-rep">×<input class="we-num" type="number" min="1" value={step.repetitions ?? 1} oninput={(e) => patchStep(bi, si, { repetitions: parseInt((e.target as HTMLInputElement).value) || 1 })} /></span>
                    <button class="we-sbtn" onclick={() => unwrapRepeat(bi, si)}>↺ Unwrap</button>
                  {/if}
                  <button class="icn" onclick={() => copyStep(bi, si)} title="Copy step">⧉</button>
                  {#if clipboard?.type === 'step'}
                    <button class="icn" onclick={() => pasteStep(bi, si)} title="Paste after">📋</button>
                  {/if}
                  <button class="icn dn" onclick={() => remStep(bi, si)}>✕</button>
                </div>

                {#if step.type === 'repeat' && step.steps}
                  <div class="we-nested">
                    {#each step.steps as ns, ni}
                      {@const nsc = colors[ns.type] ?? '#8b5cf6'}
                      <div class="we-step" style="--sc: {nsc}">
                        <div class="we-sh">
                          <select class="we-sel" value={ns.type} onchange={(e) => {
                            const ss = [...(step.steps ?? [])];
                            ss[ni] = { ...ss[ni], type: (e.target as HTMLSelectElement).value };
                            patchSteps(bi, si, ss);
                          }}>
                            {#each stepTypes as st}<option value={st.v}>{st.l}</option>{/each}
                          </select>
                          <button class="we-sbtn" onclick={() => copyStep(bi, si)} title="Copy step">⧉</button>
                          <button class="we-sbtn" onclick={() => { const ss = (step.steps ?? []).filter((_, j) => j !== ni); patchSteps(bi, si, ss); }}>✕</button>
                        </div>
                        <div class="we-ctrl">
                          <span class="we-cl">Time</span>
                          <input class="we-inp" type="number" min="0" step="any" placeholder="—" value={durVal(ns.duration)} oninput={(e) => onDuration((e.target as HTMLInputElement).value, ns.duration, (d) => patchNested(bi, si, ni, d ? { duration: d, distance: null } : { duration: null }))} />
                          <select class="we-un" value={durUnit(ns.duration)} onchange={(e) => onDurationUnit((e.target as HTMLSelectElement).value, ns.duration, (d) => patchNested(bi, si, ni, d ? { duration: d, distance: null } : { duration: null }))}>
                            <option value="s">s</option><option value="min">min</option><option value="h">h</option>
                          </select>
                          <span class="we-or">or</span>
                          <span class="we-cl">Dist</span>
                          <input class="we-inp" type="number" min="0" step="any" placeholder="—" value={distVal(ns.distance)} oninput={(e) => onDistance((e.target as HTMLInputElement).value, ns.distance, (d) => patchNested(bi, si, ni, d ? { distance: d, duration: null } : { distance: null }))} />
                          <select class="we-un" value={distUnit(ns.distance)} onchange={(e) => onDistanceUnit((e.target as HTMLSelectElement).value, ns.distance, (d) => patchNested(bi, si, ni, d ? { distance: d, duration: null } : { distance: null }))}>
                            <option value="m">m</option><option value="km">km</option><option value="mi">mi</option>
                          </select>
                        </div>
                        <div class="we-ctrl">
                          <button class="we-tb {ns.target ? 'a' : ''}" onclick={() => { if (ns.target) { patchNested(bi, si, ni, { target: null }); } else { patchNested(bi, si, ni, { target: targetInit('power_percent') }); } }}>
                            {ns.target ? targetLabel(ns.target) : '+ Target'}
                          </button>
                          {#if ns.target}
                            {@const tar = ns.target}
                            <button class="we-cy" onclick={() => { const opts = ['power_percent','hr_percent','power_zone','hr_zone','pace','power','hr','rpe','free']; const ci = opts.indexOf(tar.type); const nextType = opts[(ci + 1) % opts.length]; patchNested(bi, si, ni, { target: targetInit(nextType) }); }}>↺</button>
                            {#if tar.type === 'power_percent' || tar.type === 'hr_percent'}
                              <input class="we-inp" type="number" min="0" max="200" step="1" placeholder="%" value={tar.value ?? ''} oninput={(e) => patchNested(bi, si, ni, { target: { ...tar, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                              <span class="we-cl">% of</span>
                              <select class="we-un" value={tar.of ?? 'ftp'} onchange={(e) => patchNested(bi, si, ni, { target: { ...tar, of: (e.target as HTMLSelectElement).value } })}>
                                <option value="ftp">FTP</option><option value="max_hr">MaxHR</option><option value="lthr">LTHR</option>
                              </select>
                            {:else if tar.type === 'power_zone' || tar.type === 'hr_zone'}
                              <select class="we-un" value={tar.zone ?? 2} onchange={(e) => patchNested(bi, si, ni, { target: { ...tar, zone: parseInt((e.target as HTMLSelectElement).value) } })}>
                                {#each [1,2,3,4,5] as z}<option value={z}>Z{z}</option>{/each}
                              </select>
                            {:else if tar.type === 'pace'}
                              <input class="we-inp" type="number" min="0" step="0.1" placeholder="min/km" value={tar.value ?? ''} oninput={(e) => patchNested(bi, si, ni, { target: { ...tar, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                              <select class="we-un" value={tar.unit ?? 'min/km'} onchange={(e) => patchNested(bi, si, ni, { target: { ...tar, unit: (e.target as HTMLSelectElement).value } })}>
                                <option value="min/km">min/km</option><option value="min/mi">min/mi</option>
                              </select>
                            {:else if tar.type === 'power'}
                              <input class="we-inp" type="number" min="0" step="1" placeholder="watts" value={tar.value ?? ''} oninput={(e) => patchNested(bi, si, ni, { target: { ...tar, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                              <span class="we-cl">W</span>
                            {:else if tar.type === 'hr'}
                              <input class="we-inp" type="number" min="0" step="1" placeholder="bpm" value={tar.value ?? ''} oninput={(e) => patchNested(bi, si, ni, { target: { ...tar, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                              <span class="we-cl">bpm</span>
                            {:else if tar.type === 'rpe'}
                              <input class="we-inp" type="number" min="1" max="10" step="1" placeholder="1-10" value={tar.value ?? 7} oninput={(e) => patchNested(bi, si, ni, { target: { ...tar, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                            {:else}
                              <input class="we-inp" type="text" placeholder="e.g. easy" value={tar.value ?? ''} oninput={(e) => patchNested(bi, si, ni, { target: { ...tar, value: (e.target as HTMLInputElement).value || null } })} />
                            {/if}
                            <button class="we-clr" onclick={() => patchNested(bi, si, ni, { target: null })}>✕</button>
                          {/if}
                        </div>
                      </div>
                    {/each}
                    <button class="btn btn-outline btn-xs" onclick={() => {
                      const ss = [...(step.steps ?? [])];
                      ss.push({ type: 'interval', name: null, duration: null, distance: null, target: null, repetitions: null, steps: null, notes: null });
                      patchSteps(bi, si, ss);
                    }}>+ Add step</button>
                    {#if clipboard?.type === 'step'}
                      {@const cb = clipboard}
                      <button class="btn btn-outline btn-xs" onclick={() => {
                        const n = JSON.parse(JSON.stringify(cb.data)) as WorkoutStep;
                        const ss = [...(step.steps ?? []), n];
                        patchSteps(bi, si, ss);
                      }}>📋 Paste</button>
                    {/if}
                  </div>
                {:else}
                  <div class="we-ctrl">
                    <span class="we-cl">Time</span>
                    <input class="we-inp" type="number" min="0" step="any" placeholder="—" value={durVal(step.duration)} oninput={(e) => onDuration((e.target as HTMLInputElement).value, step.duration, (d) => patchStep(bi, si, d ? { duration: d, distance: null } : { duration: null }))} />
                    <select class="we-un" value={durUnit(step.duration)} onchange={(e) => onDurationUnit((e.target as HTMLSelectElement).value, step.duration, (d) => patchStep(bi, si, d ? { duration: d, distance: null } : { duration: null }))}>
                      <option value="s">s</option><option value="min">min</option><option value="h">h</option>
                    </select>
                    <span class="we-or">or</span>
                    <span class="we-cl">Dist</span>
                    <input class="we-inp" type="number" min="0" step="any" placeholder="—" value={distVal(step.distance)} oninput={(e) => onDistance((e.target as HTMLInputElement).value, step.distance, (d) => patchStep(bi, si, d ? { distance: d, duration: null } : { distance: null }))} />
                    <select class="we-un" value={distUnit(step.distance)} onchange={(e) => onDistanceUnit((e.target as HTMLSelectElement).value, step.distance, (d) => patchStep(bi, si, d ? { distance: d, duration: null } : { distance: null }))}>
                      <option value="m">m</option><option value="km">km</option><option value="mi">mi</option>
                    </select>
                  </div>
                  <div class="we-ctrl">
                    <button class="we-tb {step.target ? 'a' : ''}" onclick={() => { if (step.target) patchStep(bi, si, { target: null }); else patchStep(bi, si, { target: targetInit('power_percent') }); }}>
                      {step.target ? targetLabel(step.target) : '+ Target'}
                    </button>
                    {#if step.target}
                      {@const st = step.target}
                      <button class="we-cy" onclick={() => { const opts = ['power_percent','hr_percent','power_zone','hr_zone','pace','power','hr','rpe','free']; const ci = opts.indexOf(st.type); const ni = (ci + 1) % opts.length; patchStep(bi, si, { target: targetInit(opts[ni]) }); }}>↺</button>
                      {#if st.type === 'power_percent' || st.type === 'hr_percent'}
                        <input class="we-inp" type="number" min="0" max="200" step="1" placeholder="%" value={st.value ?? ''} oninput={(e) => patchStep(bi, si, { target: { ...st, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                        <span class="we-cl">% of</span>
                        <select class="we-un" value={st.of ?? 'ftp'} onchange={(e) => patchStep(bi, si, { target: { ...st, of: (e.target as HTMLSelectElement).value } })}>
                          <option value="ftp">FTP</option><option value="max_hr">MaxHR</option><option value="lthr">LTHR</option>
                        </select>
                      {:else if st.type === 'power_zone' || st.type === 'hr_zone'}
                        <select class="we-un" value={st.zone ?? 2} onchange={(e) => patchStep(bi, si, { target: { ...st, zone: parseInt((e.target as HTMLSelectElement).value) } })}>
                          {#each [1,2,3,4,5] as z}<option value={z}>Z{z}</option>{/each}
                        </select>
                      {:else if st.type === 'pace'}
                        <input class="we-inp" type="number" min="0" step="0.1" placeholder="min/km" value={st.value ?? ''} oninput={(e) => patchStep(bi, si, { target: { ...st, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                        <select class="we-un" value={st.unit ?? 'min/km'} onchange={(e) => patchStep(bi, si, { target: { ...st, unit: (e.target as HTMLSelectElement).value } })}>
                          <option value="min/km">min/km</option><option value="min/mi">min/mi</option>
                        </select>
                      {:else if st.type === 'power'}
                        <input class="we-inp" type="number" min="0" step="1" placeholder="watts" value={st.value ?? ''} oninput={(e) => patchStep(bi, si, { target: { ...st, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                        <span class="we-cl">W</span>
                      {:else if st.type === 'hr'}
                        <input class="we-inp" type="number" min="0" step="1" placeholder="bpm" value={st.value ?? ''} oninput={(e) => patchStep(bi, si, { target: { ...st, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                        <span class="we-cl">bpm</span>
                      {:else if st.type === 'rpe'}
                        <input class="we-inp" type="number" min="1" max="10" step="1" placeholder="1-10" value={st.value ?? 7} oninput={(e) => patchStep(bi, si, { target: { ...st, value: parseFloat((e.target as HTMLInputElement).value) || null } })} />
                      {:else}
                        <input class="we-inp" type="text" placeholder="e.g. easy" value={st.value ?? ''} oninput={(e) => patchStep(bi, si, { target: { ...st, value: (e.target as HTMLInputElement).value || null } })} />
                      {/if}
                      <button class="we-clr" onclick={() => patchStep(bi, si, { target: null })}>✕</button>
                    {/if}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
          <div class="we-add">
            {#each [['interval','Interval'],['recovery','Recovery'],['warmup','Warm-up'],['cooldown','Cool-down'],['rest','Rest'],['other','Other']] as [v, l]}
              <button class="btn btn-outline btn-xs" onclick={() => addStep(bi, v)}>+ {l}</button>
            {/each}
            {#if clipboard?.type === 'step'}
              <button class="btn btn-outline btn-xs" onclick={() => pasteStepEnd(bi)}>📋 Paste</button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
    <div class="we-ba">
      {#each [['Warm-up','Warm-up'],['Main Set','Main Set'],['Cool-down','Cool-down'],['','Custom']] as [v, l]}
        <button class="btn btn-outline btn-sm" onclick={() => addBlock(v)}>+ {l} Block</button>
      {/each}
      {#if clipboard?.type === 'block'}
        <button class="btn btn-outline btn-sm" onclick={() => pasteBlock(workout.blocks.length - 1)}>📋 Paste Block</button>
      {/if}
      <button class="btn btn-outline btn-sm we-pv" onclick={() => showPreview = !showPreview}>{showPreview ? 'Hide' : 'Show'} Preview</button>
    </div>
    <WorkoutSummary {workout} />
    {#if showPreview}
      <div class="we-chart">
        <WorkoutPreviewChart {workout} />
      </div>
    {/if}
  {/if}
</div>

<style>
  .we { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--card-radius, 10px); padding: var(--card-padding, 16px); }
  .we-empty { display: flex; flex-wrap: wrap; gap: 8px; }

  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; border-radius: 8px; font-family: var(--font-sans); font-size: var(--font-size-base, 13px); font-weight: var(--font-weight-medium, 500); cursor: pointer; }
  .btn-primary { background: var(--primary); color: #fff; }
  .btn-primary:hover { opacity: 0.9; }
  .btn-outline { background: var(--surface); color: var(--text); border: 0.5px solid var(--border); }
  .btn-outline:hover { background: var(--hover); }
  .btn-sm { padding: 6px 10px; font-size: var(--font-size-sm, 12px); }
  .btn-xs { padding: 4px 10px; font-size: var(--font-size-xs, 11px); border-radius: 6px; }

  .we-blocks { display: flex; flex-direction: column; gap: 14px; }
  .we-block { border: 0.5px solid var(--border); border-radius: var(--card-radius, 10px); padding: 14px; border-left: 3px solid var(--primary); background: var(--surface); }
  .we-bh { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
  .we-ba-acts { display: flex; align-items: center; gap: 4px; margin-left: auto; }
  .we-bn { flex: 1; font-size: var(--font-size-md, 14px); font-weight: 600; border: none; background: transparent; color: var(--text); outline: none; padding: 2px 4px; border-bottom: 1px solid transparent; }
  .we-bn:focus { border-bottom-color: var(--primary); }
  .we-steps { display: flex; flex-direction: column; gap: 8px; }
  .we-step { border: 0.5px solid var(--border); border-left: 3px solid var(--sc, var(--primary)); border-radius: 8px; padding: 10px 12px; background: var(--bg); }
  .we-sh { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .we-drag { cursor: grab; color: var(--text-secondary); font-size: 15px; user-select: none; opacity: 0.4; }
  .we-drag:hover { opacity: 0.7; }
  .we-sel { font-size: var(--font-size-sm, 12px); font-weight: 600; padding: 4px 8px; border: 0.5px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); outline: none; cursor: pointer; }
  .we-sel:hover { border-color: var(--primary); }
  .we-sbtn { padding: 4px 10px; font-size: var(--font-size-xs, 11px); font-weight: 500; border: 0.5px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text-secondary); cursor: pointer; }
  .we-sbtn:hover { border-color: var(--primary); color: var(--text); background: var(--hover); }
  .we-rep { font-size: var(--font-size-sm, 12px); display: flex; align-items: center; gap: 4px; color: var(--text-secondary); }
  .we-rep input { width: 36px; padding: 3px 4px; font-size: var(--font-size-sm, 12px); text-align: center; border: 0.5px solid var(--border); border-radius: 4px; background: var(--surface); color: var(--text); }
  .we-nested { padding-left: 16px; border-left: 2px solid var(--border); margin: 8px 0 2px 8px; display: flex; flex-direction: column; gap: 6px; }
  .we-ctrl { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 6px; }
  .we-cl { font-size: var(--font-size-xs, 11px); color: var(--text-secondary); white-space: nowrap; font-weight: 500; text-transform: uppercase; letter-spacing: 0.3px; }
  .we-inp { width: 52px; padding: 4px 6px; font-size: var(--font-size-sm, 12px); border: 0.5px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); }
  .we-inp:focus { outline: none; border-color: var(--primary); }
  .we-inp[type="text"] { width: 80px; }
  .we-un { font-size: var(--font-size-xs, 11px); padding: 4px 4px; border: 0.5px solid transparent; border-radius: 4px; background: transparent; color: var(--text-secondary); cursor: pointer; }
  .we-un:hover { border-color: var(--border); background: var(--surface); }
  .we-or { font-size: var(--font-size-xs, 11px); color: var(--text-secondary); margin: 0 4px; }
  .we-tb { padding: 4px 10px; font-size: var(--font-size-xs, 11px); font-weight: 500; border: 0.5px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text-secondary); cursor: pointer; white-space: nowrap; }
  .we-tb:hover { border-color: var(--primary); }
  .we-tb.a { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }
  .we-cy { font-size: var(--font-size-sm, 12px); border: none; background: transparent; color: var(--text-secondary); cursor: pointer; padding: 2px 4px; border-radius: 4px; }
  .we-cy:hover { background: var(--hover); }
  .we-clr { font-size: var(--font-size-sm, 12px); border: none; background: transparent; color: #dc2626; cursor: pointer; padding: 2px 6px; border-radius: 4px; }
  .we-clr:hover { background: #fee2e2; }
  .icn { border: none; background: transparent; cursor: pointer; padding: 4px 6px; border-radius: 6px; line-height: 1; font-size: 13px; color: var(--text-secondary); }
  .icn:hover { background: var(--hover); }
  .icn.dn { color: #dc2626; }
  .icn.dn:hover { background: #fee2e2; }
  .we-ba { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
  .we-pv { margin-left: auto; }
  .we-chart { margin-top: 14px; border-radius: 8px; overflow: hidden; border: 0.5px solid var(--border); background: var(--bg); }
  .we-add { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
</style>
