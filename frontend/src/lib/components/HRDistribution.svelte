<script lang="ts">
  import { statsApi, type HRDistributionItem } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';

  let { zones = '0-115,115-130,130-150,150-165,165-300' }: { zones?: string } = $props();

  let data = $state<HRDistributionItem[]>([]);
  let loading = $state(true);

  const zoneColors = $derived(
    data.length === 7
      ? ['var(--zone-hr-1)', 'var(--zone-hr-2)', 'var(--zone-hr-3)', 'var(--zone-hr-4)', 'var(--zone-hr-5)', 'var(--zone-hr-6)', 'var(--zone-hr-7)']
      : ['var(--zone-hr-1)', 'var(--zone-hr-2)', 'var(--zone-hr-3)', 'var(--zone-hr-4)', 'var(--zone-hr-5)']
  );

  async function loadData() {
    loading = true;
    try {
      data = await statsApi.hrDistribution(zones);
    } catch (e) {
      console.error('Failed to load HR distribution', e);
      data = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void zones;
    loadData();
  });

  const total = $derived(data.reduce((s, d) => s + d.count, 0));

  const slices = $derived.by(() => {
    if (data.length === 0 || total === 0) return [];
    const cx = 110, cy = 110, r = 100;
    let acc = 0;
    return data.map((item, i) => {
      const pct = item.percent;
      const startAngle = (acc / 100) * 2 * Math.PI - Math.PI / 2;
      acc += pct;
      const endAngle = (acc / 100) * 2 * Math.PI - Math.PI / 2;
      const largeArc = pct > 50 ? 1 : 0;
      const x1 = cx + r * Math.cos(startAngle);
      const y1 = cy + r * Math.sin(startAngle);
      const x2 = cx + r * Math.cos(endAngle);
      const y2 = cy + r * Math.sin(endAngle);
      const d = `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${largeArc},1 ${x2},${y2} Z`;
      const rangeLabel = i === 0 ? `< ${item.max}` : i === data.length - 1 ? `> ${item.min}` : `${item.min}–${item.max}`;
      return { ...item, d, color: zoneColors[i % zoneColors.length], rangeLabel };
    });
  });

  let hoveredIdx = $state<number | null>(null);
  let tooltipX = $state(0);
  let tooltipY = $state(0);

  function handleMouseMove(e: MouseEvent) {
    tooltipX = e.clientX;
    tooltipY = e.clientY;
  }
</script>

{#if !loading && data.length > 0 && total > 0}
  <div class="hrd-card">
    <div class="hrd-header">
      <div class="hrd-title-row">
        <div class="hrd-icon">
          <Icon name="heart" size={15} />
        </div>
        <span class="hrd-title">Heart rate zones</span>
      </div>
      <span class="hrd-total">{total.toLocaleString()} points</span>
    </div>

    <div class="hrd-pie-section">
      <svg viewBox="0 0 220 220" class="hrd-pie-svg" onmousemove={handleMouseMove}>
        {#each slices as slice, i}
          <path
            d={slice.d}
            fill={slice.color}
            stroke="var(--card-bg, white)"
            stroke-width="2"
            class="hrd-pie-slice"
            class:hovered={hoveredIdx === i}
            onmouseenter={() => hoveredIdx = i}
            onmouseleave={() => hoveredIdx = null}
            onmousemove={handleMouseMove}
          />
        {/each}
      </svg>
    </div>

    {#if hoveredIdx !== null && slices[hoveredIdx]}
      <div class="hrd-tooltip" style="left: {tooltipX}px; top: {tooltipY}px">
        <span class="hrd-tooltip-name">{slices[hoveredIdx].zone}</span>
        <span class="hrd-tooltip-range">{slices[hoveredIdx].rangeLabel} bpm</span>
        <span class="hrd-tooltip-pct">{slices[hoveredIdx].percent.toFixed(1)}%</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .hrd-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 380px;
  }

  .hrd-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .hrd-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .hrd-icon {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: var(--danger-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--danger);
  }
  .hrd-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
  }
  .hrd-total {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-semibold, 600);
    color: var(--text-tertiary, #999);
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 6px;
    background: var(--bg, #f5f5f5);
  }

  .hrd-pie-section {
    display: flex;
    justify-content: center;
    align-items: center;
    flex: 1;
    padding: 4px 0;
  }
  .hrd-pie-svg {
    width: 220px;
    height: 220px;
    cursor: pointer;
  }
  .hrd-pie-slice {
    transition: opacity 0.15s ease, transform 0.15s ease;
    transform-origin: 110px 110px;
  }
  .hrd-pie-slice:hover,
  .hrd-pie-slice.hovered {
    opacity: 0.85;
    transform: scale(1.03);
  }

  .hrd-tooltip {
    position: fixed;
    pointer-events: none;
    z-index: 1000;
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    display: flex;
    gap: 8px;
    align-items: center;
    transform: translate(12px, -50%);
    white-space: nowrap;
  }
  .hrd-tooltip-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }
  .hrd-tooltip-range {
    font-size: 12px;
    color: var(--text-secondary, #666);
  }
  .hrd-tooltip-pct {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary, var(--text));
  }
</style>
