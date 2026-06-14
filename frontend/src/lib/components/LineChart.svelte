<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';

  interface Props {
    data: uPlot.AlignedData;
    options?: Partial<uPlot.Options>;
    class?: string;
  }

  let { data, options = {}, class: className = '' }: Props = $props();

  let container: HTMLDivElement;
  let chart: uPlot | null = null;

  function createChart() {
    if (!container || !data || data.length < 2) return;

    if (chart) chart.destroy();

    const defaultOpts: uPlot.Options = {
      width: container.clientWidth,
      height: 200,
      axes: [
        { stroke: '#888', grid: { stroke: '#eee' } },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series: [
        {},
        { stroke: '#3b82f6', width: 2 },
      ],
      cursor: {
        drag: { x: false, y: false },
      },
      ...options,
    };

    chart = new uPlot(defaultOpts, data, container);
  }

  onMount(() => {
    createChart();
    const observer = new ResizeObserver(() => {
      if (chart && container) {
        chart.setSize({ width: container.clientWidth, height: chart.height });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  });

  onDestroy(() => {
    chart?.destroy();
  });

  $effect(() => {
    if (chart && data && data.length >= 2) {
      chart.setData(data);
    }
  });
</script>

<div bind:this={container} class={className}></div>
