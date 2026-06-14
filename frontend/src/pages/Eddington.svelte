<script lang="ts">
  import { onMount } from 'svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { statsApi } from '$lib/api/types';
  import type { EddingtonResponse } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  let data = $state<EddingtonResponse | null>(null);
  let loading = $state(true);
  let error = $state('');
  let chartContainer = $state<HTMLDivElement | null>(null);
  let chart: uPlot | null = null;

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  }

  function buildChart() {
    if (!chartContainer || !data || data.distribution.length === 0) return;

    chart?.destroy();

    const thresholds = data.distribution.map(d => d.threshold);
    const counts = data.distribution.map(d => d.count);

    const plotData: uPlot.AlignedData = [
      new Float64Array(thresholds),
      new Float64Array(counts),
    ];

    chart = new uPlot({
      width: chartContainer.clientWidth,
      height: 220,
      padding: [10, 8, 0, 0],
      cursor: {
        x: {
          formatter: (_u, val) => `${val} ${data?.unit_label ?? 'km'}`,
        },
      },
      axes: [
        {
          stroke: '#888',
          grid: { stroke: '#eee' },
          label: `Distance (${data.unit_label})`,
          labelSize: 12,
        },
        {
          stroke: '#888',
          grid: { stroke: '#eee' },
          label: 'Activities',
          labelSize: 12,
        },
      ],
      series: [
        {},
        {
          stroke: '#3b82f6',
          fill: '#3b82f620',
          width: 1.5,
          paths: uPlot.paths.bars({ size: [0.8, 100] }),
          points: { show: false },
        },
      ],
    }, plotData, chartContainer);
  }

  async function load() {
    loading = true;
    error = '';
    try {
      data = await statsApi.eddington();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load Eddington data';
    } finally {
      loading = false;
    }
    setTimeout(buildChart, 50);
  }

  onMount(load);
</script>

<div class="page">
  <h1>Eddington Number</h1>

  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if data}
    <div class="dash-card hero-card">
      <div class="hero-number">{data.eddington_number}</div>
      <div class="hero-label">
        You have {data.eddington_number} activities of at least {data.eddington_number} {data.unit_label}
      </div>
    </div>

    <div class="dash-card">
      <div class="card-header">
        <h3>Next milestone: {data.next_milestone} {data.unit_label}</h3>
        <span class="progress-count">{data.activities_qualified_for_next} / {data.next_milestone}</span>
      </div>
      <div class="progress-bar-bg">
        <div
          class="progress-bar-fill"
          style="width: {Math.min(100, (data.activities_qualified_for_next / data.next_milestone) * 100)}%"
        ></div>
      </div>
      <div class="progress-remaining">
        {#if data.activities_needed_for_next > 0}
          {data.activities_needed_for_next} more {data.activities_needed_for_next === 1 ? 'activity' : 'activities'} needed
        {:else}
          Ready to reach {data.next_milestone}!
        {/if}
      </div>
    </div>

    {#if data.distribution.length > 0}
      <div class="dash-card">
        <div class="card-header">
          <h3>Distribution</h3>
          <span class="card-subtitle">Activities by distance threshold ({data.unit_label})</span>
        </div>
        <div bind:this={chartContainer} class="chart"></div>
      </div>
    {/if}

    {#if data.qualifying_activities.length > 0}
      <div class="dash-card">
        <div class="card-header">
          <h3>Qualifying Activities</h3>
          <span class="progress-count">{data.qualifying_activities.length}</span>
        </div>
        <div class="qualifying-list">
          {#each data.qualifying_activities as a}
            <button class="qualifying-row" onclick={() => onNavigate?.('activity', a.id)}>
              <div class="q-info">
                <span class="q-name">{a.name}</span>
                <span class="q-meta">{a.sport_type} · {formatDate(a.start_time)}</span>
              </div>
              <div class="q-dist">
                <span class="q-miles">{a.distance_converted.toFixed(1)} {data.unit_label}</span>
                <span class="q-km">{(a.distance_m / 1000).toFixed(1)} km</span>
              </div>
            </button>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>

  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin-bottom: 24px;
  }

  .card-subtitle {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .progress-count {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
  }
  .hero-card {
    text-align: center;
    padding: 40px;
  }
  .hero-number {
    font-size: 80px;
    font-weight: var(--font-weight-medium, 500);
    color: var(--primary);
    line-height: 1;
  }
  .hero-label {
    font-size: var(--font-size-md, 14px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-top: 8px;
  }
  .progress-bar-bg {
    height: 12px;
    background: var(--bg);
    border-radius: 6px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: var(--primary);
    border-radius: 6px;
    transition: width 0.4s ease;
  }
  .progress-remaining {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-top: 8px;
  }
  .chart {
    margin-top: 12px;
  }
  .qualifying-list {
    display: flex;
    flex-direction: column;
  }
  .qualifying-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border: none;
    background: none;
    cursor: pointer;
    text-align: left;
    border-bottom: 0.5px solid var(--border);
    transition: background 0.1s;
    font-family: var(--font-sans);
  }
  .qualifying-row:last-child {
    border-bottom: none;
  }
  .qualifying-row:hover {
    background: var(--hover);
  }
  .q-info {
    display: flex;
    flex-direction: column;
  }
  .q-name {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .q-meta {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    text-transform: capitalize;
  }
  .q-dist {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }
  .q-miles {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .q-km {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    .hero-card { padding: 24px 16px; }
    .hero-number { font-size: 56px; }
    .hero-label { font-size: var(--font-size-base, 13px); }
    .qualifying-row { flex-direction: column; align-items: flex-start; gap: 4px; }
    .q-dist { align-items: flex-start; }
  }
</style>
