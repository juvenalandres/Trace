<script lang="ts">
  import Icon from './Icon.svelte';

  interface DayData {
    date: string;
    distance_m: number;
    moving_time_s: number;
    calories: number;
  }

  interface Props {
    data: DayData[];
  }

  let { data }: Props = $props();

  type Metric = 'load' | 'time' | 'calories';

  const metrics: { key: Metric; label: string; icon: string }[] = [
    { key: 'load', label: 'Load', icon: 'bolt' },
    { key: 'time', label: 'Moving time', icon: 'duration' },
    { key: 'calories', label: 'Calories', icon: 'activity' },
  ];

  let selected = $state<Metric>('load');

  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const cellSize = 14;
  const cellGap = 3;
  const labelWidth = 36;
  const headerHeight = 20;

  const emptyColor = 'var(--heatmap-empty, #ebedf0)';
  const levelColors = ['#9be9a8', '#40c463', '#30a14e', '#216e39'];

  function parseDate(s: string): Date {
    const [y, m, d] = s.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  function mondayOfWeek(d: Date): Date {
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    const mon = new Date(d);
    mon.setDate(mon.getDate() + diff);
    return mon;
  }

  interface Cell {
    date: string;
    value: number;
    level: number;
    col: number;
    row: number;
    isFuture: boolean;
  }

  interface MonthLabel {
    label: string;
    col: number;
  }

  function getValue(day: DayData, metric: Metric): number {
    switch (metric) {
      case 'load': return day.distance_m / 1000;
      case 'time': return day.moving_time_s / 60;
      case 'calories': return day.calories;
    }
  }

  function computeCells(metric: Metric): { cells: Cell[]; months: MonthLabel[]; cols: number } {
    if (data.length === 0) return { cells: [], months: [], cols: 0 };

    const map = new Map<string, DayData>();
    for (const d of data) map.set(d.date, d);

    const first = parseDate(data[0].date);
    const last = parseDate(data[data.length - 1].date);
    const startMon = mondayOfWeek(first);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const allVals = data.map(d => getValue(d, metric)).filter(v => v > 0);
    const maxVal = allVals.length > 0 ? Math.max(...allVals) : 1;

    const cells: Cell[] = [];
    const monthSet = new Map<string, number>();
    const cur = new Date(startMon);
    let col = 0;

    while (cur <= last || cur.getDay() !== 1) {
      const row = cur.getDay() === 0 ? 6 : cur.getDay() - 1;
      const dateStr = cur.toISOString().slice(0, 10);
      const entry = map.get(dateStr);
      const val = entry ? getValue(entry, metric) : 0;

      let level = 0;
      if (val > 0) {
        const ratio = val / maxVal;
        if (ratio <= 0.25) level = 1;
        else if (ratio <= 0.5) level = 2;
        else if (ratio <= 0.75) level = 3;
        else level = 4;
      }

      cells.push({
        date: dateStr,
        value: val,
        level,
        col,
        row,
        isFuture: cur > today,
      });

      if (cur.getDate() === 1) {
        const monthName = cur.toLocaleString('en', { month: 'short' });
        if (!monthSet.has(monthName)) monthSet.set(monthName, col);
      }

      if (row === 6) col++;
      cur.setDate(cur.getDate() + 1);
      if (col > 53) break;
    }

    const months: MonthLabel[] = [];
    const seen = new Set<string>();
    for (const [label, c] of monthSet) {
      const key = `${label}-${c}`;
      if (!seen.has(key)) {
        seen.add(key);
        months.push({ label, col: c });
      }
    }
    months.sort((a, b) => a.col - b.col);

    return { cells, months, cols: col + 1 };
  }

  function formatRange(cells: Cell[]): string {
    if (cells.length === 0) return '';
    const first = parseDate(cells[0].date);
    const last = parseDate(cells[cells.length - 1].date);
    const fmt = (d: Date) => d.toLocaleString('en', { month: 'short', year: 'numeric' });
    return `${fmt(first)} \u2013 ${fmt(last)}`;
  }

  function formatValue(v: number, metric: Metric): string {
    switch (metric) {
      case 'load': return `${v.toFixed(1)} km`;
      case 'time': {
        const h = Math.floor(v / 60);
        const m = Math.floor(v % 60);
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
      }
      case 'calories': return `${Math.round(v)} kcal`;
    }
  }

  let grid = $derived(computeCells(selected));
  let rangeLabel = $derived(formatRange(grid.cells));
  let gridWidth = $derived(grid.cols * (cellSize + cellGap));
  let totalWidth = $derived(labelWidth + gridWidth);
  let totalHeight = $derived(headerHeight + 7 * (cellSize + cellGap));
</script>

<div class="heatmap-card">
  <div class="heatmap-header">
    <span class="heatmap-title">Activity Heatmap</span>
    <div class="metric-toggles">
      {#each metrics as m}
        <button
          class="metric-btn"
          class:active={selected === m.key}
          onclick={() => selected = m.key}
        >
          <Icon name={m.icon} size={14} />
          {m.label}
        </button>
      {/each}
    </div>
  </div>

  <div class="heatmap-body">
    {#if grid.cells.length > 0}
      <div class="range-label">{rangeLabel}</div>

      <div class="grid-scroll">
        <svg width={totalWidth} height={totalHeight + 4}>
          {#each grid.months as m}
            <text
              x={labelWidth + m.col * (cellSize + cellGap) + cellSize / 2}
              y={14}
              class="month-label"
              text-anchor="middle"
            >{m.label}</text>
          {/each}

          {#each dayLabels as label, i}
            <text
              x={0}
              y={headerHeight + i * (cellSize + cellGap) + cellSize - 2}
              class="day-label"
            >{label}</text>
          {/each}

          {#each grid.cells as cell}
            {#if !cell.isFuture}
              <rect
                x={labelWidth + cell.col * (cellSize + cellGap)}
                y={headerHeight + cell.row * (cellSize + cellGap)}
                width={cellSize}
                height={cellSize}
                rx={2}
                fill={cell.level === 0 ? emptyColor : levelColors[cell.level - 1]}
              >
                <title>{cell.date}: {formatValue(cell.value, selected)}</title>
              </rect>
            {/if}
          {/each}
        </svg>
      </div>

      <div class="legend">
        <span class="legend-label">No activity</span>
        <span class="legend-cell" style="background: {emptyColor}"></span>
        {#each levelColors as color, i}
          <span class="legend-cell" style="background: {color}"></span>
          <span class="legend-label">
            {#if i === 0}Low{:else if i === 1}Medium{:else if i === 2}High{:else}Very high{/if}
          </span>
        {/each}
      </div>
    {:else}
      <div class="empty">No activity data yet</div>
    {/if}
  </div>
</div>

<style>
  .heatmap-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    overflow: hidden;
  }
  .heatmap-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
    border-bottom: 0.5px solid var(--border);
  }
  .heatmap-title {
    font-size: var(--font-size-md, 14px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .metric-toggles {
    display: flex;
    gap: 6px;
  }
  .metric-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border: 0.5px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
    transition: all 0.15s;
  }
  .metric-btn:hover {
    background: var(--hover);
    color: var(--text);
  }
  .metric-btn.active {
    border-color: var(--primary);
    background: var(--primary-light);
    color: var(--primary);
  }
  .heatmap-body {
    padding: var(--card-padding, 16px);
  }
  .range-label {
    text-align: center;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
    margin-bottom: 12px;
  }
  .grid-scroll {
    overflow-x: auto;
    margin-bottom: 12px;
  }
  .month-label {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    fill: var(--text-secondary);
  }
  .day-label {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    fill: var(--text-secondary);
  }
  .legend {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    margin-top: 8px;
  }
  .legend-cell {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }
  .legend-label {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-right: 6px;
  }
  .empty {
    text-align: center;
    padding: 40px 0;
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
  }
  @media (max-width: 768px) {
    .heatmap-header { flex-direction: column; align-items: flex-start; gap: 8px; }
    .metric-toggles { flex-wrap: wrap; }
    .heatmap-body { padding: 12px; }
  }
</style>
