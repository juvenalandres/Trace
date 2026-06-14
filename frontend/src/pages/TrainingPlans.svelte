<script lang="ts">
  import { onMount } from 'svelte';
  import { trainingApi } from '$lib/api/types';
  import type { TrainingPlan, TrainingSession, SessionTarget } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  let plans = $state<TrainingPlan[]>([]);
  let loading = $state(true);
  let error = $state('');

  let selectedPlan = $state<TrainingPlan | null>(null);
  let showPlanForm = $state(false);
  let editingPlan = $state<TrainingPlan | null>(null);
  let showDeletePlan = $state(false);
  let deletingPlan = $state<TrainingPlan | null>(null);
  let savingPlan = $state(false);

  let planName = $state('');
  let planDescription = $state('');
  let planStartDate = $state('');
  let planEndDate = $state('');

  let showSessionForm = $state(false);
  let editingSession = $state<TrainingSession | null>(null);
  let showDeleteSession = $state(false);
  let deletingSession = $state<TrainingSession | null>(null);
  let savingSession = $state(false);

  let sessDate = $state('');
  let sessSport = $state('');
  let sessName = $state('');
  let sessDescription = $state('');
  let sessTargets = $state<SessionTarget[]>([]);
  let sessIntervals = $state('');
  let sessNotes = $state('');
  let sessRestDay = $state(false);

  const sportOptions = ['run', 'ride', 'swim', 'hike', 'walk', 'other'];
  const targetTypeOptions = ['distance', 'duration', 'pace', 'hr_zone', 'power_zone', 'free'];
  const targetUnitMap: Record<string, string[]> = {
    distance: ['km', 'mi', 'm'],
    duration: ['min', 'h', 's'],
    pace: ['min/km', 'min/mi'],
    hr_zone: ['zone'],
    power_zone: ['zone'],
    free: [],
  };

  async function load() {
    loading = true;
    error = '';
    try {
      plans = await trainingApi.listPlans();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load plans';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  function openAddPlan() {
    editingPlan = null;
    planName = '';
    planDescription = '';
    planStartDate = '';
    planEndDate = '';
    showPlanForm = true;
  }

  function openEditPlan(p: TrainingPlan) {
    editingPlan = p;
    planName = p.name;
    planDescription = p.description ?? '';
    planStartDate = p.start_date ?? '';
    planEndDate = p.end_date ?? '';
    showPlanForm = true;
  }

  async function savePlan() {
    if (!planName.trim()) return;
    savingPlan = true;
    try {
      const data = {
        name: planName.trim(),
        description: planDescription.trim() || undefined,
        start_date: planStartDate || undefined,
        end_date: planEndDate || undefined,
      };
      if (editingPlan) {
        const updated = await trainingApi.updatePlan(editingPlan.id, data);
        plans = plans.map(p => p.id === updated.id ? updated : p);
        if (selectedPlan?.id === updated.id) selectedPlan = updated;
      } else {
        const created = await trainingApi.createPlan(data);
        plans = [created, ...plans];
      }
      showPlanForm = false;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save plan';
    } finally {
      savingPlan = false;
    }
  }

  async function confirmDeletePlan() {
    if (!deletingPlan) return;
    try {
      await trainingApi.deletePlan(deletingPlan.id);
      plans = plans.filter(p => p.id !== deletingPlan!.id);
      if (selectedPlan?.id === deletingPlan.id) selectedPlan = null;
      showDeletePlan = false;
      deletingPlan = null;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete plan';
    }
  }

  function selectPlan(p: TrainingPlan) {
    selectedPlan = p;
  }

  function backToList() {
    selectedPlan = null;
  }

  function openAddSession() {
    editingSession = null;
    sessDate = new Date().toISOString().split('T')[0];
    sessSport = '';
    sessName = '';
    sessDescription = '';
    sessTargets = [];
    sessIntervals = '';
    sessNotes = '';
    sessRestDay = false;
    showSessionForm = true;
  }

  function openEditSession(s: TrainingSession) {
    editingSession = s;
    sessDate = s.scheduled_date;
    sessSport = s.sport_type ?? '';
    sessName = s.name ?? '';
    sessDescription = s.description ?? '';
    sessTargets = s.targets ? [...s.targets] : [];
    sessIntervals = s.intervals ?? '';
    sessNotes = s.notes ?? '';
    sessRestDay = s.rest_day;
    showSessionForm = true;
  }

  async function saveSession() {
    if (!selectedPlan) return;
    savingSession = true;
    try {
      const data = {
        scheduled_date: sessDate,
        sport_type: sessSport || undefined,
        name: sessName.trim() || undefined,
        description: sessDescription.trim() || undefined,
        targets: sessTargets.length > 0 ? sessTargets : undefined,
        intervals: sessIntervals.trim() || undefined,
        notes: sessNotes.trim() || undefined,
        rest_day: sessRestDay,
      };
      if (editingSession) {
        const updated = await trainingApi.updateSession(editingSession.id, data);
        selectedPlan = { ...selectedPlan, sessions: selectedPlan.sessions.map(s => s.id === updated.id ? updated : s) };
      } else {
        const created = await trainingApi.createSession(selectedPlan.id, data);
        selectedPlan = { ...selectedPlan, sessions: [...selectedPlan.sessions, created] };
      }
      showSessionForm = false;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save session';
    } finally {
      savingSession = false;
    }
  }

  async function confirmDeleteSession() {
    if (!deletingSession || !selectedPlan) return;
    try {
      await trainingApi.deleteSession(deletingSession.id);
      selectedPlan = { ...selectedPlan, sessions: selectedPlan.sessions.filter(s => s.id !== deletingSession!.id) };
      showDeleteSession = false;
      deletingSession = null;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete session';
    }
  }

  function formatDate(iso: string | null): string {
    if (!iso) return '-';
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }

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

  let sortedSessions = $derived(
    selectedPlan ? [...selectedPlan.sessions].sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date)) : []
  );
</script>

<div class="page">
  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if selectedPlan}
    <div class="plan-detail">
      <div class="plan-header">
        <button class="back-btn" onclick={backToList}>
          <Icon name="chevronLeft" size={16} />
          Back
        </button>
        <div class="plan-actions">
          <button class="btn btn-outline" onclick={() => openEditPlan(selectedPlan)}>
            <Icon name="segments" size={16} />
            Edit Plan
          </button>
          <button class="btn btn-danger" onclick={() => { deletingPlan = selectedPlan; showDeletePlan = true; }}>
            <Icon name="logout" size={16} />
            Delete
          </button>
        </div>
      </div>

      <div class="plan-info">
        <h1>{selectedPlan.name}</h1>
        {#if selectedPlan.description}
          <p class="plan-desc">{selectedPlan.description}</p>
        {/if}
        {#if selectedPlan.start_date || selectedPlan.end_date}
          <div class="plan-dates">
            {#if selectedPlan.start_date}
              <span>{formatDate(selectedPlan.start_date)}</span>
            {/if}
            {#if selectedPlan.start_date && selectedPlan.end_date}
              <span class="date-sep">→</span>
            {/if}
            {#if selectedPlan.end_date}
              <span>{formatDate(selectedPlan.end_date)}</span>
            {/if}
          </div>
        {/if}
      </div>

      <div class="sessions-section">
        <div class="sessions-header">
          <h2>Sessions ({sortedSessions.length})</h2>
          <button class="btn btn-primary" onclick={openAddSession}>
            <Icon name="segments" size={16} />
            Add Session
          </button>
        </div>

        {#if sortedSessions.length === 0}
          <EmptyState icon="calendar" message="No sessions yet. Add your first training session." action="Add Session" onAction={openAddSession} />
        {:else}
          <div class="sessions-list">
            {#each sortedSessions as s}
              <div class="session-card" class:rest-day={s.rest_day}>
                <div class="session-top">
                  <div class="session-date">{formatDate(s.scheduled_date)}</div>
                  {#if s.rest_day}
                    <span class="rest-badge">Rest</span>
                  {:else if s.sport_type}
                    <span class="sport-badge sport-{s.sport_type}">{s.sport_type}</span>
                  {/if}
                  {#if s.status === 'completed'}
                    <span class="status-badge completed">Done</span>
                  {:else if s.status === 'skipped'}
                    <span class="status-badge skipped">Skipped</span>
                  {/if}
                </div>
                <div class="session-name">{s.name || (s.rest_day ? 'Rest Day' : 'Untitled')}</div>
                {#if !s.rest_day && s.targets && s.targets.length > 0}
                  <div class="target-badges">
                    {#each s.targets as target}
                      <span class="target-badge target-{target.type}">{formatTarget({ ...s, targets: [target] })}</span>
                    {/each}
                  </div>
                {/if}
                {#if s.notes}
                  <div class="session-notes">{s.notes}</div>
                {/if}
                <div class="session-actions">
                  <button class="icon-btn" onclick={() => openEditSession(s)} title="Edit">
                    <Icon name="segments" size={16} />
                  </button>
                  <button class="icon-btn danger" onclick={() => { deletingSession = s; showDeleteSession = true; }} title="Delete">
                    <Icon name="logout" size={16} />
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="page-header">
      <h1>Training Plans</h1>
      <button class="btn btn-primary" onclick={openAddPlan}>
        <Icon name="segments" size={16} />
        New Plan
      </button>
    </div>

    {#if plans.length === 0}
      <EmptyState icon="plans" message="No training plans yet. Create your first plan to start scheduling sessions." action="New Plan" onAction={openAddPlan} />
    {:else}
      <div class="plans-grid">
        {#each plans as p}
          <button class="plan-card" onclick={() => selectPlan(p)}>
            <div class="plan-card-header">
              <span class="plan-name">{p.name}</span>
              <span class="plan-count">{p.sessions.length} session{p.sessions.length !== 1 ? 's' : ''}</span>
            </div>
            {#if p.description}
              <p class="plan-card-desc">{p.description}</p>
            {/if}
            {#if p.start_date || p.end_date}
              <div class="plan-card-dates">
                {#if p.start_date}
                  <span>{formatDate(p.start_date)}</span>
                {/if}
                {#if p.start_date && p.end_date}
                  <span>→</span>
                {/if}
                {#if p.end_date}
                  <span>{formatDate(p.end_date)}</span>
                {/if}
              </div>
            {/if}
          </button>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<Modal open={showPlanForm} title={editingPlan ? 'Edit Plan' : 'New Plan'} onClose={() => showPlanForm = false}>
  <div class="form">
    <div class="field">
      <label for="plan-name">Name</label>
      <input id="plan-name" type="text" bind:value={planName} placeholder="e.g. Marathon Prep Week 1" />
    </div>
    <div class="field">
      <label for="plan-desc">Description</label>
      <textarea id="plan-desc" bind:value={planDescription} rows="3" placeholder="Optional description..."></textarea>
    </div>
    <div class="field-row">
      <div class="field">
        <label for="plan-start">Start Date</label>
        <input id="plan-start" type="date" bind:value={planStartDate} />
      </div>
      <div class="field">
        <label for="plan-end">End Date</label>
        <input id="plan-end" type="date" bind:value={planEndDate} />
      </div>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showPlanForm = false}>Cancel</button>
      <button class="btn btn-primary" onclick={savePlan} disabled={savingPlan || !planName.trim()}>
        {savingPlan ? 'Saving...' : 'Save'}
      </button>
    </div>
  </div>
</Modal>

<Modal open={showDeletePlan} title="Delete Plan" onClose={() => showDeletePlan = false}>
  <div class="delete-confirm">
    <p>Are you sure you want to delete <strong>{deletingPlan?.name}</strong>?</p>
    <p class="warning">This will also delete all sessions in this plan.</p>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showDeletePlan = false}>Cancel</button>
      <button class="btn btn-danger" onclick={confirmDeletePlan}>Delete</button>
    </div>
  </div>
</Modal>

<Modal open={showSessionForm} title={editingSession ? 'Edit Session' : 'Add Session'} onClose={() => showSessionForm = false}>
  <div class="form">
    <div class="field-row">
      <div class="field">
        <label for="sess-date">Date</label>
        <input id="sess-date" type="date" bind:value={sessDate} />
      </div>
      <div class="field">
        <label for="sess-sport">Sport</label>
        <select id="sess-sport" bind:value={sessSport}>
          <option value="">-</option>
          {#each sportOptions as sport}
            <option value={sport}>{sport}</option>
          {/each}
        </select>
      </div>
    </div>
    <div class="field">
      <label for="sess-name">Name</label>
      <input id="sess-name" type="text" bind:value={sessName} placeholder="e.g. Long Run, Recovery Ride" />
    </div>
    <div class="field">
      <label class="checkbox-label">
        <input type="checkbox" bind:checked={sessRestDay} />
        Rest day
      </label>
    </div>
    {#if !sessRestDay}
      <div class="field">
        <label>Targets</label>
        <div class="targets-list">
          {#each sessTargets as target, i}
            <div class="target-row">
              <select bind:value={target.type} class="target-type-select">
                <option value="">-</option>
                {#each targetTypeOptions as t}
                  <option value={t}>{t}</option>
                {/each}
              </select>
              {#if target.type && targetUnitMap[target.type]?.length > 0}
                <input type="number" bind:value={target.value} step="any" placeholder="Value" class="target-value-input" />
                <select bind:value={target.unit} class="target-unit-select">
                  <option value="">-</option>
                  {#each targetUnitMap[target.type] as u}
                    <option value={u}>{u}</option>
                  {/each}
                </select>
              {/if}
              <button class="icon-btn danger" onclick={() => { sessTargets = sessTargets.filter((_, idx) => idx !== i); }} title="Remove target">
                <Icon name="logout" size={14} />
              </button>
            </div>
          {/each}
        </div>
        <button class="btn btn-outline btn-sm" onclick={() => { sessTargets = [...sessTargets, { type: '', value: null, unit: null }]; }}>
          <Icon name="segments" size={14} />
          Add Target
        </button>
      </div>
      <div class="field">
        <label for="sess-intervals">Intervals (JSON)</label>
        <textarea id="sess-intervals" bind:value={sessIntervals} rows="3" placeholder="e.g. warmup 10min, work 4x4min @250W"></textarea>
      </div>
    {/if}
    <div class="field">
      <label for="sess-desc">Description</label>
      <textarea id="sess-desc" bind:value={sessDescription} rows="2" placeholder="Optional notes..."></textarea>
    </div>
    <div class="field">
      <label for="sess-notes">Notes</label>
      <textarea id="sess-notes" bind:value={sessNotes} rows="2" placeholder="Additional notes..."></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showSessionForm = false}>Cancel</button>
      <button class="btn btn-primary" onclick={saveSession} disabled={savingSession || !sessDate}>
        {savingSession ? 'Saving...' : 'Save'}
      </button>
    </div>
  </div>
</Modal>

<Modal open={showDeleteSession} title="Delete Session" onClose={() => showDeleteSession = false}>
  <div class="delete-confirm">
    <p>Are you sure you want to delete this session?</p>
    <p class="warning">This action cannot be undone.</p>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showDeleteSession = false}>Cancel</button>
      <button class="btn btn-danger" onclick={confirmDeleteSession}>Delete</button>
    </div>
  </div>
</Modal>

<style>
  .page {
    max-width: 1200px;
  }
  .page-header {
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
    margin: 0;
  }

  .plans-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
  }
  .plan-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: var(--card-padding, 16px);
    cursor: pointer;
    text-align: left;
    width: 100%;
    transition: border-color 0.15s;
  }
  .plan-card:hover {
    border-color: var(--primary);
  }
  .plan-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .plan-name {
    font-size: var(--font-size-md, 14px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .plan-count {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    background: var(--bg);
    padding: 2px 8px;
    border-radius: 10px;
  }
  .plan-card-desc {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin: 0 0 8px;
    line-height: 1.4;
  }
  .plan-card-dates {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    display: flex;
    gap: 4px;
  }

  .plan-detail { }
  .plan-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: none;
    background: none;
    color: var(--primary);
    cursor: pointer;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    padding: 6px 10px;
    border-radius: 6px;
  }
  .back-btn:hover { background: var(--primary-light); }
  .plan-actions {
    display: flex;
    gap: 8px;
  }
  .plan-info { margin-bottom: 24px; }
  .plan-info h1 { margin-bottom: 4px; }
  .plan-desc {
    color: var(--text-secondary);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    margin: 0 0 8px;
  }
  .plan-dates {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .date-sep { color: var(--border); }

  .sessions-section { }
  .sessions-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .sessions-list {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }
  .session-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: 14px 16px;
    position: relative;
  }
  .session-card.rest-day {
    border-style: dashed;
    opacity: 0.7;
  }
  .session-top {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .session-date {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .sport-badge {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    padding: 2px 8px;
    border-radius: 10px;
    background: var(--bg);
    color: var(--text-secondary);
  }
  .sport-run { background: #22c55e20; color: #22c55e; }
  .sport-ride { background: #3b82f620; color: #3b82f6; }
  .sport-swim { background: #06b6d420; color: #06b6d4; }
  .sport-hike { background: #f9731620; color: #f97316; }
  .sport-walk { background: #f59e0b20; color: #f59e0b; }
  .sport-other { background: #8b5cf620; color: #8b5cf6; }
  .target-badge {
    display: inline-block;
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
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
  .targets-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;
  }
  .target-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .target-type-select,
  .target-value-input,
  .target-unit-select {
    flex: 1;
  }
  .btn-sm {
    font-size: var(--font-size-sm, 12px);
    padding: 4px 10px;
  }
  .rest-badge {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    padding: 2px 8px;
    border-radius: 10px;
    background: #f3f4f6;
    color: #6b7280;
  }
  .status-badge {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    padding: 2px 8px;
    border-radius: 10px;
  }
  .status-badge.completed { background: #dcfce7; color: #166534; }
  .status-badge.skipped { background: #fef3c7; color: #92400e; }
  .session-name {
    font-size: var(--font-size-md, 14px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
    margin-bottom: 4px;
  }
  .session-notes {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-top: 4px;
  }
  .session-actions {
    position: absolute;
    top: 12px;
    right: 12px;
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
  }
  .session-card:hover .session-actions { opacity: 1; }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: none;
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
  }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-outline {
    background: var(--surface);
    color: var(--text);
    border: 0.5px solid var(--border);
  }
  .btn-outline:hover { background: var(--hover); }
  .btn-danger {
    background: #fee2e2;
    color: #dc2626;
    border: 0.5px solid #fecaca;
  }
  .btn-danger:hover { background: #fecaca; }
  .icon-btn {
    width: 32px;
    height: 32px;
    border: none;
    background: none;
    color: var(--text-secondary);
    cursor: pointer;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .icon-btn:hover { background: var(--hover); color: var(--text); }
  .icon-btn.danger:hover { background: #fee2e2; color: #dc2626; }

  .form {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-width: 360px;
    font-family: var(--font-sans);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field-row {
    display: flex;
    gap: 12px;
  }
  .field-row .field { flex: 1; }
  label {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
  }
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    cursor: pointer;
  }
  .checkbox-label input[type="checkbox"] {
    width: 16px;
    height: 16px;
    cursor: pointer;
  }
  input, select, textarea {
    padding: 10px 12px;
    border: 0.5px solid var(--border);
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    background: var(--bg);
    color: var(--text);
  }
  input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: var(--primary);
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 4px;
  }
  .delete-confirm p {
    margin: 0 0 8px;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text);
  }
  .delete-confirm .warning {
    color: #dc2626;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    margin-bottom: 16px;
  }

  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: var(--font-size-2xl, 22px); }
    .plans-grid { grid-template-columns: 1fr; }
    .form { min-width: 100%; }
    .field-row { flex-direction: column; }
    .plan-header { flex-wrap: wrap; gap: 8px; }
    .sessions-header { flex-wrap: wrap; gap: 8px; }
    .sessions-list { grid-template-columns: 1fr; }
    .session-actions { opacity: 1; }
  }
</style>
