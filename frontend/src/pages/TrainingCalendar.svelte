<script lang="ts">
  import { onMount } from 'svelte';
  import { trainingApi } from '$lib/api/types';
  import type { TrainingPlan, TrainingSession, WeeklyVolumeResponse, WeeklyVolumeWeek } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  let plans = $state<TrainingPlan[]>([]);
  let loading = $state(true);
  let error = $state('');
  let selectedPlanId = $state<number | null>(null);
  let weeklyVolume = $state<WeeklyVolumeResponse | null>(null);

  let currentYear = $state(new Date().getFullYear());
  let currentMonth = $state(new Date().getMonth());
  let selectedDate = $state<string | null>(null);
  let showDayDetail = $state(false);
  let showPicker = $state(false);
  let pickerYear = $state(new Date().getFullYear());
  let pickerRef: HTMLDivElement;
  let viewMode = $state<'month' | 'week'>('month');
  let weekStartDate = $state(getMonday(new Date()));

  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

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
      plans = await trainingApi.listPlans();
      if (plans.length > 0) {
        selectedPlanId = plans[0].id;
        await loadWeeklyVolume();
      }
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load plans';
    } finally {
      loading = false;
    }
  }

  async function loadWeeklyVolume() {
    if (!selectedPlanId) return;
    try {
      weeklyVolume = await trainingApi.weeklyVolume(selectedPlanId);
    } catch (e: unknown) {
      console.error('Failed to load weekly volume:', e);
    }
  }

  function selectPlan(planId: number) {
    selectedPlanId = planId;
    loadWeeklyVolume();
  }

  onMount(load);

  let allSessions = $derived(
    plans.flatMap(p => p.sessions)
  );

  let blockColorMap = $derived(
    new Map(
      plans.flatMap(p =>
        (p.blocks || []).map((b, i, arr) => [
          b.id,
          arr.length <= 1 ? '#3b82f6' : `hsl(${(i / arr.length) * 360}, 55%, 45%)`,
        ] as const)
      )
    )
  );

  let sessionsByDate = $derived(
    new Map<string, TrainingSession[]>(
      (() => {
        const map = new Map<string, TrainingSession[]>();
        for (const s of allSessions) {
          const existing = map.get(s.scheduled_date) ?? [];
          existing.push(s);
          map.set(s.scheduled_date, existing);
        }
        return [...map.entries()];
      })()
    )
  );

  let calendarDays = $derived((() => {
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const daysInMonth = lastDay.getDate();

    let startDayOfWeek = firstDay.getDay();
    if (startDayOfWeek === 0) startDayOfWeek = 7;

    const days: { date: number; month: 'prev' | 'current' | 'next'; dateStr: string }[] = [];

    const prevMonthLast = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = startDayOfWeek - 1; i > 0; i--) {
      const d = prevMonthLast - i + 1;
      const m = currentMonth === 0 ? 11 : currentMonth - 1;
      const y = currentMonth === 0 ? currentYear - 1 : currentYear;
      days.push({ date: d, month: 'prev', dateStr: `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}` });
    }

    for (let d = 1; d <= daysInMonth; d++) {
      days.push({ date: d, month: 'current', dateStr: `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}` });
    }

    const remaining = days.length % 7 === 0 ? 0 : 7 - (days.length % 7);
    for (let d = 1; d <= remaining; d++) {
      const m = currentMonth === 11 ? 0 : currentMonth + 1;
      const y = currentMonth === 11 ? currentYear + 1 : currentYear;
      days.push({ date: d, month: 'next', dateStr: `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}` });
    }

    return days;
  })());

  let todayStr = $derived(new Date().toISOString().split('T')[0]);

  function prevMonth() {
    if (currentMonth === 0) {
      currentMonth = 11;
      currentYear--;
    } else {
      currentMonth--;
    }
  }

  function nextMonth() {
    if (currentMonth === 11) {
      currentMonth = 0;
      currentYear++;
    } else {
      currentMonth++;
    }
  }

  function goToToday() {
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth();
    pickerYear = currentYear;
    showPicker = false;
  }

  function goToMonth(m: number) {
    currentYear = pickerYear;
    currentMonth = m;
    showPicker = false;
  }

  function getMonday(d: Date): Date {
    const date = new Date(d);
    const day = date.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    date.setDate(date.getDate() + diff);
    date.setHours(0, 0, 0, 0);
    return date;
  }

  function formatDateStr(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  let weekDays = $derived((() => {
    const days: { date: Date; dateStr: string; isToday: boolean }[] = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStartDate);
      d.setDate(d.getDate() + i);
      days.push({
        date: d,
        dateStr: formatDateStr(d),
        isToday: d.getTime() === today.getTime(),
      });
    }
    return days;
  })());

  let weekLabel = $derived((() => {
    const start = weekDays[0].date;
    const end = weekDays[6].date;
    const fmt = (d: Date) => d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    if (start.getMonth() === end.getMonth()) {
      return `${fmt(start)} – ${fmt(end)}, ${end.getFullYear()}`;
    }
    return `${fmt(start)} – ${fmt(end)}, ${end.getFullYear()}`;
  })());

  function prevWeek() {
    const d = new Date(weekStartDate);
    d.setDate(d.getDate() - 7);
    weekStartDate = d;
  }

  function nextWeek() {
    const d = new Date(weekStartDate);
    d.setDate(d.getDate() + 7);
    weekStartDate = d;
  }

  function goToThisWeek() {
    weekStartDate = getMonday(new Date());
  }

  function switchView(mode: 'month' | 'week') {
    viewMode = mode;
    if (mode === 'week') {
      const now = new Date();
      weekStartDate = getMonday(now);
      currentYear = now.getFullYear();
      currentMonth = now.getMonth();
    }
  }

  function handlePickerKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') showPicker = false;
  }

  $effect(() => {
    if (showPicker && pickerRef) {
      pickerRef.focus();
    }
  });

  function selectDay(dateStr: string) {
    selectedDate = dateStr;
    showDayDetail = true;
  }

  let selectedDaySessions = $derived(
    selectedDate ? (sessionsByDate.get(selectedDate) ?? []).sort((a, b) => {
      if (a.rest_day !== b.rest_day) return a.rest_day ? 1 : -1;
      return (a.name ?? '').localeCompare(b.name ?? '');
    }) : []
  );

  function formatTarget(s: TrainingSession): string {
    if (!s.targets || s.targets.length === 0) return 'Free';
    return s.targets.map(t => {
      if (t.type === 'free') return 'Free';
      const parts: string[] = [t.type];
      if (t.value) parts.push(String(t.value));
      if (t.unit) parts.push(t.unit);
      return parts.join(' ');
    }).join(' + ');
  }

  function formatDateLong(dateStr: string): string {
    return new Date(dateStr + 'T12:00:00').toLocaleDateString('en-GB', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  }
</script>

<div class="page">
  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else}
    {#if plans.length > 1}
      <div class="plan-selector">
        {#each plans as p}
          <button class="plan-tab" class:active={selectedPlanId === p.id} onclick={() => selectPlan(p.id)}>
            {p.name}
          </button>
        {/each}
      </div>
    {/if}

    {#if weeklyVolume && weeklyVolume.weeks.length > 0}
      {@const currentWeek = weeklyVolume.weeks.find(w => {
        const weekStart = new Date(w.week_start);
        const now = new Date();
        return weekStart <= now && now < new Date(weekStart.getTime() + 7 * 86400000);
      })}
      {#if currentWeek && (currentWeek.total_planned_distance_m > 0 || currentWeek.total_planned_count > 0)}
        <div class="weekly-progress dash-card">
          <div class="card-header">
            <h3>This Week's Progress</h3>
          </div>
          <div class="progress-grid">
            {#if currentWeek.total_planned_distance_m > 0}
              {@const pct = Math.min(100, (currentWeek.total_actual_distance_m / currentWeek.total_planned_distance_m) * 100)}
              <div class="progress-item">
                <div class="progress-label">
                  <span class="progress-name">Distance</span>
                  <span class="progress-values">{(currentWeek.total_actual_distance_m / 1000).toFixed(1)} / {(currentWeek.total_planned_distance_m / 1000).toFixed(1)} km</span>
                </div>
                <div class="progress-bar-bg">
                  <div class="progress-bar-fill" style="width: {pct}%; background: {pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444'}"></div>
                </div>
              </div>
            {/if}
            {#if currentWeek.total_planned_count > 0}
              {@const pct = Math.min(100, (currentWeek.total_actual_count / currentWeek.total_planned_count) * 100)}
              <div class="progress-item">
                <div class="progress-label">
                  <span class="progress-name">Activities</span>
                  <span class="progress-values">{currentWeek.total_actual_count} / {currentWeek.total_planned_count}</span>
                </div>
                <div class="progress-bar-bg">
                  <div class="progress-bar-fill" style="width: {pct}%; background: {pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444'}"></div>
                </div>
              </div>
            {/if}
            {#each Object.entries(currentWeek.planned) as [sport, planned]}
              {@const actual = currentWeek.actual[sport] ?? { distance_m: 0, duration_s: 0, count: 0 }}
              {#if planned.distance_m > 0}
                {@const pct = Math.min(100, (actual.distance_m / planned.distance_m) * 100)}
                <div class="progress-item">
                  <div class="progress-label">
                    <span class="progress-name"><span class="sport-dot" style="background: {sportColors[sport] ?? sportColors.other}"></span>{sport}</span>
                    <span class="progress-values">{(actual.distance_m / 1000).toFixed(1)} / {(planned.distance_m / 1000).toFixed(1)} km</span>
                  </div>
                  <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: {pct}%; background: {sportColors[sport] ?? sportColors.other}"></div>
                  </div>
                </div>
              {/if}
            {/each}
          </div>
        </div>
      {/if}
    {/if}

    <div class="calendar-header">
      <div class="view-toggle">
        <button class="view-btn" class:active={viewMode === 'month'} onclick={() => switchView('month')}>Month</button>
        <button class="view-btn" class:active={viewMode === 'week'} onclick={() => switchView('week')}>Week</button>
      </div>
      <div class="month-nav">
        <button class="nav-btn" onclick={viewMode === 'month' ? prevMonth : prevWeek} title={viewMode === 'month' ? 'Previous month' : 'Previous week'}>
          <Icon name="chevronLeft" size={16} />
        </button>
        {#if viewMode === 'month'}
          <button class="month-label" onclick={() => { pickerYear = currentYear; showPicker = !showPicker; }}>
            {monthNames[currentMonth]} {currentYear}
          </button>
        {:else}
          <button class="month-label" onclick={goToThisWeek} title="Go to this week">
            {weekLabel}
          </button>
        {/if}
        {#if showPicker && viewMode === 'month'}
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
                  class:selected={currentYear === pickerYear && currentMonth === i}
                  onclick={() => goToMonth(i)}
                >{name.slice(0, 3)}</button>
              {/each}
            </div>
            <button class="picker-today" onclick={goToToday}>Today</button>
          </div>
        {/if}
        <button class="nav-btn" onclick={viewMode === 'month' ? nextMonth : nextWeek} title={viewMode === 'month' ? 'Next month' : 'Next week'}>
          <Icon name="chevronRight" size={16} />
        </button>
      </div>
    </div>

    {#if viewMode === 'month'}
    <div class="calendar-grid">
      {#each dayNames as dayName}
        <div class="day-header">{dayName}</div>
      {/each}

      {#each calendarDays as day}
        {@const sessions = sessionsByDate.get(day.dateStr) ?? []}
        {@const hasSessions = sessions.length > 0}
        {@const isToday = day.dateStr === todayStr}
        <button
          class="day-cell"
          class:other-month={day.month !== 'current'}
          class:today={isToday}
          class:has-sessions={hasSessions}
          onclick={() => selectDay(day.dateStr)}
        >
          <span class="day-number" class:today-circle={isToday}>{day.date}</span>
          {#if hasSessions}
            <div class="session-chips">
              {#each sessions.slice(0, 3) as s}
                <span
                  class="session-chip"
                  title={s.name || s.sport_type || (s.rest_day ? 'Rest' : 'Session')}
                >
                  <span
                    class="chip-badge"
                    class:chip-rest={s.rest_day}
                    style={s.rest_day ? '' : `background: ${sportColors[s.sport_type ?? 'other'] ?? sportColors.other}`}
                  >{s.rest_day ? 'R' : (s.sport_type?.charAt(0).toUpperCase() ?? 'S')}</span>
                  <span class="chip-label">{s.name || (s.rest_day ? 'Rest' : s.sport_type ?? '')}</span>
                </span>
              {/each}
              {#if sessions.length > 3}
                <span class="chip-more">+{sessions.length - 3}</span>
              {/if}
            </div>
          {/if}
        </button>
      {/each}
    </div>
    {:else}
    <div class="week-grid">
      {#each weekDays as day}
        {@const sessions = sessionsByDate.get(day.dateStr) ?? []}
        {@const hasSessions = sessions.length > 0}
        <button
          class="week-day-cell"
          class:today={day.isToday}
          onclick={() => selectDay(day.dateStr)}
        >
          <div class="week-day-header">
            <span class="week-day-name">{day.date.toLocaleDateString('en-GB', { weekday: 'short' })}</span>
            <span class="week-day-number" class:today-circle={day.isToday}>{day.date.getDate()}</span>
          </div>
          <div class="week-day-body">
            {#if hasSessions}
              {#each sessions as s}
                <div
                  class="week-session-card"
                  class:rest={s.rest_day}
                  style={s.rest_day ? '' : `border-left: 3px solid ${s.block_id && blockColorMap.has(s.block_id) ? blockColorMap.get(s.block_id) : sportColors[s.sport_type ?? 'other'] ?? sportColors.other}`}
                >
                  <div class="week-session-top">
                    {#if s.rest_day}
                      <span class="week-session-sport rest-text">Rest</span>
                    {:else if s.sport_type}
                      <span class="week-session-sport" style="color: {sportColors[s.sport_type] ?? sportColors.other}">{s.sport_type}</span>
                    {/if}
                    {#if s.status === 'completed'}
                      <span class="status-badge completed">Done</span>
                    {:else if s.status === 'skipped'}
                      <span class="status-badge skipped">Skipped</span>
                    {/if}
                  </div>
                  <div class="week-session-name">{s.name || (s.rest_day ? 'Rest Day' : 'Untitled')}</div>
                  {#if !s.rest_day && s.targets && s.targets.length > 0}
                    <div class="week-session-targets">
                      {#each s.targets as target}
                        <span class="target-badge target-{target.type}">{formatTarget({ ...s, targets: [target] })}</span>
                      {/each}
                    </div>
                  {/if}
                  {#if s.activity_id}
                    <button class="week-session-link" onclick={(e) => { e.stopPropagation(); onNavigate?.('activity', s.activity_id!); }}>
                      View Activity
                    </button>
                  {/if}
                </div>
              {/each}
            {:else}
              <div class="week-empty">–</div>
            {/if}
          </div>
        </button>
      {/each}
    </div>
    {/if}

    <div class="legend">
      {#each Object.entries(sportColors) as [sport, color]}
        <span class="legend-item">
          <span class="legend-dot" style="background: {color}"></span>
          {sport}
        </span>
      {/each}
      <span class="legend-item">
        <span class="legend-dot legend-dot-rest"></span>
        rest
      </span>
    </div>
  {/if}
</div>

<Modal open={showDayDetail} title={selectedDate ? formatDateLong(selectedDate) : ''} onClose={() => showDayDetail = false}>
  {#if selectedDaySessions.length === 0}
    <div class="no-sessions">No sessions scheduled for this day.</div>
  {:else}
    <div class="day-sessions">
      {#each selectedDaySessions as s}
        <div class="sd">
          <div class="sd-header">
            <div class="sd-header-left">
              <div class="sd-date">{new Date(s.scheduled_date).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</div>
              <div class="sd-name">{s.name || (s.rest_day ? 'Rest Day' : 'Untitled')}</div>
            </div>
            <div class="sd-badges">
              {#if s.rest_day}
                <span class="sdb sdb-rest">Rest</span>
              {:else if s.sport_type}
                <span class="sdb sdb-sport">{(s.sport_type)}</span>
              {/if}
              {#if s.status === 'completed'}
                <span class="sdb sdb-done">Done</span>
              {:else if s.status === 'skipped'}
                <span class="sdb sdb-skip">Skipped</span>
              {:else}
                <span class="sdb sdb-plan">Planned</span>
              {/if}
            </div>
          </div>

          <div class="sd-body">
            {#if !s.rest_day}
              <div class="sdb-section">
                <div class="sdb-section-title">Targets</div>
                {#if s.targets && s.targets.length > 0}
                  <div class="sdb-pills">
                    {#each s.targets as t}
                      <span class="sdb-pill target-{t.type}">{t.type}{t.value ? ` ${t.value}` : ''}{t.unit ? ` ${t.unit}` : ''}</span>
                    {/each}
                  </div>
                {:else}
                  <span class="sdb-empty">Free session</span>
                {/if}
              </div>

              {#if s.intervals}
                {@const items = s.intervals.split(',').map(i => i.trim()).filter(Boolean)}
                <div class="sdb-section">
                  <div class="sdb-section-title">Intervals ({items.length})</div>
                  <ul class="sdb-interval-list">
                    {#each items as item}
                      <li class="sdb-interval-item">{item}</li>
                    {/each}
                  </ul>
                </div>
              {/if}
            {/if}

            {#if s.description}
              <div class="sdb-section">
                <div class="sdb-section-title">Description</div>
                <p class="sdb-text">{s.description}</p>
              </div>
            {/if}

            {#if s.notes}
              <div class="sdb-section">
                <div class="sdb-section-title">Notes</div>
                <p class="sdb-text">{s.notes}</p>
              </div>
            {/if}
          </div>

          <div class="sd-plan">
            Plan: {plans.find(p => p.id === s.plan_id)?.name ?? '-'}
            {#if s.block_id}
              {#each plans as p}
                {#each p.blocks || [] as b}
                  {#if b.id === s.block_id}
                    <span class="sd-block" style="color: {blockColorMap.get(s.block_id)}">· {b.name}</span>
                  {/if}
                {/each}
              {/each}
            {/if}
          </div>
          {#if s.activity_id}
            <button class="sd-activity-link" onclick={() => { showDayDetail = false; onNavigate?.('activity', s.activity_id!); }}>
              View Activity →
            </button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</Modal>

<style>
  .page {
    max-width: 1200px;
  }
  .calendar-header {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    position: relative;
  }
  .month-nav {
    display: flex;
    align-items: center;
    gap: 4px;
    background: var(--bg);
    border-radius: 10px;
    padding: 4px;
    position: relative;
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
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
  }
  .btn-outline {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .btn-outline:hover { background: var(--hover); }

  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    background: var(--border);
    gap: 1px;
  }
  .day-header {
    padding: 10px 4px;
    text-align: center;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg);
  }
  .day-cell {
    background: var(--surface);
    min-height: 90px;
    padding: 6px;
    cursor: pointer;
    border: none;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 4px;
    transition: background 0.1s;
  }
  .day-cell:hover {
    background: var(--hover);
  }
  .day-cell.other-month {
    opacity: 0.4;
  }
  .day-cell.today {
  }
  .day-number {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    line-height: 24px;
    height: 24px;
  }
  .today-circle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--primary);
    color: white;
    font-size: 12px;
    line-height: 1;
    font-weight: 600;
  }
  .session-chips {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: 2px;
  }
  .session-chip {
    display: flex;
    align-items: center;
    gap: 4px;
    background: white;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 4px 2px 2px;
    min-width: 0;
    overflow: hidden;
  }
  .chip-badge {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 8px;
    font-weight: 700;
    color: white;
    flex-shrink: 0;
  }
  .chip-rest {
    background: #d1d5db;
    color: #6b7280;
  }
  .chip-label {
    font-size: 9px;
    font-weight: 500;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .chip-more {
    font-size: 9px;
    color: var(--text-secondary);
    font-weight: 600;
    padding-left: 2px;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 12px;
    padding: 8px 0;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: capitalize;
  }
  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }
  .legend-dot-rest {
    background: #d1d5db;
    border: 1px solid #9ca3af;
  }

  .no-sessions {
    padding: 24px;
    text-align: center;
    color: var(--text-secondary);
    font-size: 14px;
  }
  .day-sessions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 320px;
  }

  .sd { min-width: 380px; max-width: 520px; font-family: var(--font-sans); }

  .sd-header {
    display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
    margin-bottom: 14px; padding-bottom: 14px;
    border-bottom: 0.5px solid var(--border);
  }
  .sd-header-left { display: flex; flex-direction: column; gap: 4px; }
  .sd-date {
    font-size: 12px; font-weight: 500; color: var(--text-secondary);
  }
  .sd-name {
    font-size: 20px; font-weight: 700; color: var(--text);
  }
  .sd-badges { display: flex; gap: 6px; flex-wrap: wrap; }
  .sdb {
    font-size: 10px; font-weight: 600; padding: 3px 10px; border-radius: 6px;
  }
  .sdb-rest { background: #f3f4f6; color: #6b7280; }
  .sdb-sport { background: #3b82f620; color: #3b82f6; text-transform: uppercase; }
  .sdb-done { background: #dcfce7; color: #166534; }
  .sdb-skip { background: #fef3c7; color: #92400e; }
  .sdb-plan { background: #e0f2fe; color: #0369a1; }

  .sd-body { display: flex; flex-direction: column; gap: 10px; }

  .sdb-section {
    border: 0.5px solid var(--border);
    border-radius: 8px; padding: 10px 12px;
    background: var(--bg);
  }
  .sdb-section-title {
    font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
    color: var(--text-secondary); margin-bottom: 6px;
  }
  .sdb-text {
    font-size: 13px; color: var(--text); line-height: 1.5; margin: 0; white-space: pre-wrap;
  }
  .sdb-pills { display: flex; flex-wrap: wrap; gap: 4px; }
  .sdb-pill {
    font-size: 11px; font-weight: 500; padding: 3px 9px; border-radius: 6px;
  }
  .sdb-empty { font-size: 12px; color: var(--text-secondary); font-style: italic; }
  .sdb-interval-list {
    list-style: none; margin: 0; padding: 0;
    display: flex; flex-direction: column; gap: 4px;
  }
  .sdb-interval-item {
    font-size: 13px; color: var(--text); line-height: 1.5;
  }
  .sdb-interval-item::before { content: '•'; margin-right: 6px; color: var(--text-secondary); }

  .sd-plan {
    font-size: 12px; color: var(--text-secondary);
    margin-top: 8px; padding-top: 10px;
    border-top: 0.5px solid var(--border);
    display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
  }
  .sd-block { font-weight: 500; }
  .sd-activity-link {
    margin-top: 8px;
    display: inline-block;
    background: none; border: none;
    font-size: 12px; font-weight: 600;
    color: var(--primary);
    cursor: pointer; padding: 0;
  }
  .sd-activity-link:hover { text-decoration: underline; }

  .status-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
  }
  .status-badge.completed { background: #dcfce7; color: #166534; }
  .status-badge.skipped { background: #fef3c7; color: #92400e; }
  .session-name {
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 6px;
  }
  .session-body { display: flex; flex-direction: column; gap: 10px; margin-bottom: 10px; }
  .sb-section { }
  .sb-section-title {
    font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
    color: var(--text-secondary); margin-bottom: 6px;
  }
  .sb-text {
    font-size: 13px; color: var(--text); line-height: 1.5; margin: 0; white-space: pre-wrap;
  }
  .sb-empty { font-size: 12px; color: var(--text-secondary); font-style: italic; }
  .sb-interval-list {
    list-style: none; margin: 0; padding: 0;
    display: flex; flex-direction: column; gap: 4px;
  }
  .sb-interval-item {
    font-size: 13px; color: var(--text); line-height: 1.5;
  }
  .sb-interval-item::before { content: '•'; margin-right: 5px; color: var(--text-tertiary, #9ca3af); }
  .target-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
    margin-bottom: 4px;
  }
  .target-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 4px;
  }
  .target-distance { background: #3b82f620; color: #3b82f6; }
  .target-duration { background: #6b728020; color: #6b7280; }
  .target-pace { background: #22c55e20; color: #22c55e; }
  .target-hr_zone { background: #ef444420; color: #ef4444; }
  .target-power_zone { background: #3b82f620; color: #3b82f6; }
  .target-free { background: #8b5cf620; color: #8b5cf6; }
  .plan-selector {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .plan-tab {
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text-secondary);
    font-size: 13px;
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
  .weekly-progress {
    margin-bottom: 16px;
  }
  .progress-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .progress-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .progress-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
  }
  .progress-name {
    font-weight: 500;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .progress-values {
    color: var(--text-secondary);
    font-size: 12px;
  }
  .progress-bar-bg {
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .sport-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .view-toggle {
    display: flex;
    gap: 2px;
    background: var(--bg);
    border-radius: 8px;
    padding: 2px;
    margin-right: 12px;
  }
  .view-btn {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }
  .view-btn:hover {
    color: var(--text);
  }
  .view-btn.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  }

  .week-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 8px;
  }
  .week-day-cell {
    background: var(--surface);
    border: 0.5px solid var(--border);
    border-radius: 10px;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.15s;
    text-align: left;
    padding: 0;
  }
  .week-day-cell:hover {
    border-color: var(--primary);
  }
  .week-day-cell.today {
    border-color: var(--primary);
    border-width: 1.5px;
  }
  .week-day-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 10px;
    background: var(--bg);
    border-bottom: 0.5px solid var(--border);
  }
  .week-day-name {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }
  .week-day-number {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
  .week-day-body {
    flex: 1;
    padding: 6px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow-y: auto;
  }
  .week-session-card {
    background: var(--bg);
    border-radius: 6px;
    padding: 8px 10px;
    border-left: 3px solid var(--border);
  }
  .week-session-card.rest {
    border-left: 3px solid #d1d5db;
    opacity: 0.7;
  }
  .week-session-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    margin-bottom: 4px;
  }
  .week-session-sport {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .rest-text {
    color: #6b7280;
  }
  .week-session-name {
    font-size: 12px;
    font-weight: 500;
    color: var(--text);
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .week-session-targets {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    margin-top: 4px;
  }
  .week-session-link {
    display: inline-block;
    margin-top: 4px;
    padding: 0;
    border: none;
    background: none;
    color: var(--primary);
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    font-family: var(--font-sans);
  }
  .week-session-link:hover {
    text-decoration: underline;
  }
  .week-empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--border);
    font-size: 14px;
  }

  @media (max-width: 768px) {
    .page { padding: 16px; }
    .day-cell { min-height: 64px; padding: 4px; }
    .day-number { font-size: 12px; }
    .dot { width: 6px; height: 6px; }
    .day-sessions { min-width: 100%; }
    .calendar-header { flex-direction: column; align-items: flex-start; gap: 12px; }
    .week-grid { grid-template-columns: 1fr; }
    .week-day-cell { min-height: auto; }
    .view-toggle { margin-right: 0; }
  }
</style>
