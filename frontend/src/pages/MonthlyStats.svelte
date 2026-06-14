<script lang="ts">
  import { onMount } from 'svelte';
  import { activitiesApi } from '$lib/api/types';
  import type { ActivitySummary } from '$lib/api/types';
  import ActivityTable from '$lib/components/ActivityTable.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import Icon from '$lib/components/Icon.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  const today = new Date();
  let year = $state(today.getFullYear());
  let month = $state(today.getMonth());
  let activities = $state<ActivitySummary[]>([]);
  let loading = $state(true);
  let selectedDate = $state<string | null>(null);
  let showPicker = $state(false);
  let pickerYear = $state(today.getFullYear());
  let pickerRef: HTMLElement | undefined = $state(undefined);

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const sportColors: Record<string, string> = {
    ride: '#378ADD',
    run: '#1D9E75',
    swim: '#06b6d4',
    hike: '#f59e0b',
    walk: '#f59e0b',
    other: '#64748b',
  };

  function formatKm(m: number): string {
    return (m / 1000).toFixed(1);
  }

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function formatDurationColon(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}:${String(m).padStart(2, '0')}`;
  }

  async function loadActivities() {
    loading = true;
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const dateFrom = firstDay.toISOString().slice(0, 10);
    const dateTo = lastDay.toISOString().slice(0, 10);

    try {
      const res = await activitiesApi.list(1, 500, { date_from: dateFrom, date_to: dateTo });
      activities = res.items;
    } catch {
      activities = [];
    } finally {
      loading = false;
    }
  }

  onMount(loadActivities);

  function prevMonth() {
    if (month === 0) {
      month = 11;
      year--;
    } else {
      month--;
    }
    selectedDate = null;
    loadActivities();
  }

  function nextMonth() {
    if (month === 11) {
      month = 0;
      year++;
    } else {
      month++;
    }
    selectedDate = null;
    loadActivities();
  }

  function goToday() {
    year = today.getFullYear();
    month = today.getMonth();
    pickerYear = year;
    selectedDate = null;
    showPicker = false;
    loadActivities();
  }

  function goToMonth(m: number) {
    year = pickerYear;
    month = m;
    selectedDate = null;
    showPicker = false;
    loadActivities();
  }

  function handlePickerKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') showPicker = false;
  }

  $effect(() => {
    if (showPicker && pickerRef) {
      pickerRef.focus();
    }
  });

  interface DayCell {
    date: number;
    dateStr: string;
    isCurrentMonth: boolean;
    isToday: boolean;
    activities: ActivitySummary[];
    totalDist: number;
  }

  function buildCalendar(): DayCell[] {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    let startDow = firstDay.getDay();
    if (startDow === 0) startDow = 7;

    const cells: DayCell[] = [];

    for (let i = startDow - 1; i > 0; i--) {
      const d = new Date(year, month, 1 - i);
      cells.push(makeCell(d, false));
    }

    for (let d = 1; d <= lastDay.getDate(); d++) {
      const date = new Date(year, month, d);
      cells.push(makeCell(date, true));
    }

    const remaining = 7 - (cells.length % 7);
    if (remaining < 7) {
      for (let i = 1; i <= remaining; i++) {
        const d = new Date(year, month + 1, i);
        cells.push(makeCell(d, false));
      }
    }

    return cells;
  }

  function makeCell(date: Date, isCurrentMonth: boolean): DayCell {
    const dateStr = date.toISOString().slice(0, 10);
    const dayActs = activities.filter(a => a.start_time.slice(0, 10) === dateStr);
    const isToday = date.toDateString() === today.toDateString();
    return {
      date: date.getDate(),
      dateStr,
      isCurrentMonth,
      isToday,
      activities: dayActs,
      totalDist: dayActs.reduce((s, a) => s + (a.distance_m ?? 0), 0),
    };
  }

  let calendar = $derived(buildCalendar());

  let selectedDayActivities = $derived(
    selectedDate ? activities.filter(a => a.start_time.slice(0, 10) === selectedDate) : []
  );

  let monthDist = $derived(activities.reduce((s, a) => s + (a.distance_m ?? 0), 0));
  let monthDur = $derived(activities.reduce((s, a) => s + (a.duration_s ?? 0), 0));
  let monthElev = $derived(activities.reduce((s, a) => s + (a.elevation_gain ?? 0), 0));

  let uniqueSports = $derived(() => {
    const sports = new Set<string>();
    for (const a of activities) {
      if (a.sport_type) sports.add(a.sport_type);
    }
    return Array.from(sports);
  });
</script>

<div class="page">
  <!-- Topbar -->
  <div class="month-topbar">
    <h1>Monthly stats</h1>
    <div class="month-nav">
      <button class="nav-btn" onclick={prevMonth}>
        <Icon name="chevronLeft" size={16} />
      </button>
      <button class="month-label" onclick={() => { pickerYear = year; showPicker = !showPicker; }}>
        {monthNames[month]} {year}
      </button>
      {#if showPicker}
        <button class="picker-backdrop" onclick={() => showPicker = false} aria-label="Close month picker"></button>
        <div class="month-picker" bind:this={pickerRef} role="dialog" aria-label="Select month" tabindex="-1" onkeydown={handlePickerKeydown}>
          <div class="picker-year-row">
            <button class="picker-nav" onclick={() => pickerYear--}>
              <Icon name="chevronLeft" size={14} />
            </button>
            <span class="picker-year">{pickerYear}</span>
            <button class="picker-nav" onclick={() => pickerYear++}>
              <Icon name="chevronRight" size={14} />
            </button>
          </div>
          <div class="picker-months">
            {#each monthNames as name, i}
              <button
                class="picker-month"
                class:selected={year === pickerYear && month === i}
                onclick={() => goToMonth(i)}
              >{name.slice(0, 3)}</button>
            {/each}
          </div>
          <button class="picker-today" onclick={goToday}>Today</button>
        </div>
      {/if}
      <button class="nav-btn" onclick={nextMonth}>
        <Icon name="chevronRight" size={16} />
      </button>
    </div>
  </div>

  {#if loading}
    <LoadingSpinner />
  {:else}
    <!-- Metric Cards -->
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-icon" style="background: #3b82f620; color: #3b82f6">
          <Icon name="distance" size={18} />
        </div>
        <div class="metric-label">Distance</div>
        <div class="metric-value">{formatKm(monthDist)} <span class="metric-unit">km</span></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon" style="background: #14b8a620; color: #14b8a6">
          <Icon name="duration" size={18} />
        </div>
        <div class="metric-label">Duration</div>
        <div class="metric-value">{formatDurationColon(monthDur)} <span class="metric-unit">h</span></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon" style="background: #f59e0b20; color: #f59e0b">
          <Icon name="elevation" size={18} />
        </div>
        <div class="metric-label">Elevation</div>
        <div class="metric-value">{Math.round(monthElev)} <span class="metric-unit">m</span></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon" style="background: #f9731620; color: #f97316">
          <Icon name="activity" size={18} />
        </div>
        <div class="metric-label">Activities</div>
        <div class="metric-value">{activities.length}</div>
      </div>
    </div>

    <!-- Activity Calendar -->
    <div class="dash-card">
      <div class="card-header">
        <h3>Activity calendar</h3>
        <div class="calendar-legend">
          {#each uniqueSports() as sport}
            <span class="legend-item">
              <span class="legend-dot" style="background: {sportColors[sport] ?? sportColors.other}"></span>
              <span class="legend-text">{sport}</span>
            </span>
          {/each}
        </div>
      </div>
      <div class="calendar-header">
        {#each dayNames as d}
          <div class="day-header">{d}</div>
        {/each}
      </div>
      <div class="calendar-grid">
        {#each calendar as cell}
          <button
            class="day-cell"
            class:other-month={!cell.isCurrentMonth}
            class:today={cell.isToday}
            class:has-activity={cell.activities.length > 0}
            onclick={() => selectedDate = selectedDate === cell.dateStr ? null : cell.dateStr}
          >
            <div class="day-inner">
              <span class="day-num" class:today={cell.isToday} class:active={cell.activities.length > 0 && !cell.isToday}>
                {cell.date}
              </span>
              {#if cell.activities.length > 0}
                <div class="activity-badges">
                  {#each cell.activities as a}
                    <span class="sport-badge" style="background: {sportColors[a.sport_type] ?? sportColors.other}20; color: {sportColors[a.sport_type] ?? sportColors.other}">{formatKm(a.distance_m)} km</span>
                  {/each}
                </div>
              {/if}
            </div>
          </button>
        {/each}
      </div>
    </div>

    {#if selectedDate && selectedDayActivities.length > 0}
      <div class="selected-section">
        <h2>{new Date(selectedDate + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</h2>
        <ActivityTable activities={selectedDayActivities} onRowClick={(id) => onNavigate?.('activity', id)} />
      </div>
    {:else if selectedDate}
      <div class="selected-section">
        <h2>{new Date(selectedDate + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</h2>
        <p class="no-activities">No activities on this day.</p>
      </div>
    {/if}
  {/if}
</div>

<style>
  .page {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
    font-family: var(--font-sans);
  }
  .month-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }
  h1 {
    font-size: var(--font-size-2xl, 22px);
    font-weight: var(--font-weight-medium, 500);
    margin: 0;
  }
  h2 {
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    margin-bottom: 12px;
  }
  .month-nav {
    display: flex;
    align-items: center;
    gap: 4px;
    background: var(--bg);
    border-radius: 10px;
    padding: 4px;
  }
  .nav-btn {
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 8px;
    background: none;
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .nav-btn:hover {
    color: var(--text);
  }
  .month-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    padding: 8px 16px;
    font-family: var(--font-sans);
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    min-width: 90px;
    text-align: center;
  }
  .month-label:hover {
    background: var(--hover);
  }

  /* Metric Cards */
  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }
  .metric-card {
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }
  .metric-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
  }
  .metric-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }
  .metric-value {
    font-size: 26px;
    font-weight: 500;
    color: var(--text);
    line-height: 1.1;
  }
  .metric-unit {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
  }

  /* Calendar Card */
  .dash-card {
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 24px;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  .card-header h3 {
    font-size: 14px;
    font-weight: 600;
    margin: 0;
    color: var(--text);
  }
  .calendar-legend {
    display: flex;
    gap: 12px;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .legend-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }
  .legend-text {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    text-transform: capitalize;
  }

  .calendar-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    border-bottom: 0.5px solid var(--border);
  }
  .day-header {
    padding: 10px 0;
    text-align: center;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }

  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
  }
  .day-cell {
    height: 72px;
    border: none;
    background: none;
    cursor: pointer;
    border-right: 0.5px solid var(--border);
    border-bottom: 0.5px solid var(--border);
    padding: 0;
    transition: background 0.1s;
    font-family: var(--font-sans);
  }
  .day-cell:nth-child(7n) {
    border-right: none;
  }
  .day-cell:nth-last-child(-n+7) {
    border-bottom: none;
  }
  .day-cell:hover {
    background: var(--hover);
  }
  .day-cell.other-month {
    opacity: 0.4;
  }
  .day-cell.other-month .day-num {
    color: var(--text-secondary);
  }

  .day-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 8px;
    gap: 4px;
  }
  .day-num {
    font-size: 13px;
    font-weight: 400;
    color: var(--text);
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
  .day-num.active {
    color: #185FA5;
    font-weight: 500;
  }
  .day-num.today {
    background: #378ADD;
    color: #E6F1FB;
    font-weight: 500;
  }
  .activity-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    justify-content: center;
  }
  .sport-badge {
    font-size: 10px;
    font-weight: 500;
    padding: 1px 6px;
    border-radius: 8px;
    line-height: 1.4;
  }

  /* Month Picker */
  .month-nav {
    position: relative;
  }
  .picker-backdrop {
    position: fixed;
    inset: 0;
    z-index: 9;
    border: none;
    background: transparent;
    padding: 0;
  }
  .month-picker {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 10;
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    min-width: 200px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  }
  .picker-year-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .picker-nav {
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 6px;
    background: transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
  }
  .picker-nav:hover {
    background: var(--hover);
  }
  .picker-year {
    font-size: 15px;
    font-weight: 500;
    color: var(--text);
  }
  .picker-months {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-bottom: 12px;
  }
  .picker-month {
    padding: 6px 0;
    border: none;
    border-radius: 6px;
    background: transparent;
    cursor: pointer;
    font-size: 13px;
    font-weight: 400;
    color: var(--text);
    font-family: var(--font-sans);
  }
  .picker-month:hover {
    background: var(--hover);
  }
  .picker-month.selected {
    background: #378ADD;
    color: #fff;
    font-weight: 500;
  }
  .picker-today {
    display: block;
    width: 100%;
    padding: 8px 0;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    background: transparent;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    font-family: var(--font-sans);
    text-align: center;
  }
  .picker-today:hover {
    background: var(--hover);
  }

  .selected-section {
    margin-top: 8px;
  }
  .no-activities {
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 400;
  }

  @media (max-width: 768px) {
    .page { padding: 16px; }
    .metric-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .month-topbar { flex-direction: column; align-items: flex-start; gap: 12px; }
    .day-cell { height: 52px; }
    .day-num { font-size: 11px; }
    .sport-badge { font-size: 8px; padding: 1px 4px; }
  }
</style>
