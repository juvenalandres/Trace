<script lang="ts">
  import type { Workout, WorkoutStep, IntensityTarget } from '$lib/api/types';

  interface Props {
    parsed: Workout | null;
    legacy: string | null;
  }

  let { parsed, legacy }: Props = $props();

  function fmtDuration(d: { value: number; unit: string } | null): string {
    if (!d) return '';
    const v = Number.isInteger(d.value) ? d.value.toString() : d.value.toFixed(1);
    return `${v}${d.unit}`;
  }

  function fmtTarget(t: IntensityTarget | null): string {
    if (!t) return '';
    if (t.zone) return `Z${t.zone}`;
    if (t.value && t.of) return `${t.value}% ${t.of.toUpperCase()}`;
    if (t.value && t.unit) return `${t.value}${t.unit}`;
    if (t.value) return `${t.value}`;
    return t.type;
  }

  function stepLabel(s: WorkoutStep): string {
    const labels: Record<string, string> = {
      warmup: 'Warm-up',
      interval: 'Interval',
      recovery: 'Recovery',
      cooldown: 'Cool-down',
      rest: 'Rest',
      repeat: 'Repeat',
    };
    return labels[s.type] || s.name || s.type;
  }

  function stepSummary(s: WorkoutStep): string {
    const parts: string[] = [stepLabel(s)];
    if (s.duration) parts.push(fmtDuration(s.duration));
    if (s.distance) parts.push(`${s.distance.value}${s.distance.unit}`);
    if (s.target) parts.push(`@ ${fmtTarget(s.target)}`);
    if (s.notes) parts.push(`(${s.notes})`);
    return parts.join(' ');
  }
</script>

{#if parsed}
  {#each parsed.blocks as block}
    <div class="wb-block">
      {#if block.name}
        <div class="wb-block-name">{block.name}</div>
      {/if}
      {#each block.steps as step}
        {#if step.type === 'repeat' && step.steps}
          <div class="wb-step wb-repeat">
            <span class="wb-step-text">{stepLabel(step)} ×{step.repetitions ?? 1}{step.name ? ` – ${step.name}` : ''}</span>
            <div class="wb-nested">
              {#each step.steps as nested}
                <div class="wb-step wb-nested-step">
                  <span class="wb-step-text">{stepSummary(nested)}</span>
                </div>
              {/each}
            </div>
          </div>
        {:else}
          <div class="wb-step">
            <span class="wb-step-text">{stepSummary(step)}</span>
          </div>
        {/if}
      {/each}
    </div>
  {/each}
{:else if legacy}
  {@const items = legacy.split(',').map(i => i.trim()).filter(Boolean)}
  <div class="wb-legacy">
    {#each items as item}
      <span class="wb-legacy-item">{item}</span>
    {/each}
  </div>
{/if}

<style>
  .wb-block {
    margin-bottom: 8px;
  }
  .wb-block-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 4px;
  }
  .wb-step {
    padding: 3px 0;
  }
  .wb-step-text {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .wb-repeat {
    margin-top: 4px;
  }
  .wb-nested {
    padding-left: 14px;
    border-left: 2px solid var(--border);
    margin: 2px 0 2px 6px;
  }
  .wb-nested-step .wb-step-text {
    font-size: 11px;
  }
  .wb-legacy {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .wb-legacy-item {
    font-size: 11px;
    padding: 2px 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-secondary);
  }
</style>
