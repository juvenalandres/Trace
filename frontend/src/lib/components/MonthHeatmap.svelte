<script lang="ts">
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

  const metrics: { key: Metric; label: string }[] = [
    { key: 'load', label: 'Load' },
    { key: 'time', label: 'Time' },
    { key: 'calories', label: 'Cal' },
  ];

  let selected = $state<Metric>('load');

  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const emptyColor = '#ebedf0';
  const levelColors = ['#B5D4F4', '#378ADD', '#185FA5', '#0C447C'];

  function getValue(day: DayData, metric: Metric): number {
    switch (metric) {
      case 'load': return day.distance_m / 1000;
      case 'time': return day.moving_time_s / 60;
      case 'calories': return day.calories;
    }
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

  function monthCells(year: number, month: number, weekOffset: number, dateMap: Map<string, DayData>, maxVal: number) {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDow = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
    const totalWeeks = Math.ceil((startDow + daysInMonth) / 7);

    const cells: { date: string; value: number; level: number; week: number; dow: number }[] = [];

    for (let week = 0; week < totalWeeks; week++) {
      for (let dow = 0; dow < 7; dow++) {
        const dayNum = week * 7 + dow - startDow + 1;
        if (dayNum < 1 || dayNum > daysInMonth) continue;

        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
        const entry = dateMap.get(dateStr);
        const val = entry ? getValue(entry, selected) : 0;

        let level = 0;
        if (val > 0 && maxVal > 0) {
          const ratio = val / maxVal;
          if (ratio <= 0.25) level = 1;
          else if (ratio <= 0.5) level = 2;
          else if (ratio <= 0.75) level = 3;
          else level = 4;
        }

        cells.push({ date: dateStr, value: val, level, week: week + weekOffset, dow });
      }
    }

    return { cells, totalWeeks };
  }

  let monthInfo = $derived.by(() => {
    const now = new Date();
    const currYear = now.getFullYear();
    const currMonth = now.getMonth();

    // Previous month
    const prevDate = new Date(currYear, currMonth - 1, 1);
    const prevYear = prevDate.getFullYear();
    const prevMonth = prevDate.getMonth();

    const dateMap = new Map<string, DayData>();
    for (const d of data) dateMap.set(d.date, d);

    const allVals = data.map(d => getValue(d, selected)).filter(v => v > 0);
    const maxVal = allVals.length > 0 ? Math.max(...allVals) : 0;

    const spacer = 1; // one spacer column between months

    const prev = monthCells(prevYear, prevMonth, 0, dateMap, maxVal);
    const curr = monthCells(currYear, currMonth, prev.totalWeeks + spacer, dateMap, maxVal);

    const prevName = prevDate.toLocaleString('en', { month: 'short' });
    const currName = now.toLocaleString('en', { month: 'short' });
    const currLong = now.toLocaleString('en', { month: 'long' });
    const prevYearLabel = prevYear !== currYear ? ` ${prevYear}` : '';

    const cols: string[] = [];
    for (let i = 0; i < prev.totalWeeks; i++) cols.push('20px');
    cols.push('8px');
    for (let i = 0; i < curr.totalWeeks; i++) cols.push('20px');

    return {
      cells: [...prev.cells, ...curr.cells],
      totalWeeks: prev.totalWeeks + spacer + curr.totalWeeks,
      colTemplate: cols.join(' '),
      prevLabel: prevName + prevYearLabel,
      currLabel: currName,
      prevWeeks: prev.totalWeeks,
      currWeeks: curr.totalWeeks,
      currTitle: `${currLong} ${currYear}`,
    };
  });
</script>

<div class="heatmap-wrap">
  <div class="heatmap-header">
    <span class="heatmap-title">Activity heatmap</span>
    <span class="month-badge">{monthInfo.currTitle}</span>
  </div>

  <div class="heatmap-body">
    <div class="day-labels">
      {#each dayLabels as label}
        <span class="day-label">{label}</span>
      {/each}
    </div>
    <div class="grid-area">
      <div class="month-labels" style="grid-template-columns: {monthInfo.colTemplate}">
        <span class="month-label" style="grid-column: 1 / span {monthInfo.prevWeeks}">{monthInfo.prevLabel}</span>
        <span class="month-label" style="grid-column: {monthInfo.prevWeeks + 2} / -1">{monthInfo.currLabel}</span>
      </div>
      <div class="grid" style="grid-template-columns: {monthInfo.colTemplate}">
        {#each monthInfo.cells as cell}
          <div
            class="cell"
            class:empty={cell.level === 0}
            class:level-1={cell.level === 1}
            class:level-2={cell.level === 2}
            class:level-3={cell.level === 3}
            class:level-4={cell.level === 4}
            style="grid-column: {cell.week + 1}; grid-row: {cell.dow + 1}"
            title="{cell.date}: {formatValue(cell.value, selected)}"
          ></div>
        {/each}
      </div>
    </div>
  </div>

  <div class="legend">
    <span class="legend-label">Less</span>
    <span class="legend-cell" style="background: {emptyColor}"></span>
    {#each levelColors as color, i}
      <span class="legend-cell" style="background: {color}"></span>
    {/each}
    <span class="legend-label">More</span>
  </div>
</div>

<style>
  .heatmap-wrap {
    width: 100%;
  }
  .heatmap-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  .heatmap-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
  }
  .month-badge {
    font-size: 12px;
    font-weight: 500;
    color: var(--text);
    background: var(--bg);
    padding: 4px 10px;
    border-radius: 12px;
    border: 0.5px solid var(--border);
  }
  .heatmap-body {
    width: 100%;
    display: flex;
    gap: 8px;
  }
  .day-labels {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding-top: 20px;
  }
  .day-label {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    line-height: 20px;
    height: 20px;
    display: flex;
    align-items: center;
  }
  .grid-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .month-labels {
    display: grid;
    gap: 2px;
    height: 16px;
    margin-bottom: 4px;
  }
  .month-label {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
  }
  .grid {
    display: grid;
    grid-template-rows: repeat(7, 20px);
    gap: 2px;
  }
  .cell {
    width: 100%;
    height: 100%;
    border-radius: 3px;
  }
  .cell.empty {
    background: var(--heatmap-empty, #ebedf0);
  }
  .cell.level-1 {
    background: #B5D4F4;
  }
  .cell.level-2 {
    background: #378ADD;
  }
  .cell.level-3 {
    background: #185FA5;
  }
  .cell.level-4 {
    background: #0C447C;
  }
  .legend {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 12px;
    justify-content: flex-end;
  }
  .legend-cell {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }
  .legend-label {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
  }
</style>
