<script lang="ts">
  import { onMount } from 'svelte';
  import { gearApi } from '$lib/api/types';
  import type { Gear, GearStats } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  let gear = $state<Gear[]>([]);
  let stats = $state<GearStats[]>([]);
  let loading = $state(true);
  let error = $state('');

  let showForm = $state(false);
  let editing = $state<Gear | null>(null);
  let showDelete = $state(false);
  let deleting = $state<Gear | null>(null);
  let saving = $state(false);
  let showRetired = $state(false);

  let formName = $state('');
  let formType = $state('bike');
  let formBrand = $state('');
  let formModel = $state('');
  let formNotes = $state('');
  let formMaintKm = $state('');

  const typeIcons: Record<string, string> = {
    bike: 'activity',
    shoes: 'segments',
    other: 'gear',
  };

  const typeLabels: Record<string, string> = {
    bike: 'Bike',
    shoes: 'Shoes',
    other: 'Other',
  };

  async function load() {
    try {
      const [gearData, statsData] = await Promise.all([
        gearApi.list(),
        gearApi.stats().catch(() => []),
      ]);
      gear = gearData;
      stats = statsData;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load gear';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  let activeGear = $derived(gear.filter(g => !g.retired));
  let retiredGear = $derived(gear.filter(g => g.retired));

  function openAdd() {
    editing = null;
    formName = '';
    formType = 'bike';
    formBrand = '';
    formModel = '';
    formNotes = '';
    formMaintKm = '';
    showForm = true;
  }

  function openEdit(g: Gear) {
    editing = g;
    formName = g.name;
    formType = g.gear_type;
    formBrand = g.brand ?? '';
    formModel = g.model ?? '';
    formNotes = g.notes ?? '';
    formMaintKm = g.maintenance_interval_km?.toString() ?? '';
    showForm = true;
  }

  async function saveForm() {
    if (!formName.trim()) return;
    saving = true;
    try {
      const data = {
        name: formName.trim(),
        gear_type: formType,
        brand: formBrand.trim() || undefined,
        model: formModel.trim() || undefined,
        notes: formNotes.trim() || undefined,
        maintenance_interval_km: formMaintKm ? parseFloat(formMaintKm) : undefined,
      };

      if (editing) {
        await gearApi.update(editing.id, data);
      } else {
        await gearApi.create(data);
      }
      showForm = false;
      await load();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save';
    } finally {
      saving = false;
    }
  }

  async function toggleRetire(g: Gear) {
    try {
      await gearApi.update(g.id, { retired: !g.retired });
      await load();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to update gear';
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    try {
      await gearApi.delete(deleting.id);
      showDelete = false;
      deleting = null;
      await load();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete gear';
    }
  }

  function formatDist(m: number): string {
    if (m >= 1000) return `${(m / 1000).toFixed(0)}km`;
    return `${Math.round(m)}m`;
  }

  function formatDuration(s: number): string {
    if (s < 60) return `${Math.round(s)}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    const h = Math.floor(s / 3600);
    const d = Math.floor(h / 24);
    const remH = h % 24;
    const remM = Math.floor((s % 3600) / 60);
    if (d > 0) return `${d}d ${remH}h ${remM}m`;
    return `${h}h ${remM}m`;
  }

  function formatSpeed(ms: number): string {
    return `${(ms * 3.6).toFixed(1)}km/h`;
  }

  function getMaintenanceProgress(s: GearStats): { percent: number; sinceKm: number; intervalKm: number; color: string } | null {
    if (!s.maintenance_interval_km || !s.gear_id) return null;
    const intervalM = s.maintenance_interval_km * 1000;
    const sinceM = s.total_distance_m - (s.last_service_distance_m ?? 0);
    const percent = Math.min(100, (sinceM / intervalM) * 100);
    let color = '#22c55e';
    if (percent >= 90) color = '#ef4444';
    else if (percent >= 75) color = '#f59e0b';
    return { percent, sinceKm: sinceM / 1000, intervalKm: s.maintenance_interval_km, color };
  }

  async function markServiced(gearId: number) {
    try {
      await gearApi.markServiced(gearId);
      await load();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to mark as serviced';
    }
  }

  let activeStats = $derived(stats.filter(s => !s.retired));
  let retiredStats = $derived(stats.filter(s => s.retired));
</script>

<div class="page">
  <div class="page-header">
    <h1>Gear</h1>
    <button class="btn btn-primary" onclick={openAdd}>
      <Icon name="segments" size={16} />
      Add Gear
    </button>
  </div>

  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else}
    {#if activeStats.length > 0}
      <div class="stats-table-card">
        <div class="stats-table-wrap">
          <div class="gear-table">
            <div class="table-header">
              <span class="col-gear">Gear</span>
              <span class="col-num">Workouts</span>
              <span class="col-num">Total Dist</span>
              <span class="col-num">Total Elev</span>
              <span class="col-num">Total Time</span>
              <span class="col-num">Avg Speed</span>
              <span class="col-num">Total Cal</span>
            </div>
            {#each activeStats as s}
              <div class="table-row">
                <span class="col-gear">
                  <span class="stat-gear-name">{s.gear_name}</span>
                </span>
                <span class="col-num">{s.workout_count}</span>
                <span class="col-num">{formatDist(s.total_distance_m)}</span>
                <span class="col-num">{formatDist(s.total_elevation_m)}</span>
                <span class="col-num">{formatDuration(s.total_moving_time_s)}</span>
                <span class="col-num">{formatSpeed(s.avg_speed)}</span>
                <span class="col-num">{s.total_calories.toLocaleString()} kcal</span>
              </div>
            {/each}
          </div>
        </div>

        {#if retiredStats.length > 0}
          <button class="retired-stats-toggle" onclick={() => showRetired = !showRetired}>
            <Icon name={showRetired ? 'chevronDown' : 'chevronRight'} size={14} />
            Retired gear
          </button>
          {#if showRetired}
            <div class="stats-table-wrap">
              <div class="gear-table retired-table">
                {#each retiredStats as s}
                  <div class="table-row">
                    <span class="col-gear">
                      <span class="stat-gear-name">{s.gear_name}</span>
                    </span>
                    <span class="col-num">{s.workout_count}</span>
                    <span class="col-num">{formatDist(s.total_distance_m)}</span>
                    <span class="col-num">{formatDist(s.total_elevation_m)}</span>
                    <span class="col-num">{formatDuration(s.total_moving_time_s)}</span>
                    <span class="col-num">{formatSpeed(s.avg_speed)}</span>
                    <span class="col-num">{s.total_calories.toLocaleString()} kcal</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/if}
      </div>
    {/if}

    {#if activeGear.length === 0 && retiredGear.length === 0 && stats.length === 0}
      <EmptyState icon="gear" message="No gear yet. Add your bikes, shoes, or other equipment." action="Add Gear" onAction={openAdd} />
    {/if}

    {#if activeGear.length > 0}
      <div class="gear-grid">
        {#each activeGear as g}
          <div class="gear-card">
            <div class="gear-header">
              <div class="gear-icon">
                <Icon name={typeIcons[g.gear_type] ?? 'gear'} size={20} />
              </div>
              <div class="gear-info">
                <span class="gear-name">{g.name}</span>
                <span class="gear-type">{typeLabels[g.gear_type] ?? g.gear_type}</span>
              </div>
              <div class="gear-actions">
                <button class="icon-btn" onclick={() => openEdit(g)} title="Edit">
                  <Icon name="segments" size={16} />
                </button>
                <button class="icon-btn" onclick={() => toggleRetire(g)} title="Retire">
                  <Icon name="logout" size={16} />
                </button>
                <button class="icon-btn danger" onclick={() => { deleting = g; showDelete = true; }} title="Delete">
                  <Icon name="logout" size={16} />
                </button>
              </div>
            </div>
            {#if g.brand || g.model}
              <div class="gear-detail">
                {#if g.brand}<span>{g.brand}</span>{/if}
                {#if g.model}<span>{g.model}</span>{/if}
              </div>
            {/if}
            {#if g.notes}
              <div class="gear-notes">{g.notes}</div>
            {/if}
            {#if g.maintenance_interval_km && activeStats.find(s => s.gear_id === g.id)}
              {@const gStats = activeStats.find(s => s.gear_id === g.id)!}
              {@const maint = getMaintenanceProgress(gStats)}
              {#if maint}
                <div class="maint-section">
                  <div class="maint-header">
                    <span class="maint-label">Maintenance</span>
                    <span class="maint-value">{maint.sinceKm.toFixed(0)} / {maint.intervalKm} km</span>
                  </div>
                  <div class="maint-bar-bg">
                    <div class="maint-bar-fill" style="width: {maint.percent}%; background: {maint.color}"></div>
                  </div>
                  <button class="service-btn" onclick={() => markServiced(g.id)}>
                    <Icon name="segments" size={14} />
                    Mark as serviced
                  </button>
                </div>
              {/if}
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    {#if retiredGear.length > 0}
      <button class="retired-toggle" onclick={() => showRetired = !showRetired}>
        <Icon name={showRetired ? 'chevronDown' : 'chevronRight'} size={16} />
        Retired ({retiredGear.length})
      </button>

      {#if showRetired}
        <div class="gear-grid retired">
          {#each retiredGear as g}
            <div class="gear-card retired">
              <div class="gear-header">
                <div class="gear-icon retired-icon">
                  <Icon name={typeIcons[g.gear_type] ?? 'gear'} size={20} />
                </div>
                <div class="gear-info">
                  <span class="gear-name">{g.name}</span>
                  <span class="gear-type">Retired</span>
                </div>
                <div class="gear-actions">
                  <button class="icon-btn" onclick={() => toggleRetire(g)} title="Reactivate">
                    <Icon name="segments" size={16} />
                  </button>
                  <button class="icon-btn danger" onclick={() => { deleting = g; showDelete = true; }} title="Delete">
                    <Icon name="logout" size={16} />
                  </button>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  {/if}
</div>

<Modal open={showForm} title={editing ? 'Edit Gear' : 'Add Gear'} onClose={() => showForm = false}>
  <div class="form">
    <div class="field">
      <label for="gear-name">Name</label>
      <input id="gear-name" type="text" bind:value={formName} placeholder="My Road Bike" />
    </div>
    <div class="field">
      <label for="gear-type">Type</label>
      <select id="gear-type" bind:value={formType}>
        <option value="bike">Bike</option>
        <option value="shoes">Shoes</option>
        <option value="other">Other</option>
      </select>
    </div>
    <div class="field-row">
      <div class="field">
        <label for="gear-brand">Brand</label>
        <input id="gear-brand" type="text" bind:value={formBrand} placeholder="Specialized" />
      </div>
      <div class="field">
        <label for="gear-model">Model</label>
        <input id="gear-model" type="text" bind:value={formModel} placeholder="Tarmac SL7" />
      </div>
    </div>
    <div class="field">
      <label for="gear-maint">Maintenance interval (km)</label>
      <input id="gear-maint" type="number" bind:value={formMaintKm} placeholder="5000" step="100" />
    </div>
    <div class="field">
      <label for="gear-notes">Notes</label>
      <textarea id="gear-notes" bind:value={formNotes} rows="3" placeholder="Optional notes..."></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showForm = false}>Cancel</button>
      <button class="btn btn-primary" onclick={saveForm} disabled={saving || !formName.trim()}>
        {saving ? 'Saving...' : 'Save'}
      </button>
    </div>
  </div>
</Modal>

<Modal open={showDelete} title="Delete Gear" onClose={() => showDelete = false}>
  <div class="delete-confirm">
    <p>Are you sure you want to delete <strong>{deleting?.name}</strong>?</p>
    <p class="warning">This action cannot be undone.</p>
    <div class="form-actions">
      <button class="btn btn-outline" onclick={() => showDelete = false}>Cancel</button>
      <button class="btn btn-danger" onclick={confirmDelete}>Delete</button>
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
  .gear-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }
  .stats-table-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    margin-bottom: 24px;
  }
  .stats-table-wrap {
    overflow-x: auto;
    padding: var(--card-padding, 16px);
  }
  .gear-table {
    width: 100%;
  }
  .table-header {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr 1fr;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 0.5px solid var(--border);
  }
  .table-header span {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }
  .table-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr 1fr;
    gap: 8px;
    padding: 12px 0;
    border-bottom: 0.5px solid var(--border);
    align-items: center;
  }
  .table-row:last-of-type {
    border-bottom: none;
  }
  .retired-table {
    opacity: 0.6;
  }
  .col-gear {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .col-num {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text);
    text-align: right;
    white-space: nowrap;
  }
  .stat-gear-name {
    font-weight: var(--font-weight-medium, 500);
  }
  .retired-stats-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    border: none;
    background: none;
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
    border-top: 0.5px solid var(--border);
    width: 100%;
  }
  .retired-stats-toggle:hover {
    color: var(--text);
    background: var(--hover);
  }
  .gear-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: var(--card-padding, 16px);
  }
  .gear-card.retired {
    opacity: 0.7;
  }
  .gear-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .gear-icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: color-mix(in srgb, var(--primary) 10%, transparent);
    color: var(--primary);
    flex-shrink: 0;
  }
  .retired-icon {
    background: var(--bg);
    color: var(--text-secondary);
  }
  .gear-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .gear-name {
    font-size: var(--font-size-md, 14px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .gear-type {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .gear-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }
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
  .icon-btn:hover {
    background: var(--hover);
    color: var(--text);
  }
  .icon-btn.danger:hover {
    background: #fee2e2;
    color: #dc2626;
  }
  .gear-detail {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
  }
  .gear-notes {
    margin-top: 8px;
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    line-height: 1.4;
  }
  .maint-section {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 0.5px solid var(--border);
  }
  .maint-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .maint-label {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--text-secondary);
  }
  .maint-value {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
  }
  .maint-bar-bg {
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 8px;
  }
  .maint-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .service-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
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
  .service-btn:hover {
    background: var(--hover);
    color: var(--text);
    border-color: var(--primary);
  }
  .retired-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 0;
    border: none;
    background: none;
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    cursor: pointer;
    margin-bottom: 12px;
  }
  .retired-toggle:hover {
    color: var(--text);
  }
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
  .btn-primary {
    background: var(--primary);
    color: white;
  }
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
  .field-row .field {
    flex: 1;
  }
  label {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text-secondary);
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
    .gear-grid { grid-template-columns: 1fr; }
    .stats-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .form { min-width: 100%; }
    .field-row { flex-direction: column; }
  }
</style>
