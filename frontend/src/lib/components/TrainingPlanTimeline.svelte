<script lang="ts">
  import type { TrainingPlan, TrainingBlock, TrainingSession } from '$lib/api/types';
  import Modal from './Modal.svelte';

  let { plan, onSessionClick }: { plan: TrainingPlan; onSessionClick?: (s: TrainingSession) => void } = $props();

  interface WeekInfo {
    date: Date;
    weekNum: number;
    year: number;
    label: string;
    monthLabel: string;
    block: TrainingBlock | null;
    sessions: TrainingSession[];
    isNow: boolean;
  }

  interface MonthGroup {
    label: string;
    weeks: WeekInfo[];
  }

  let selectedWeek = $state<WeekInfo | null>(null);
  let selectedBlock = $state<TrainingBlock | null>(null);
  let selectedSession = $state<TrainingSession | null>(null);

  const blockTypeColor: Record<string, { bg: string; text: string; border: string; label: string }> = {
    base:      { bg: '#E1F5EE', text: '#085041', border: '#5DCAA5', label: 'Base' },
    build:     { bg: '#FAEEDA', text: '#633806', border: '#EF9F27', label: 'Build' },
    benchmark: { bg: '#EEEDFE', text: '#26215C', border: '#7F77DD', label: 'Benchmark' },
    recovery:  { bg: '#EAF3DE', text: '#27500A', border: '#97C459', label: 'Recovery' },
    holiday:   { bg: '#F7F6F3', text: '#999999', border: '#CCCCCC', label: 'Holiday' },
  };

  const shortMonths = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  function isoWeek(d: Date): { weekNum: number; year: number } {
    const copy = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const dayNum = copy.getUTCDay() || 7;
    copy.setUTCDate(copy.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(copy.getUTCFullYear(), 0, 1));
    const weekNum = Math.ceil((((copy.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
    return { weekNum, year: copy.getUTCFullYear() };
  }

  function mondayOfWeek(d: Date): Date {
    const copy = new Date(d);
    const day = copy.getDay();
    const diff = copy.getDate() - day + (day === 0 ? -6 : 1);
    copy.setDate(diff);
    copy.setHours(0, 0, 0, 0);
    return copy;
  }

  function sameWeek(a: Date, b: Date): boolean {
    const wa = isoWeek(a);
    const wb = isoWeek(b);
    return wa.weekNum === wb.weekNum && wa.year === wb.year;
  }

  function localMidnight(iso: string): Date {
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  function sundayOfWeek(monday: Date): Date {
    const copy = new Date(monday);
    copy.setDate(copy.getDate() + 6);
    copy.setHours(23, 59, 59, 999);
    return copy;
  }

  function weekOverlapsBlock(monday: Date, start: string | null, end: string | null): boolean {
    if (!start && !end) return false;
    const sunday = sundayOfWeek(monday);
    if (start) {
      const s = localMidnight(start);
      if (sunday.getTime() < s.getTime()) return false;
    }
    if (end) {
      const e = localMidnight(end);
      e.setHours(23, 59, 59, 999);
      if (monday.getTime() > e.getTime()) return false;
    }
    return true;
  }

  const weeks = $derived.by<{ months: MonthGroup[]; weekMap: Map<string, WeekInfo> }>(() => {
    const blocks = plan.blocks || [];
    const sessions = plan.sessions || [];

    if (blocks.length === 0) return { months: [], weekMap: new Map() };

    let minDate: Date | null = null;
    let maxDate: Date | null = null;

    for (const b of blocks) {
      if (b.start_date) {
        const d = localMidnight(b.start_date);
        if (!minDate || d < minDate) minDate = d;
      }
      if (b.end_date) {
        const d = localMidnight(b.end_date);
        if (!maxDate || d > maxDate) maxDate = d;
      }
    }

    if (!minDate || !maxDate) return { months: [], weekMap: new Map() };

    const start = mondayOfWeek(minDate);
    const end = mondayOfWeek(maxDate);

    const today = new Date();
    const weekMap = new Map<string, WeekInfo>();
    const weeksByMonth = new Map<string, WeekInfo[]>();

    const current = new Date(start);
    while (current <= end) {
      const wi = isoWeek(current);
      const key = `${wi.year}-${wi.weekNum}`;
      const monthLabel = shortMonths[current.getMonth()];

      const block = blocks.find(b =>
        weekOverlapsBlock(current, b.start_date, b.end_date)
      ) || null;

      const weekSessions = sessions.filter(s => {
        const sd = new Date(s.scheduled_date);
        return sameWeek(sd, current);
      });

      const info: WeekInfo = {
        date: new Date(current),
        weekNum: wi.weekNum,
        year: wi.year,
        label: `W${wi.weekNum}`,
        monthLabel,
        block,
        sessions: weekSessions,
        isNow: sameWeek(current, today),
      };

      weekMap.set(key, info);

      if (!weeksByMonth.has(monthLabel)) weeksByMonth.set(monthLabel, []);
      weeksByMonth.get(monthLabel)!.push(info);

      current.setDate(current.getDate() + 7);
    }

    const months: MonthGroup[] = [];
    const monthOrder = shortMonths.filter(m => weeksByMonth.has(m));
    for (const m of monthOrder) {
      months.push({ label: m, weeks: weeksByMonth.get(m)! });
    }

    return { months, weekMap };
  });

  const weekList = $derived(Array.from(weeks.weekMap.values()));

  function blockColor(index: number, total: number): string {
    if (total <= 1) return '#3b82f6';
    const hue = (index / total) * 360;
    return `hsl(${hue}, 55%, 45%)`;
  }

  function getColor(block: TrainingBlock | null): { bg: string; text: string; border: string; label: string } {
    if (!block) return { bg: '#F3F4F6', text: '#9CA3AF', border: '#E5E7EB', label: '' };
    const semantic = blockTypeColor[block.block_type];
    if (semantic) return semantic;
    const total = plan.blocks.length;
    const idx = plan.blocks.findIndex(b => b.id === block.id);
    const color = blockColor(idx, total);
    return { bg: `${color}20`, text: color, border: color, label: '' };
  }

  function selectWeek(w: WeekInfo) {
    if (selectedWeek === w) {
      selectedWeek = null;
      selectedBlock = null;
      return;
    }
    selectedWeek = w;
    selectedBlock = w.block;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  function blockSessionCount(blockId: number): number {
    return plan.sessions.filter(s => s.block_id === blockId).length;
  }
</script>

<div class="timeline">
  {#if weeks.months.length === 0}
    <div class="timeline-empty">
      <p>Blocks need start and end dates to show the timeline. Edit your blocks to add dates.</p>
    </div>
  {:else}
    <div class="calendar">
      {#each weeks.months as month}
        <div class="cal-row">
          <div class="cal-month">{month.label}</div>
          <div class="cal-weeks">
            {#each month.weeks as w}
              {@const color = getColor(w.block)}
              <button
                class="week-box"
                style="background: {color.bg}; color: {color.text}; border-color: {color.border};"
                class:active={selectedWeek === w}
                class:now={w.isNow}
                onclick={() => selectWeek(w)}
                aria-label="Week {w.weekNum}"
              >
                <span class="week-tag">{w.label}</span>
                {#if w.block}
                  <span class="week-sub">{w.block.name}</span>
                {/if}
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>

    <div class="legend">
      {#each plan.blocks as b}
        {@const c = getColor(b)}
        <span class="legend-item">
          <span class="legend-dot" style="background: {c.bg}; border: 0.5px solid {c.border};"></span>
          {b.name}
        </span>
      {/each}
    </div>

    <div class="detail">
      {#if selectedWeek && selectedBlock}
        <div class="detail-top">
          <div>
            <div class="detail-title">{selectedBlock.name}</div>
            <div class="detail-sub">
              Week {selectedWeek.weekNum} ({selectedWeek.date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })})
              {#if selectedWeek.isNow}<span class="now-badge">Now</span>{/if}
            </div>
          </div>
          <div class="type-badge" style="background: {getColor(selectedBlock).bg}; color: {getColor(selectedBlock).text}; border-color: {getColor(selectedBlock).border};">
            {getColor(selectedBlock).label || selectedBlock.block_type}
          </div>
        </div>

        {#if selectedBlock.description}
          <p class="detail-desc">{selectedBlock.description}</p>
        {/if}
        {#if selectedBlock.focus}
          <p class="detail-focus">Focus: {selectedBlock.focus}</p>
        {/if}

        {#if selectedBlock.start_date && selectedBlock.end_date}
          <div class="detail-range">
            {new Date(selectedBlock.start_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            →
            {new Date(selectedBlock.end_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            &middot;
            {blockSessionCount(selectedBlock.id)} session{blockSessionCount(selectedBlock.id) !== 1 ? 's' : ''}
          </div>
        {/if}

        {#if selectedWeek.sessions.length > 0}
          <div class="sessions-grid">
            {#each selectedWeek.sessions as s}
              <div class="session-card" class:rest-day={s.rest_day} onclick={() => selectedSession = s}>
                <div class="session-eyebrow">{formatDate(s.scheduled_date)}</div>
                <div class="session-name">{s.name || (s.rest_day ? 'Rest Day' : 'Untitled')}</div>
                {#if !s.rest_day && s.targets && s.targets.length > 0}
                  <div class="target-pills">
                    {#each s.targets as t}
                      <span class="target-pill target-{t.type}">{t.type}{t.value ? ` ${t.value}` : ''}{t.unit ? ` ${t.unit}` : ''}</span>
                    {/each}
                  </div>
                {/if}
                {#if s.description}
                  <div class="session-desc">{s.description}</div>
                {/if}
                {#if s.sport_type && !s.rest_day}
                  <span class="sport-tag sport-{s.sport_type}">{s.sport_type}</span>
                {/if}
              </div>
            {/each}
          </div>
        {:else}
          <p class="no-sessions">No sessions scheduled for this week.</p>
        {/if}
      {:else if selectedWeek && !selectedBlock}
        <p class="detail-placeholder">This week falls outside any block.</p>
      {:else}
        <p class="detail-placeholder">Click any week to see session details.</p>
      {/if}
    </div>
  {/if}
</div>

<Modal open={selectedSession !== null} onClose={() => selectedSession = null}>
  {#if selectedSession}
    {@const s = selectedSession}
    <div class="session-detail">
      <div class="sd-top">
        <div class="sd-date">{new Date(s.scheduled_date).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</div>
        <div class="sd-badges">
          {#if s.rest_day}
            <span class="sd-badge rest">Rest</span>
          {:else if s.sport_type}
            <span class="sd-badge sport">{(s.sport_type)}</span>
          {/if}
          {#if s.status === 'completed'}
            <span class="sd-badge done">Done</span>
          {:else if s.status === 'skipped'}
            <span class="sd-badge skip">Skipped</span>
          {:else}
            <span class="sd-badge planned">Planned</span>
          {/if}
        </div>
      </div>

      <div class="sd-name">{s.name || (s.rest_day ? 'Rest Day' : 'Untitled')}</div>

      {#if s.description}
        <p class="sd-desc">{s.description}</p>
      {/if}

      {#if !s.rest_day && s.targets && s.targets.length > 0}
        <div class="sd-section">
          <div class="sd-section-label">Targets</div>
          <div class="sd-targets">
            {#each s.targets as t}
              <span class="sd-target target-{t.type}">{t.type}{t.value ? ` ${t.value}` : ''}{t.unit ? ` ${t.unit}` : ''}</span>
            {/each}
          </div>
        </div>
      {/if}

      {#if s.intervals}
        <div class="sd-section">
          <div class="sd-section-label">Intervals</div>
          <p class="sd-text">{s.intervals}</p>
        </div>
      {/if}

      {#if s.notes}
        <div class="sd-section">
          <div class="sd-section-label">Notes</div>
          <p class="sd-text">{s.notes}</p>
        </div>
      {/if}

      <div class="sd-actions">
        <button class="btn btn-primary" onclick={() => { const sess = selectedSession; selectedSession = null; onSessionClick?.(sess!); }}>
          Edit Session
        </button>
      </div>
    </div>
  {/if}
</Modal>

<style>
  .timeline { }

  .timeline-empty {
    background: var(--card-bg, var(--surface));
    border: 0.5px solid var(--border);
    border-radius: 10px;
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
    font-size: 13px;
  }

  .calendar { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
  .cal-row { display: flex; align-items: center; gap: 10px; }
  .cal-month {
    font-size: 13px; font-weight: 600; color: var(--text-secondary);
    width: 34px; text-align: right; flex-shrink: 0;
  }
  .cal-weeks { display: flex; gap: 4px; flex: 1; }

  .week-box {
    flex: 1; height: 60px; border-radius: 8px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 600; cursor: pointer; line-height: 1.3;
    transition: transform .1s, box-shadow .1s;
    border: 0.5px solid transparent; position: relative;
    font-family: inherit; min-width: 0; overflow: hidden;
  }
  .week-box:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
  .week-box.active { outline: 2.5px solid var(--text); outline-offset: 2px; }
  .week-box.now::before {
    content: '▼'; position: absolute; top: -16px; left: 50%; transform: translateX(-50%);
    font-size: 9px; color: var(--text);
  }
  .week-tag { font-size: 11px; font-weight: 700; line-height: 1; }
  .week-sub { font-size: 9px; opacity: .65; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; padding: 0 4px; }

  .legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-secondary); }
  .legend-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }

  .detail {
    background: var(--card-bg, var(--surface));
    border: 0.5px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    min-height: 180px;
  }
  .detail-placeholder, .no-sessions {
    font-size: 13px; color: var(--text-secondary);
    padding: .75rem 0; margin: 0;
  }
  .detail-top {
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 10px; margin-bottom: 10px;
  }
  .detail-title {
    font-size: 17px; font-weight: 700; color: var(--text); margin-bottom: 2px;
  }
  .detail-sub {
    font-size: 12px; color: var(--text-secondary);
    display: flex; align-items: center; gap: 6px;
  }
  .now-badge {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    background: var(--text); color: var(--bg);
    padding: 1px 6px; border-radius: 4px;
  }
  .type-badge {
    font-size: 10px; font-weight: 600; padding: 3px 10px;
    border-radius: 20px; border: 0.5px solid; white-space: nowrap; flex-shrink: 0;
  }
  .detail-desc {
    font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin: 0 0 8px;
  }
  .detail-focus {
    font-size: 12px; color: var(--text-secondary); margin: 0 0 8px;
    font-style: italic;
  }
  .detail-range {
    font-size: 11px; color: var(--text-secondary); margin-bottom: 12px;
  }

  .sessions-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .session-card {
    background: var(--bg); border: 0.5px solid var(--border);
    border-radius: 8px; padding: 10px 12px; cursor: pointer;
  }
  .session-card.rest-day { border-style: dashed; opacity: .7; }
  .session-eyebrow {
    font-size: 10px; font-weight: 600; color: var(--text-secondary);
    letter-spacing: .04em; text-transform: uppercase; margin-bottom: 3px;
  }
  .session-name { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 3px; }
  .session-desc { font-size: 11px; color: var(--text-secondary); line-height: 1.5; margin-top: 3px; }

  .target-pills { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px; }
  .target-pill {
    font-size: 10px; font-weight: 500; padding: 1px 6px; border-radius: 4px;
  }
  .target-distance { background: #3b82f620; color: #3b82f6; }
  .target-duration { background: #6b728020; color: #6b7280; }
  .target-pace { background: #22c55e20; color: #22c55e; }
  .target-hr_zone { background: #ef444420; color: #ef4444; }
  .target-power_zone { background: #3b82f620; color: #3b82f6; }
  .target-free { background: #8b5cf620; color: #8b5cf6; }

  .sport-tag {
    display: inline-block;
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    padding: 1px 6px; border-radius: 4px; margin-top: 4px;
  }
  .sport-run { background: #22c55e20; color: #22c55e; }
  .sport-ride { background: #3b82f620; color: #3b82f6; }
  .sport-swim { background: #06b6d420; color: #06b6d4; }
  .sport-hike { background: #f9731620; color: #f97316; }
  .sport-walk { background: #f59e0b20; color: #f59e0b; }
  .sport-other { background: #8b5cf620; color: #8b5cf6; }

  .session-detail {
    min-width: 380px;
    font-family: var(--font-sans);
  }
  .sd-top {
    display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px;
  }
  .sd-date {
    font-size: 13px; font-weight: 500; color: var(--text-secondary);
  }
  .sd-badges { display: flex; gap: 6px; flex-wrap: wrap; }
  .sd-badge {
    font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 6px;
  }
  .sd-badge.rest { background: #f3f4f6; color: #6b7280; }
  .sd-badge.sport { background: #3b82f620; color: #3b82f6; text-transform: uppercase; }
  .sd-badge.done { background: #dcfce7; color: #166534; }
  .sd-badge.skip { background: #fef3c7; color: #92400e; }
  .sd-badge.planned { background: #e0f2fe; color: #0369a1; }

  .sd-name {
    font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 10px;
  }
  .sd-desc {
    font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin: 0 0 16px;
  }
  .sd-section { margin-bottom: 14px; }
  .sd-section-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
    color: var(--text-secondary); margin-bottom: 4px;
  }
  .sd-text {
    font-size: 13px; color: var(--text); line-height: 1.5; margin: 0; white-space: pre-wrap;
  }
  .sd-targets { display: flex; flex-wrap: wrap; gap: 4px; }
  .sd-target {
    font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 6px;
  }
  .sd-actions {
    display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; padding-top: 14px;
    border-top: 0.5px solid var(--border);
  }

  .btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 16px; border: none; border-radius: 8px;
    font-family: var(--font-sans); font-size: 13px; font-weight: 500;
    cursor: pointer;
  }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { opacity: 0.9; }

  @media (max-width: 540px) {
    .sessions-grid { grid-template-columns: 1fr; }
    .week-box { height: 52px; }
  }
</style>
