<script lang="ts">
  import { onMount } from 'svelte';
  import { trainingApi } from '$lib/api/types';
  import type { TrainingInsights, CtlResponse, SportLoad, WeeklyLoad, TrainingPlan, WeeklyVolumeResponse } from '$lib/api/types';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import Icon from '$lib/components/Icon.svelte';
  import StatCard from '$lib/components/StatCard.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';

  let insights = $state<TrainingInsights | null>(null);
  let ctlData = $state<CtlResponse | null>(null);
  let plans = $state<TrainingPlan[]>([]);
  let selectedPlanId = $state<number | null>(null);
  let weeklyVolume = $state<WeeklyVolumeResponse | null>(null);
  let loading = $state(true);
  let error = $state('');

  let volumeContainer: HTMLDivElement;
  let paceContainer: HTMLDivElement;
  let pmcContainer: HTMLDivElement;
  let sportLoadContainer: HTMLDivElement;
  let weeklyLoadContainer: HTMLDivElement;
  let acwrTrendContainer: HTMLDivElement;
  let volumeTooltip: HTMLDivElement;
  let paceTooltip: HTMLDivElement;
  let weeklyLoadTooltip: HTMLDivElement;
  let pmcTooltip: HTMLDivElement;
  let chartTooltip: HTMLDivElement;
  let mouseX = 0;
  let mouseY = 0;

  let charts: uPlot[] = [];

  const sportColors: Record<string, string> = {
    run: '#22c55e',
    ride: '#3b82f6',
    swim: '#06b6d4',
    hike: '#f97316',
    walk: '#f59e0b',
    other: '#8b5cf6',
  };

  async function load() {
    loading = true;
    error = '';
    try {
      const [insightsResult, ctlResult, plansResult] = await Promise.all([
        trainingApi.insights(),
        trainingApi.ctl(90).catch(() => null),
        trainingApi.listPlans().catch(() => []),
      ]);
      insights = insightsResult;
      ctlData = ctlResult;
      plans = plansResult;
      if (plans.length > 0) {
        selectedPlanId = plans[0].id;
        await loadWeeklyVolume();
      }
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load insights';
    } finally {
      loading = false;
    }
    setTimeout(() => {
      destroyCharts();
      buildVolumeChart();
      buildPaceChart();
      buildPmcChart();
      buildSportLoadChart();
      buildWeeklyLoadChart();
      buildAcwrTrendChart();
    }, 50);
  }

  async function loadWeeklyVolume() {
    if (!selectedPlanId) {
      weeklyVolume = null;
      return;
    }
    try {
      weeklyVolume = await trainingApi.weeklyVolume(selectedPlanId);
    } catch (e: unknown) {
      console.error('Failed to load weekly volume:', e);
      weeklyVolume = null;
    }
  }

  async function selectPlan(planId: number | null) {
    selectedPlanId = planId;
    await loadWeeklyVolume();
    setTimeout(() => {
      destroyCharts();
      buildVolumeChart();
      buildPaceChart();
      buildPmcChart();
      buildSportLoadChart();
      buildWeeklyLoadChart();
      buildAcwrTrendChart();
    }, 50);
  }

  onMount(load);

  function destroyCharts() {
    charts.forEach(c => c.destroy());
    charts = [];
  }

  function formatKm(m: number): string {
    return (m / 1000).toFixed(1);
  }

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function buildVolumeChart() {
    if (!volumeContainer || !insights || insights.weekly_volume.length === 0) return;
    volumeContainer.innerHTML = '';

    const data = insights.weekly_volume;
    const xData = data.map(d => {
      const parts = d.week_start.split('-');
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2])).getTime() / 1000;
    });
    const distData = data.map(d => d.distance_m / 1000);
    const durData = data.map(d => d.duration_s / 3600);

    // Compute target values from weekly volume data
    let targetDist = 0;
    let targetDur = 0;
    if (weeklyVolume && weeklyVolume.weeks.length > 0) {
      const weeksWithTarget = weeklyVolume.weeks.filter(w => w.total_planned_distance_m > 0 || w.total_planned_duration_s > 0);
      if (weeksWithTarget.length > 0) {
        targetDist = weeksWithTarget.reduce((s, w) => s + w.total_planned_distance_m, 0) / weeksWithTarget.length / 1000;
        targetDur = weeksWithTarget.reduce((s, w) => s + w.total_planned_duration_s, 0) / weeksWithTarget.length / 3600;
      }
    }

    const chartData: uPlot.AlignedData = [
      new Float64Array(xData),
      new Float64Array(distData),
      new Float64Array(durData),
    ];

    const chart = new uPlot({
      width: volumeContainer.clientWidth,
      height: 250,
      padding: [10, 10, 30, 50],
      cursor: { points: { show: false } },
      legend: { show: false },
      axes: [
        {
          stroke: '#888',
          values: (_u, ticks) => ticks.map(t => {
            const d = new Date(t * 1000);
            return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
          }),
          grid: { show: false },
        },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series: [
        {},
        { stroke: '#3b82f6', fill: 'rgba(59,130,246,0.15)', width: 2, points: { show: false } },
        { stroke: '#22c55e', fill: 'rgba(34,197,94,0.1)', width: 2, points: { show: false }, scale: 'y2' },
      ],
      scales: {
        x: { time: false },
        y: { range: (u) => {
          const maxVal = Math.max((u.series[1].max ?? 10), targetDist);
          return [0, maxVal * 1.1];
        }},
        y2: { range: (u) => {
          const maxVal = Math.max((u.series[2].max ?? 1), targetDur);
          return [0, maxVal * 1.1];
        }, side: 1 },
      },
      hooks: {
        draw: [(u: uPlot) => {
          const ctx = u.ctx;
          // Draw target distance line
          if (targetDist > 0) {
            const y = u.valToPos(targetDist, 'y', true);
            ctx.save();
            ctx.strokeStyle = '#3b82f680';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(u.bbox.left, y);
            ctx.lineTo(u.bbox.left + u.bbox.width, y);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#3b82f6';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(`${targetDist.toFixed(0)} km`, u.bbox.left + u.bbox.width - 4, y - 4);
            ctx.restore();
          }
          // Draw target duration line
          if (targetDur > 0) {
            const y = u.valToPos(targetDur, 'y2', true);
            ctx.save();
            ctx.strokeStyle = '#22c55e80';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(u.bbox.left, y);
            ctx.lineTo(u.bbox.left + u.bbox.width, y);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#22c55e';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(`${targetDur.toFixed(1)} h`, u.bbox.left + 4, y - 4);
            ctx.restore();
          }
        }],
        setCursor: [(u: uPlot) => {
          if (u.cursor.idx != null) showTooltip(u.cursor.idx, u, 'volume');
        }],
      },
    }, chartData, volumeContainer);
    charts.push(chart);

    const ro = new ResizeObserver(() => {
      if (volumeContainer) chart.setSize({ width: volumeContainer.clientWidth, height: 250 });
    });
    ro.observe(volumeContainer);
  }

  function buildPaceChart() {
    if (!paceContainer || !insights) return;
    paceContainer.innerHTML = '';

    const trends = insights.pace_trends;
    const sports = Object.keys(trends).filter(s => trends[s].some(p => p.avg_speed !== null));
    if (sports.length === 0) return;

    const allWeeks = insights.weekly_volume.map(d => {
      const parts = d.week_start.split('-');
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2])).getTime() / 1000;
    });

    const series: uPlot.Series[] = [
      {},
      ...sports.map(sport => ({
        label: sport,
        stroke: sportColors[sport] ?? sportColors.other,
        width: 2,
        points: { show: false },
      })),
    ];

    const chartData: uPlot.AlignedData = [
      new Float64Array(allWeeks),
      ...sports.map(sport => {
        const points = trends[sport];
        return new Float64Array(points.map(p => p.avg_speed ?? 0));
      }),
    ];

    const chart = new uPlot({
      width: paceContainer.clientWidth,
      height: 250,
      padding: [10, 10, 30, 50],
      cursor: { points: { show: false } },
      legend: { show: false },
      axes: [
        {
          stroke: '#888',
          values: (_u, ticks) => ticks.map(t => {
            const d = new Date(t * 1000);
            return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
          }),
          grid: { show: false },
        },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series,
      scales: {
        x: { time: false },
        y: { range: (u) => {
          const vals = u.series.slice(1).flatMap(s => (s.max ?? 0) > 0 ? [s.max!] : []);
          const max = vals.length > 0 ? Math.max(...vals) : 10;
          return [0, max * 1.1];
        }},
      },
      hooks: {
        setCursor: [(u: uPlot) => {
          if (u.cursor.idx != null) showTooltip(u.cursor.idx, u, 'pace');
        }],
      },
    }, chartData, paceContainer);
    charts.push(chart);

    const ro = new ResizeObserver(() => {
      if (paceContainer) chart.setSize({ width: paceContainer.clientWidth, height: 250 });
    });
    ro.observe(paceContainer);
  }

  function buildPmcChart() {
    if (!pmcContainer || !ctlData || ctlData.data.length === 0) return;
    pmcContainer.innerHTML = '';

    const data = ctlData.data;
    const xData = data.map(d => {
      const parts = d.date.split('-');
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2])).getTime() / 1000;
    });

    const chartData: uPlot.AlignedData = [
      new Float64Array(xData),
      new Float64Array(data.map(d => d.ctl)),
      new Float64Array(data.map(d => d.atl)),
      new Float64Array(data.map(d => d.tsb)),
    ];

    const chart = new uPlot({
      width: pmcContainer.clientWidth,
      height: 300,
      padding: [10, 10, 30, 50],
      cursor: { points: { show: false } },
      legend: { show: false },
      axes: [
        {
          stroke: '#888',
          values: (_u, ticks) => ticks.map(t => {
            const d = new Date(t * 1000);
            return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
          }),
          grid: { show: false },
        },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series: [
        {},
        { label: 'CTL', stroke: '#3b82f6', width: 2, points: { show: false } },
        { label: 'ATL', stroke: '#ef4444', width: 2, points: { show: false } },
        { label: 'TSB', stroke: '#22c55e', width: 0, points: { show: false }, fill: 'rgba(34,197,94,0.2)' },
      ],
      scales: {
        x: { time: false },
        y: {
          range: (u) => {
            // u.data[1] = CTL, u.data[2] = ATL, u.data[3] = TSB
            const allVals: number[] = [];
            for (let i = 1; i < u.data.length; i++) {
              const arr = u.data[i] as Float64Array;
              for (let j = 0; j < arr.length; j++) {
                if (arr[j] != null && !isNaN(arr[j])) allVals.push(arr[j]);
              }
            }
            if (allVals.length === 0) return [-20, 20];
            const min = Math.min(...allVals);
            const max = Math.max(...allVals);
            const pad = (max - min) * 0.1 || 10;
            return [min - pad, max + pad];
          },
        },
      },
      hooks: {
        setCursor: [(u: uPlot) => {
          if (u.cursor.idx != null) showTooltip(u.cursor.idx, u, 'pmc');
        }],
      },
    }, chartData, pmcContainer);
    charts.push(chart);

    const ro = new ResizeObserver(() => {
      if (pmcContainer) chart.setSize({ width: pmcContainer.clientWidth, height: 300 });
    });
    ro.observe(pmcContainer);
  }

  function buildSportLoadChart() {
    if (!sportLoadContainer || !ctlData || ctlData.sport_load.length === 0) return;
    sportLoadContainer.innerHTML = '';

    const data = ctlData.sport_load;
    const totalLoad = data.reduce((s, d) => s + d.total_load, 0);
    if (totalLoad <= 0) return;

    const sorted = [...data].sort((a, b) => b.total_load - a.total_load);
    
    // Build horizontal bar chart
    const barHeight = 28;
    const gap = 6;
    const labelWidth = 60;
    const chartHeight = sorted.length * (barHeight + gap);
    const maxLoad = Math.max(...sorted.map(d => d.total_load));
    
    const containerWidth = sportLoadContainer.clientWidth;
    const barAreaWidth = containerWidth - labelWidth - 60;

    let html = '';
    sorted.forEach((d, i) => {
      const pct = ((d.total_load / totalLoad) * 100).toFixed(1);
      const barWidth = maxLoad > 0 ? (d.total_load / maxLoad) * barAreaWidth : 0;
      const color = sportColors[d.sport_type] ?? sportColors.other;
      const y = i * (barHeight + gap);
      
      html += `<div class="sport-bar-row" style="top: ${y}px; height: ${barHeight}px;">`;
      html += `<span class="sport-bar-label">${d.sport_type}</span>`;
      html += `<div class="sport-bar-track">`;
      html += `<div class="sport-bar-fill" style="width: ${barWidth}px; background: ${color}"></div>`;
      html += `</div>`;
      html += `<span class="sport-bar-value">${pct}%</span>`;
      html += `</div>`;
    });

    sportLoadContainer.style.height = `${chartHeight}px`;
    sportLoadContainer.innerHTML = html;
  }

  function buildWeeklyLoadChart() {
    if (!weeklyLoadContainer || !ctlData || ctlData.weekly_loads.length === 0) return;
    weeklyLoadContainer.innerHTML = '';

    const data = ctlData.weekly_loads;
    const xData = data.map(d => {
      const parts = d.week_start.split('-');
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2])).getTime() / 1000;
    });
    const loadData = data.map(d => d.load);

    const chartData: uPlot.AlignedData = [
      new Float64Array(xData),
      new Float64Array(loadData),
    ];

    const chart = new uPlot({
      width: weeklyLoadContainer.clientWidth,
      height: 200,
      padding: [10, 10, 30, 50],
      cursor: { points: { show: false } },
      legend: { show: false },
      axes: [
        {
          stroke: '#888',
          values: (_u, ticks) => ticks.map(t => {
            const d = new Date(t * 1000);
            return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
          }),
          grid: { show: false },
        },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series: [
        {},
        {
          stroke: '#8b5cf6',
          fill: 'rgba(139,92,246,0.2)',
          width: 1.5,
          points: { show: false },
          paths: uPlot.paths.bars({ size: [0.6, 100] }),
        },
      ],
      scales: {
        x: { time: false },
        y: { range: (u) => [0, (u.series[1].max ?? 10) * 1.1] },
      },
      hooks: {
        setCursor: [(u: uPlot) => {
          if (u.cursor.idx != null) showTooltip(u.cursor.idx, u, 'weeklyLoad');
        }],
      },
    }, chartData, weeklyLoadContainer);
    charts.push(chart);

    const ro = new ResizeObserver(() => {
      if (weeklyLoadContainer) chart.setSize({ width: weeklyLoadContainer.clientWidth, height: 200 });
    });
    ro.observe(weeklyLoadContainer);
  }

  function buildAcwrTrendChart() {
    if (!acwrTrendContainer || !ctlData || ctlData.data.length < 14) return;
    acwrTrendContainer.innerHTML = '';

    const data = ctlData.data;
    // Compute ACWR for each day (need 7 days minimum)
    const acwrPoints: { date: number; value: number }[] = [];
    
    for (let i = 6; i < data.length; i++) {
      const acute = data.slice(i - 6, i + 1).reduce((s, d) => s + d.training_load, 0);
      const chronicDays = Math.min(28, i + 1);
      const chronicSum = data.slice(i - chronicDays + 1, i + 1).reduce((s, d) => s + d.training_load, 0);
      const chronicAvg = chronicSum / (chronicDays / 7);
      
      if (chronicAvg > 0) {
        const parts = data[i].date.split('-');
        acwrPoints.push({
          date: new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2])).getTime() / 1000,
          value: acute / chronicAvg,
        });
      }
    }

    if (acwrPoints.length === 0) return;

    const chartData: uPlot.AlignedData = [
      new Float64Array(acwrPoints.map(p => p.date)),
      new Float64Array(acwrPoints.map(p => p.value)),
    ];

    const chart = new uPlot({
      width: acwrTrendContainer.clientWidth,
      height: 200,
      padding: [10, 10, 30, 50],
      cursor: { points: { show: false } },
      legend: { show: false },
      axes: [
        {
          stroke: '#888',
          values: (_u, ticks) => ticks.map(t => {
            const d = new Date(t * 1000);
            return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
          }),
          grid: { show: false },
        },
        { stroke: '#888', grid: { stroke: '#eee' } },
      ],
      series: [
        {},
        {
          stroke: '#f59e0b',
          width: 2,
          points: { show: false },
        },
      ],
      scales: {
        x: { time: false },
        y: { range: (u) => {
          const vals = u.data[1] as Float64Array;
          let max = 0;
          for (let i = 0; i < vals.length; i++) {
            if (vals[i] > max) max = vals[i];
          }
          return [0, Math.max(max * 1.1, 2.0)];
        }},
      },
      hooks: {
        setCursor: [(u: uPlot) => {
          if (u.cursor.idx != null) showTooltip(u.cursor.idx, u, 'acwr');
        }],
      },
    }, chartData, acwrTrendContainer);
    charts.push(chart);

    const ro = new ResizeObserver(() => {
      if (acwrTrendContainer) chart.setSize({ width: acwrTrendContainer.clientWidth, height: 200 });
    });
    ro.observe(acwrTrendContainer);
  }

  function showTooltip(idx: number, activeChart: uPlot, type: 'pmc' | 'acwr' | 'volume' | 'pace' | 'weeklyLoad') {
    const tooltip = type === 'pmc' ? pmcTooltip : type === 'acwr' ? chartTooltip : type === 'volume' ? volumeTooltip : type === 'pace' ? paceTooltip : weeklyLoadTooltip;
    if (!tooltip) return;

    let html = '';
    
    if (type === 'pmc' && ctlData && idx < ctlData.data.length) {
      const point = ctlData.data[idx];
      const dateParts = point.date.split('-');
      const dateStr = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
      
      html = `<div class="tooltip-date">${dateStr}</div>`;
      html += '<div class="tooltip-metrics">';
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#3b82f6"></span>CTL (Fitness): ${point.ctl.toFixed(1)}</div>`;
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#ef4444"></span>ATL (Fatigue): ${point.atl.toFixed(1)}</div>`;
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#22c55e"></span>TSB (Form): ${point.tsb.toFixed(1)}</div>`;
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#8b5cf6"></span>Load: ${point.training_load.toFixed(1)}</div>`;
      html += '</div>';
    } else if (type === 'acwr' && ctlData && ctlData.data.length >= 14) {
      const data = ctlData.data;
      if (idx + 7 <= data.length) {
        const acute = data.slice(idx, idx + 7).reduce((s, d) => s + d.training_load, 0);
        const chronicDays = Math.min(28, idx + 7);
        const chronicSum = data.slice(idx, idx + chronicDays).reduce((s, d) => s + d.training_load, 0);
        const chronicAvg = chronicSum / (chronicDays / 7);
        
        if (chronicAvg > 0) {
          const acwr = acute / chronicAvg;
          const dateParts = data[idx + 6]?.date.split('-') ?? data[idx].date.split('-');
          const dateStr = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
          
          const status = acwr < 0.8 ? 'Undertrained' : acwr <= 1.0 ? 'Well-managed' : acwr <= 1.3 ? 'Sweet spot' : acwr <= 1.5 ? 'Caution' : 'Danger';
          const color = acwr < 0.8 ? '#3b82f6' : acwr <= 1.3 ? '#22c55e' : acwr <= 1.5 ? '#f59e0b' : '#ef4444';
          
          html = `<div class="tooltip-date">${dateStr}</div>`;
          html += '<div class="tooltip-metrics">';
          html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:${color}"></span>ACWR: ${acwr.toFixed(2)}</div>`;
          html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#8b5cf6"></span>Acute (7d): ${acute.toFixed(0)}</div>`;
          html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#6b7280"></span>Chronic (28d avg/wk): ${chronicAvg.toFixed(0)}</div>`;
          html += `<div class="tooltip-row" style="color:${color};font-weight:600">${status}</div>`;
          html += '</div>';
        }
      }
    } else if (type === 'volume' && insights && idx < insights.weekly_volume.length) {
      const week = insights.weekly_volume[idx];
      const parts = week.week_start.split('-');
      const dateStr = `Week of ${parts[2]}/${parts[1]}`;
      
      html = `<div class="tooltip-date">${dateStr}</div>`;
      html += '<div class="tooltip-metrics">';
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#3b82f6"></span>Distance: ${(week.distance_m / 1000).toFixed(1)} km</div>`;
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#22c55e"></span>Duration: ${formatDuration(week.duration_s)}</div>`;
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#8b5cf6"></span>Activities: ${week.count}</div>`;
      html += '</div>';
    } else if (type === 'pace' && insights && idx < insights.weekly_volume.length) {
      const week = insights.weekly_volume[idx];
      const parts = week.week_start.split('-');
      const dateStr = `Week of ${parts[2]}/${parts[1]}`;
      
      html = `<div class="tooltip-date">${dateStr}</div>`;
      html += '<div class="tooltip-metrics">';
      const trends = insights.pace_trends;
      Object.keys(trends).forEach(sport => {
        if (idx < trends[sport].length && trends[sport][idx].avg_speed !== null) {
          const speed = trends[sport][idx].avg_speed!;
          const color = sportColors[sport] ?? sportColors.other;
          html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:${color}"></span>${sport}: ${speed.toFixed(1)} m/s</div>`;
        }
      });
      html += '</div>';
    } else if (type === 'weeklyLoad' && ctlData && idx < ctlData.weekly_loads.length) {
      const load = ctlData.weekly_loads[idx];
      const parts = load.week_start.split('-');
      const dateStr = `Week of ${parts[2]}/${parts[1]}`;
      
      html = `<div class="tooltip-date">${dateStr}</div>`;
      html += '<div class="tooltip-metrics">';
      html += `<div class="tooltip-row"><span class="tooltip-dot" style="background:#8b5cf6"></span>Load: ${load.load.toFixed(0)}</div>`;
      html += '</div>';
    }

    if (html) {
      tooltip.innerHTML = html;
      tooltip.style.display = 'block';

      const tooltipWidth = tooltip.offsetWidth;
      const tooltipHeight = tooltip.offsetHeight;

      let finalLeft = mouseX + 15;
      let finalTop = mouseY - tooltipHeight - 10;

      if (finalLeft + tooltipWidth > window.innerWidth) {
        finalLeft = mouseX - tooltipWidth - 15;
      }
      if (finalTop < 0) {
        finalTop = mouseY + 15;
      }

      tooltip.style.left = `${finalLeft}px`;
      tooltip.style.top = `${finalTop}px`;
    }
  }

  function hideTooltip(tooltip: HTMLDivElement) {
    if (tooltip) tooltip.style.display = 'none';
  }

  function handleMouseMove(e: MouseEvent) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }

  let totalDistance = $derived(
    insights ? insights.weekly_volume.reduce((s, w) => s + w.distance_m, 0) : 0
  );
  let totalDuration = $derived(
    insights ? insights.weekly_volume.reduce((s, w) => s + w.duration_s, 0) : 0
  );
  let totalActivities = $derived(
    insights ? insights.weekly_volume.reduce((s, w) => s + w.count, 0) : 0
  );
  let avgWeeklyKm = $derived(
    insights && insights.total_weeks > 0 ? totalDistance / 1000 / insights.total_weeks : 0
  );

  let currentCtl = $derived(ctlData && ctlData.data.length > 0 ? ctlData.data[ctlData.data.length - 1].ctl : null);
  let currentAtl = $derived(ctlData && ctlData.data.length > 0 ? ctlData.data[ctlData.data.length - 1].atl : null);
  let currentTsb = $derived(ctlData && ctlData.data.length > 0 ? ctlData.data[ctlData.data.length - 1].tsb : null);
  let tsbStatus = $derived.by(() => {
    if (currentTsb === null) return null;
    if (currentTsb >= 15) return { label: 'Peak Form', color: '#22c55e' };
    if (currentTsb >= 5) return { label: 'Fresh', color: '#22c55e' };
    if (currentTsb >= -10) return { label: 'Balanced', color: '#f59e0b' };
    if (currentTsb >= -30) return { label: 'Fatigued', color: '#f97316' };
    return { label: 'Overreaching', color: '#ef4444' };
  });
</script>

<div class="page">
  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if insights}
    <div class="page-header">
      <h1>Training Insights</h1>
      {#if plans.length > 0}
        <div class="plan-selector">
          <button class="plan-tab" class:active={selectedPlanId === null} onclick={() => selectPlan(null)}>All Plans</button>
          {#each plans as p}
            <button class="plan-tab" class:active={selectedPlanId === p.id} onclick={() => selectPlan(p.id)}>{p.name}</button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Section 1: Overview -->
    <div class="section">
      <h2 class="section-title">Overview</h2>
      <div class="stat-grid">
        <StatCard label="Streak" value={insights.consistency_streak} unit="weeks" icon="milestones" />
        <StatCard label="Avg Weekly" value={avgWeeklyKm.toFixed(1)} unit="km" icon="distance" color="#3b82f6" bg="#3b82f620" />
        <StatCard label="Total Distance" value={formatKm(totalDistance)} unit="km" icon="distance" color="#3b82f6" bg="#3b82f620" />
        <StatCard label="Total Duration" value={formatDuration(totalDuration)} icon="duration" color="#14b8a6" bg="#14b8a620" />
      </div>
      {#if currentCtl !== null}
        <div class="metric-row">
          <div class="metric-card">
            <div class="metric-label">CTL (Fitness)</div>
            <div class="metric-value" style="color: #3b82f6">{currentCtl.toFixed(1)}</div>
            <div class="metric-desc">42-day rolling average</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">ATL (Fatigue)</div>
            <div class="metric-value" style="color: #ef4444">{currentAtl?.toFixed(1)}</div>
            <div class="metric-desc">7-day rolling average</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">TSB (Form)</div>
            <div class="metric-value" style="color: {tsbStatus?.color ?? '#6b7280'}">{currentTsb?.toFixed(1)}</div>
            {#if tsbStatus}
              <div class="metric-badge" style="background: {tsbStatus.color}20; color: {tsbStatus.color}">{tsbStatus.label}</div>
            {/if}
          </div>
          {#if ctlData?.acwr}
            <div class="metric-card">
              <div class="metric-label">ACWR</div>
              <div class="metric-value" style="color: {ctlData.acwr.color}">{ctlData.acwr.value}</div>
              <div class="metric-badge" style="background: {ctlData.acwr.color}20; color: {ctlData.acwr.color}">{ctlData.acwr.status}</div>
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Section 2: Performance Management -->
    <div class="section">
      <h2 class="section-title">Performance Management</h2>
      {#if ctlData && ctlData.data.length > 0}
        <div class="chart-card">
          <div class="chart-header">
            <h3>CTL / ATL / TSB</h3>
            <div class="pmc-legend">
              <span class="legend-item"><span class="legend-line" style="background: #3b82f6"></span>CTL (Fitness)</span>
              <span class="legend-item"><span class="legend-line" style="background: #ef4444"></span>ATL (Fatigue)</span>
              <span class="legend-item"><span class="legend-area"></span>TSB (Form)</span>
            </div>
          </div>
          <div
            class="chart-container"
            bind:this={pmcContainer}
            onmouseleave={() => hideTooltip(pmcTooltip)}
            onmousemove={handleMouseMove}
          ></div>
          <div bind:this={pmcTooltip} class="chart-tooltip" style="display: none;"></div>
        </div>

        <div class="chart-row">
          <div class="chart-card half">
            <div class="chart-header">
              <h3>Weekly Training Load</h3>
            </div>
            {#if ctlData && ctlData.weekly_loads.length > 0}
              <div
                class="chart-container"
                bind:this={weeklyLoadContainer}
                onmouseleave={() => hideTooltip(weeklyLoadTooltip)}
                onmousemove={handleMouseMove}
              ></div>
              <div bind:this={weeklyLoadTooltip} class="chart-tooltip" style="display: none;"></div>
            {:else}
              <p class="no-data">Not enough data yet. Upload activities to see weekly load trends.</p>
            {/if}
          </div>
          <div class="chart-card half">
            <div class="chart-header">
              <h3>ACWR Trend</h3>
              <div class="acwr-zones">
                <span class="zone" style="background: #22c55e20">0.8-1.3</span>
                <span class="zone" style="background: #f59e0b20">1.3-1.5</span>
                <span class="zone" style="background: #ef444420">&gt;1.5</span>
              </div>
            </div>
            {#if ctlData && ctlData.data.length >= 14}
              <div
                class="chart-container"
                bind:this={acwrTrendContainer}
                onmouseleave={() => hideTooltip(chartTooltip)}
                onmousemove={handleMouseMove}
              ></div>
              <div bind:this={chartTooltip} class="chart-tooltip" style="display: none;"></div>
            {:else}
              <p class="no-data">Need at least 14 days of data to show ACWR trend.</p>
            {/if}
          </div>
        </div>
      {:else}
        <p class="no-data">Not enough data for performance management charts. Upload activities with heart rate data to get started.</p>
      {/if}
    </div>

    <!-- Section 3: Volume & Trends -->
    <div class="section">
      <h2 class="section-title">Volume & Trends</h2>
      <div class="chart-row">
        <div class="chart-card half">
          <div class="chart-header">
            <h3>Weekly Volume</h3>
            <div class="volume-legend">
              <span class="legend-item"><span class="legend-dot" style="background: #3b82f6"></span>Distance (km)</span>
              <span class="legend-item"><span class="legend-dot" style="background: #22c55e"></span>Duration (h)</span>
            </div>
          </div>
          <div
            class="chart-container"
            bind:this={volumeContainer}
            onmouseleave={() => hideTooltip(volumeTooltip)}
            onmousemove={handleMouseMove}
          ></div>
          <div bind:this={volumeTooltip} class="chart-tooltip" style="display: none;"></div>
        </div>
        <div class="chart-card half">
          <div class="chart-header">
            <h3>Speed Trends</h3>
          </div>
          {#if Object.keys(insights.pace_trends).length === 0}
            <p class="no-data">Not enough data for speed trends.</p>
          {:else}
            <div
              class="chart-container"
              bind:this={paceContainer}
              onmouseleave={() => hideTooltip(paceTooltip)}
              onmousemove={handleMouseMove}
            ></div>
            <div bind:this={paceTooltip} class="chart-tooltip" style="display: none;"></div>
            <div class="sport-legend">
              {#each Object.entries(sportColors) as [sport, color]}
                {#if insights.pace_trends[sport]}
                  <span class="legend-item">
                    <span class="legend-dot" style="background: {color}"></span>
                    {sport}
                  </span>
                {/if}
              {/each}
            </div>
          {/if}
        </div>
      </div>

      {#if ctlData && ctlData.sport_load.length > 0}
        <div class="chart-card">
          <div class="chart-header">
            <h3>Training Load by Sport</h3>
          </div>
          <div class="sport-load-chart" bind:this={sportLoadContainer}></div>
        </div>
      {/if}
    </div>

    <!-- Section 4: Recovery Status -->
    {#if currentTsb !== null}
      <div class="section">
        <h2 class="section-title">Recovery Status</h2>
        <div class="recovery-card">
          <div class="recovery-header">
            <div class="recovery-icon" style="background: {tsbStatus?.color ?? '#6b7280'}20; color: {tsbStatus?.color ?? '#6b7280'}">
              <Icon name="activity" size={24} />
            </div>
            <div>
              <div class="recovery-title" style="color: {tsbStatus?.color}">{tsbStatus?.label}</div>
              <div class="recovery-tsb">TSB: {currentTsb?.toFixed(1)}</div>
            </div>
          </div>
          <div class="recovery-bar-container">
            <div class="recovery-bar">
              <div class="recovery-zone zone-overreaching" style="left: 0; width: 20%"></div>
              <div class="recovery-zone zone-fatigued" style="left: 20%; width: 20%"></div>
              <div class="recovery-zone zone-balanced" style="left: 40%; width: 20%"></div>
              <div class="recovery-zone zone-fresh" style="left: 60%; width: 20%"></div>
              <div class="recovery-zone zone-peak" style="left: 80%; width: 20%"></div>
              <div class="recovery-marker" style="left: {Math.min(100, Math.max(0, ((currentTsb ?? 0) + 50) / 100 * 100))}%"></div>
            </div>
            <div class="recovery-labels">
              <span>-50</span>
              <span>-30</span>
              <span>-10</span>
              <span>+5</span>
              <span>+15</span>
              <span>+25</span>
            </div>
          </div>
          <div class="recovery-guidance">
            {#if currentTsb >= 15}
              You're in peak form. Ideal for racing or key workouts.
            {:else if currentTsb >= 5}
              You're fresh and ready for quality training sessions.
            {:else if currentTsb >= -10}
              You're in a balanced training state. Normal productive training.
            {:else if currentTsb >= -30}
              You're carrying fatigue. Monitor recovery and consider easier sessions.
            {:else}
              You're overreaching significantly. Consider a recovery block to avoid injury.
            {/if}
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .page {
    max-width: 1200px;
  }
  .page-header {
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  .plan-selector {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .plan-tab {
    padding: 5px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
  }
  .plan-tab:hover {
    background: var(--hover);
  }
  .plan-tab.active {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
  }
  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  .section {
    margin-bottom: 36px;
  }
  .section-title {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0 0 16px;
    color: var(--text);
  }
  h3 {
    font-size: var(--font-size-md, 14px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
    color: var(--text);
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  .metric-row {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .metric-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 14px 16px;
    text-align: center;
    flex: 1;
    max-width: 250px;
    min-width: 180px;
  }
  .metric-label {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }
  .metric-value {
    font-size: var(--font-size-3xl, 26px);
    font-weight: var(--font-weight-medium, 500);
    line-height: 1.1;
  }
  .metric-desc {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-top: 4px;
  }
  .metric-badge {
    display: inline-block;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    padding: 2px 8px;
    border-radius: 10px;
    margin-top: 6px;
    text-transform: capitalize;
  }
  .chart-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: var(--card-padding, 16px);
    margin-bottom: 16px;
    position: relative;
  }
  .chart-card.half {
    flex: 1;
    min-width: 0;
  }
  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
  }
  .chart-header h3 {
    font-weight: 600;
  }
  .chart-row {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
  }
  .chart-container {
    width: 100%;
  }
  .pmc-legend, .volume-legend, .sport-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    text-transform: capitalize;
  }
  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .legend-line {
    width: 16px;
    height: 2px;
    border-radius: 1px;
  }
  .legend-area {
    width: 16px;
    height: 10px;
    background: rgba(34, 197, 94, 0.2);
    border: 1px solid rgba(34, 197, 94, 0.5);
    border-radius: 2px;
  }
  .acwr-zones {
    display: flex;
    gap: 6px;
  }
  .zone {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    padding: 2px 6px;
    border-radius: 4px;
  }
  .sport-load-chart {
    position: relative;
    width: 100%;
  }
  :global(.sport-bar-row) {
    position: absolute;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  :global(.sport-bar-label) {
    width: 50px;
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text);
    text-transform: capitalize;
    text-align: right;
    flex-shrink: 0;
  }
  :global(.sport-bar-track) {
    flex: 1;
    height: 20px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
  }
  :global(.sport-bar-fill) {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }
  :global(.sport-bar-value) {
    width: 45px;
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    text-align: right;
    flex-shrink: 0;
  }
  .recovery-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 20px;
  }
  .recovery-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }
  .recovery-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .recovery-title {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
  }
  .recovery-tsb {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .recovery-bar-container {
    margin-bottom: 16px;
  }
  .recovery-bar {
    position: relative;
    height: 12px;
    background: var(--bg);
    border-radius: 6px;
    overflow: hidden;
  }
  .recovery-zone {
    position: absolute;
    top: 0;
    height: 100%;
  }
  .zone-overreaching { background: #ef444440; }
  .zone-fatigued { background: #f9731640; }
  .zone-balanced { background: #f59e0b40; }
  .zone-fresh { background: #22c55e40; }
  .zone-peak { background: #22c55e60; }
  .recovery-marker {
    position: absolute;
    top: -4px;
    width: 4px;
    height: 20px;
    background: var(--text);
    border-radius: 2px;
    transform: translateX(-50%);
  }
  .recovery-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 6px;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .recovery-guidance {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    line-height: 1.5;
  }
  .chart-tooltip {
    position: fixed;
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: 8px;
    padding: 10px 12px;
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    z-index: 1000;
    pointer-events: none;
    min-width: 140px;
  }
  :global(.tooltip-date) {
    font-weight: var(--font-weight-medium, 500);
    font-size: var(--font-size-base, 13px);
    color: var(--text);
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 0.5px solid var(--border-light);
  }
  :global(.tooltip-metrics) {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  :global(.tooltip-row) {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
  }
  :global(.tooltip-dot) {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .no-data {
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    text-align: center;
    padding: 40px 0;
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: var(--font-size-2xl, 22px); }
    .stat-grid { grid-template-columns: repeat(2, 1fr); }
    .chart-row { flex-direction: column; }
    .chart-card.half { width: 100%; }
  }
</style>
