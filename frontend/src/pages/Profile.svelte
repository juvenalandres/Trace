<script lang="ts">
  import { onMount } from 'svelte';
  import { userApi, zonesApi } from '$lib/api/types';
  import type { User, UserZone } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';

  interface Props {
    user: User | null;
    onLogout?: () => void;
    onUserUpdated?: (user: User) => void;
  }

  let { user, onLogout, onUserUpdated }: Props = $props();

  let name = $state(user?.name ?? '');
  let preferredUnits = $state(user?.preferred_units ?? 'metric');
  let weightKg = $state(user?.weight_kg?.toString() ?? '');
  let ftpWatts = $state(user?.ftp_watts?.toString() ?? '');
  let maxHr = $state(user?.max_hr?.toString() ?? '');
  let restingHr = $state(user?.resting_hr?.toString() ?? '');
  let saving = $state(false);
  let saved = $state(false);
  let error = $state('');

  let hrZone = $state<UserZone | null>(null);
  let powerZone = $state<UserZone | null>(null);
  let hrValues = $state<number[]>(new Array(10).fill(0));
  let powerValues = $state<number[]>(new Array(10).fill(0));
  let zonesLoading = $state(true);
  let hrSaving = $state(false);
  let powerSaving = $state(false);
  let hrSaved = $state(false);
  let powerSaved = $state(false);
  let hrExpanded = $state(false);
  let powerExpanded = $state(false);

  let users = $state<User[]>([]);
  let usersLoading = $state(false);
  let usersError = $state('');

  function zoneToValues(zone: UserZone | null): number[] {
    if (!zone) return new Array(10).fill(0);
    return [
      zone.zone_1_min ?? 0, zone.zone_1_max ?? 0,
      zone.zone_2_min ?? 0, zone.zone_2_max ?? 0,
      zone.zone_3_min ?? 0, zone.zone_3_max ?? 0,
      zone.zone_4_min ?? 0, zone.zone_4_max ?? 0,
      zone.zone_5_min ?? 0, zone.zone_5_max ?? 0,
    ];
  }

  async function loadZones() {
    try {
      const zones = await zonesApi.list();
      hrZone = zones.find(z => z.zone_type === 'hr') ?? null;
      powerZone = zones.find(z => z.zone_type === 'power') ?? null;
      hrValues = zoneToValues(hrZone);
      powerValues = zoneToValues(powerZone);
    } catch {
      // ignore
    } finally {
      zonesLoading = false;
    }
  }

  async function loadUsers() {
    if (!user?.is_admin) return;
    usersLoading = true;
    try {
      users = await userApi.list();
    } catch (e: unknown) {
      usersError = e instanceof Error ? e.message : 'Failed to load users';
    } finally {
      usersLoading = false;
    }
  }

  async function toggleAdmin(targetUser: User) {
    try {
      await userApi.setAdmin(targetUser.id, !targetUser.is_admin);
      targetUser.is_admin = !targetUser.is_admin;
      users = [...users];
    } catch (e: unknown) {
      usersError = e instanceof Error ? e.message : 'Failed to update admin status';
    }
  }

  onMount(() => {
    loadZones();
    loadUsers();
  });

  async function save() {
    saving = true;
    error = '';
    saved = false;

    try {
      const data: Record<string, unknown> = {
        name: name || undefined,
        preferred_units: preferredUnits,
        weight_kg: weightKg ? parseFloat(weightKg) : undefined,
        ftp_watts: ftpWatts ? parseInt(ftpWatts) : undefined,
        max_hr: maxHr ? parseInt(maxHr) : undefined,
        resting_hr: restingHr ? parseInt(restingHr) : undefined,
      };
      await userApi.update(data);
      saved = true;
      onUserUpdated?.(await userApi.me());
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save';
    } finally {
      saving = false;
    }
  }

  function valuesToPayload(values: number[]) {
    return {
      zone_1_min: values[0] ?? undefined,
      zone_1_max: values[1] || undefined,
      zone_2_min: values[2] || undefined,
      zone_2_max: values[3] || undefined,
      zone_3_min: values[4] || undefined,
      zone_3_max: values[5] || undefined,
      zone_4_min: values[6] || undefined,
      zone_4_max: values[7] || undefined,
      zone_5_min: values[8] || undefined,
      zone_5_max: values[9] ?? undefined,
    };
  }

  async function saveHrZones() {
    hrSaving = true;
    hrSaved = false;
    try {
      if (hrZone) {
        await zonesApi.update(hrZone.id, valuesToPayload(hrValues));
      } else {
        await zonesApi.create({ zone_type: 'hr', ...valuesToPayload(hrValues) });
      }
      hrSaved = true;
      await loadZones();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save HR zones';
    } finally {
      hrSaving = false;
    }
  }

  async function savePowerZones() {
    powerSaving = true;
    powerSaved = false;
    try {
      if (powerZone) {
        await zonesApi.update(powerZone.id, valuesToPayload(powerValues));
      } else {
        await zonesApi.create({ zone_type: 'power', ...valuesToPayload(powerValues) });
      }
      powerSaved = true;
      await loadZones();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save power zones';
    } finally {
      powerSaving = false;
    }
  }
</script>

<div class="page">
  <h1>Profile</h1>

  <div class="card">
    <div class="card-header">
      <Icon name="activity" size={20} />
      <span>Account</span>
    </div>
    <div class="card-body">
      <div class="field">
        <label for="email">Email</label>
        <input id="email" type="email" value={user?.email ?? ''} disabled />
      </div>
      <div class="field">
        <label for="name">Name</label>
        <input id="name" type="text" bind:value={name} placeholder="Your name" />
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <Icon name="speed" size={20} />
      <span>Physiology</span>
    </div>
    <div class="card-body">
      <div class="field-row">
        <div class="field">
          <label for="units">Units</label>
          <select id="units" bind:value={preferredUnits}>
            <option value="metric">Metric (km, kg)</option>
            <option value="imperial">Imperial (mi, lbs)</option>
          </select>
        </div>
        <div class="field">
          <label for="weight">Weight (kg)</label>
          <input id="weight" type="number" bind:value={weightKg} placeholder="70" step="0.1" />
        </div>
      </div>
      <div class="field-row">
        <div class="field">
          <label for="ftp">FTP (watts)</label>
          <input id="ftp" type="number" bind:value={ftpWatts} placeholder="250" />
        </div>
        <div class="field">
          <label for="maxhr">Max HR (bpm)</label>
          <input id="maxhr" type="number" bind:value={maxHr} placeholder="190" />
        </div>
        <div class="field">
          <label for="resthr">Resting HR (bpm)</label>
          <input id="resthr" type="number" bind:value={restingHr} placeholder="60" />
        </div>
      </div>
    </div>
  </div>

  {#if !zonesLoading}
    <div class="card">
      <button class="card-header card-header-toggle" class:expanded={hrExpanded} onclick={() => hrExpanded = !hrExpanded}>
        <Icon name="heart" size={20} />
        <span>Heart Rate Zones (bpm)</span>
        {#if hrSaved}
          <span class="zone-saved">Saved!</span>
        {/if}
        <Icon name="chevronDown" size={16} class="chevron-toggle {hrExpanded ? 'chevron-open' : ''}" />
      </button>
      {#if hrExpanded}
      <div class="card-body">
        <div class="zones-grid">
          <div class="zones-header-row">
            <span class="zone-label">Zone</span>
            <span class="zone-col">Min</span>
            <span class="zone-col">Max</span>
          </div>
          <div class="zone-row">
            <span class="zone-label">Z1</span>
            <span class="zone-placeholder">—</span>
            <input class="zone-input" type="number" bind:value={hrValues[1]} placeholder="—" />
          </div>
          {#each [1, 2, 3] as i}
            <div class="zone-row">
              <span class="zone-label">Z{i + 1}</span>
              <input class="zone-input" type="number" bind:value={hrValues[i * 2]} placeholder="—" />
              <input class="zone-input" type="number" bind:value={hrValues[i * 2 + 1]} placeholder="—" />
            </div>
          {/each}
          <div class="zone-row">
            <span class="zone-label">Z5</span>
            <input class="zone-input" type="number" bind:value={hrValues[8]} placeholder="—" />
            <span class="zone-placeholder">—</span>
          </div>
        </div>
        <div class="zone-actions">
          <button class="btn btn-primary" onclick={saveHrZones} disabled={hrSaving}>
            {hrSaving ? 'Saving...' : 'Save HR Zones'}
          </button>
        </div>
      </div>
      {/if}
    </div>

    <div class="card">
      <button class="card-header card-header-toggle" class:expanded={powerExpanded} onclick={() => powerExpanded = !powerExpanded}>
        <Icon name="power" size={20} />
        <span>Power Zones (watts)</span>
        {#if powerSaved}
          <span class="zone-saved">Saved!</span>
        {/if}
        <Icon name="chevronDown" size={16} class="chevron-toggle {powerExpanded ? 'chevron-open' : ''}" />
      </button>
      {#if powerExpanded}
      <div class="card-body">
        <div class="zones-grid">
          <div class="zones-header-row">
            <span class="zone-label">Zone</span>
            <span class="zone-col">Min</span>
            <span class="zone-col">Max</span>
          </div>
          <div class="zone-row">
            <span class="zone-label">Z1</span>
            <span class="zone-placeholder">—</span>
            <input class="zone-input" type="number" bind:value={powerValues[1]} placeholder="—" />
          </div>
          {#each [1, 2, 3] as i}
            <div class="zone-row">
              <span class="zone-label">Z{i + 1}</span>
              <input class="zone-input" type="number" bind:value={powerValues[i * 2]} placeholder="—" />
              <input class="zone-input" type="number" bind:value={powerValues[i * 2 + 1]} placeholder="—" />
            </div>
          {/each}
          <div class="zone-row">
            <span class="zone-label">Z5</span>
            <input class="zone-input" type="number" bind:value={powerValues[8]} placeholder="—" />
            <span class="zone-placeholder">—</span>
          </div>
        </div>
        <div class="zone-actions">
          <button class="btn btn-primary" onclick={savePowerZones} disabled={powerSaving}>
            {powerSaving ? 'Saving...' : 'Save Power Zones'}
          </button>
        </div>
      </div>
      {/if}
    </div>
  {/if}

  {#if error}
    <ErrorBanner message={error} />
  {/if}
  {#if saved}
    <p class="success">Saved!</p>
  {/if}

  <div class="actions">
    <button class="btn btn-primary" onclick={save} disabled={saving}>
      {saving ? 'Saving...' : 'Save Changes'}
    </button>
  </div>

  {#if user?.is_admin}
    <div class="card">
      <div class="card-header">
        <Icon name="activity" size={20} />
        <span>Admin — Users</span>
      </div>
      <div class="card-body">
        {#if usersLoading}
          <LoadingSpinner size="sm" />
        {:else if usersError}
          <ErrorBanner message={usersError} />
        {:else}
          <div class="users-list">
            {#each users as u}
              <div class="user-row">
                <span class="user-email">{u.email}</span>
                <span class="user-name">{u.name || '—'}</span>
                <span class="user-badge" class:admin={u.is_admin}>
                  {u.is_admin ? 'Admin' : 'User'}
                </span>
                {#if u.id !== user.id}
                  <button
                    class="btn btn-sm"
                    class:btn-outline={u.is_admin}
                    class:btn-primary={!u.is_admin}
                    onclick={() => toggleAdmin(u)}
                  >
                    {u.is_admin ? 'Revoke admin' : 'Make admin'}
                  </button>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <div class="card danger-zone">
    <div class="card-header">
      <Icon name="logout" size={20} />
      <span>Session</span>
    </div>
    <div class="card-body">
      <button class="btn btn-danger" onclick={onLogout}>Logout</button>
    </div>
  </div>
</div>

<style>
  .page {
    max-width: 700px;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 24px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 16px;
    overflow: hidden;
  }
  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
  }
  .card-header-toggle {
    cursor: pointer;
    background: none;
    border: none;
    border-bottom: none;
    width: 100%;
    font-family: var(--font-sans);
    transition: background 0.1s;
  }
  .card-header-toggle.expanded {
    border-bottom: 1px solid var(--border);
  }
  .card-header-toggle:hover {
    background: var(--hover);
  }
  .card-header-toggle :global(.chevron-toggle) {
    margin-left: auto;
    transition: transform 0.2s;
    color: var(--text-secondary);
  }
  .card-header-toggle :global(.chevron-open) {
    transform: rotate(180deg);
  }
  .card-body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field-row {
    display: flex;
    gap: 16px;
  }
  .field-row .field {
    flex: 1;
  }
  label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
  }
  input, select {
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
  }
  input:focus, select:focus {
    outline: none;
    border-color: var(--primary);
  }
  input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 16px;
  }
  .btn {
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
  }
  .btn-primary {
    background: var(--primary);
    color: white;
  }
  .btn-primary:hover {
    opacity: 0.9;
  }
  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn-danger {
    background: #fee2e2;
    color: #dc2626;
    border: 1px solid #fecaca;
  }
  .btn-danger:hover {
    background: #fecaca;
  }
  .danger-zone {
    border-color: #fecaca;
  }
  .zones-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .zones-header-row {
    display: flex;
    gap: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
  }
  .zone-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .zone-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    width: 32px;
    flex-shrink: 0;
  }
  .zone-col {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    flex: 1;
    text-align: center;
  }
  .zone-input {
    flex: 1;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
    text-align: center;
  }
  .zone-input:focus {
    outline: none;
    border-color: var(--primary);
  }
  .zone-placeholder {
    flex: 1;
    padding: 8px 10px;
    text-align: center;
    font-size: 14px;
    color: var(--text-secondary);
    opacity: 0.4;
  }
  .zone-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 8px;
  }
  .zone-saved {
    margin-left: auto;
    color: #16a34a;
    font-size: 13px;
    font-weight: 500;
  }
  .success {
    color: #16a34a;
    font-size: 14px;
    margin: 0;
  }
  .users-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .user-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: var(--bg);
    border-radius: 8px;
  }
  .user-email {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    min-width: 180px;
  }
  .user-name {
    font-size: 13px;
    color: var(--text-secondary);
    flex: 1;
  }
  .user-badge {
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 12px;
    background: var(--border-light);
    color: var(--text-secondary);
  }
  .user-badge.admin {
    background: #dbeafe;
    color: #1d4ed8;
  }
  .btn-sm {
    padding: 6px 12px;
    font-size: 12px;
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: 22px; }
    .field-row { flex-direction: column; }
    .card-body { padding: 16px; }
  }
</style>
