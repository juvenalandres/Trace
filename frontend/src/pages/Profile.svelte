<script lang="ts">
  import { onMount } from 'svelte';
  import { userApi, zonesApi, statsApi, fitnessTestApi } from '$lib/api/types';
  import type { User, UserZone, DashboardResponse, FitnessTest } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import Toast from '$lib/components/Toast.svelte';

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
  let error = $state('');

  let hrZone = $state<UserZone | null>(null);
  let powerZone = $state<UserZone | null>(null);
  let hrNumZones = $state(5);
  let powerNumZones = $state(5);
  let zonesLoading = $state(true);
  let hrExpanded = $state(false);
  let powerExpanded = $state(false);

  let users = $state<User[]>([]);
  let usersLoading = $state(false);
  let usersError = $state('');
  let dashboard = $state<DashboardResponse | null>(null);
  let fitnessTests = $state<FitnessTest[]>([]);
  let editingBenchmark = $state<string | null>(null);

  // Toast state
  let toasts = $state<{ id: number; message: string; type: 'success' | 'error' | 'info' }[]>([]);
  let toastCounter = 0;

  function showToast(message: string, type: 'success' | 'error' | 'info' = 'success') {
    const id = ++toastCounter;
    toasts = [...toasts, { id, message, type }];
    setTimeout(() => { toasts = toasts.filter(t => t.id !== id); }, 3000);
  }

  function dismissToast(id: number) {
    toasts = toasts.filter(t => t.id !== id);
  }

  // Dirty state tracking
  let profileDirty = $state(false);
  let hrDirty = $state(false);
  let powerDirty = $state(false);

  // Snapshot of original profile values for dirty check
  let originalProfile = $state({ name: '', preferredUnits: 'metric', weightKg: '', ftpWatts: '', maxHr: '', restingHr: '' });

  function snapshotProfile() {
    originalProfile = { name, preferredUnits, weightKg, ftpWatts, maxHr, restingHr };
  }

  function checkProfileDirty() {
    profileDirty =
      name !== originalProfile.name ||
      preferredUnits !== originalProfile.preferredUnits ||
      weightKg !== originalProfile.weightKg ||
      ftpWatts !== originalProfile.ftpWatts ||
      maxHr !== originalProfile.maxHr ||
      restingHr !== originalProfile.restingHr;
  }

  // Dynamic flat arrays: 2 values per zone (min, max), max 14 values for 7 zones
  let hrValues = $state<number[]>(new Array(14).fill(0));
  let powerValues = $state<number[]>(new Array(14).fill(0));
  let hrSnapshot = $state<number[]>(new Array(14).fill(0));
  let powerSnapshot = $state<number[]>(new Array(14).fill(0));

  const HR_ZONE_KEYS = ['zone_1_min', 'zone_1_max', 'zone_2_min', 'zone_2_max', 'zone_3_min', 'zone_3_max', 'zone_4_min', 'zone_4_max', 'zone_5_min', 'zone_5_max'] as const;

  function updateHrValuesFromZone() {
    if (!hrZone) return;
    hrNumZones = hrZone.num_zones ?? 5;
    hrValues = new Array(14).fill(0);
    for (let i = 0; i < HR_ZONE_KEYS.length; i++) {
      hrValues[i] = (hrZone as unknown as Record<string, number | null>)[HR_ZONE_KEYS[i]] ?? 0;
    }
    if (hrNumZones >= 6) {
      hrValues[10] = hrZone.zone_6_min ?? 0;
      hrValues[11] = hrZone.zone_6_max ?? 0;
    }
    if (hrNumZones >= 7) {
      hrValues[12] = hrZone.zone_7_min ?? 0;
      hrValues[13] = hrZone.zone_7_max ?? 0;
    }
    hrSnapshot = [...hrValues];
  }

  function updatePowerValuesFromZone() {
    if (!powerZone) return;
    powerNumZones = powerZone.num_zones ?? 5;
    powerValues = new Array(14).fill(0);
    for (let i = 0; i < HR_ZONE_KEYS.length; i++) {
      powerValues[i] = (powerZone as unknown as Record<string, number | null>)[HR_ZONE_KEYS[i]] ?? 0;
    }
    if (powerNumZones >= 6) {
      powerValues[10] = powerZone.zone_6_min ?? 0;
      powerValues[11] = powerZone.zone_6_max ?? 0;
    }
    if (powerNumZones >= 7) {
      powerValues[12] = powerZone.zone_7_min ?? 0;
      powerValues[13] = powerZone.zone_7_max ?? 0;
    }
    powerSnapshot = [...powerValues];
  }

  function checkHrDirty() {
    hrDirty = hrValues.some((v, i) => v !== hrSnapshot[i]) || hrNumZones !== (hrZone?.num_zones ?? 5);
  }

  function checkPowerDirty() {
    powerDirty = powerValues.some((v, i) => v !== powerSnapshot[i]) || powerNumZones !== (powerZone?.num_zones ?? 5);
  }

  async function loadZones() {
    try {
      const zones = await zonesApi.list();
      hrZone = zones.find(z => z.zone_type === 'hr') ?? null;
      powerZone = zones.find(z => z.zone_type === 'power') ?? null;
      updateHrValuesFromZone();
      updatePowerValuesFromZone();
      hrDirty = false;
      powerDirty = false;
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
    snapshotProfile();
    loadZones();
    loadUsers();
    statsApi.dashboard().then(d => { dashboard = d; }).catch(() => {});
    fitnessTestApi.list().then(t => { fitnessTests = t; }).catch(() => {});
  });

  function latestTest(type: string): FitnessTest | undefined {
    return fitnessTests.filter(t => t.test_type === type).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  }

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 30) return `${diffDays}d ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  // Zone bar helpers
  const HR_ZONE_COLORS = ['var(--zone-hr-1)', 'var(--zone-hr-2)', 'var(--zone-hr-3)', 'var(--zone-hr-4)', 'var(--zone-hr-5)', 'var(--zone-hr-6)', 'var(--zone-hr-7)'];
  const POWER_ZONE_COLORS = ['var(--zone-power-1)', 'var(--zone-power-2)', 'var(--zone-power-3)', 'var(--zone-power-4)', 'var(--zone-power-5)', 'var(--zone-power-6)', 'var(--zone-power-7)'];

  function getZoneRanges(values: number[], numZones: number): { min: number; max: number }[] {
    const ranges: { min: number; max: number }[] = [];
    for (let i = 0; i < numZones; i++) {
      const min = i === 0 ? 0 : values[i * 2] || 0;
      const max = i === numZones - 1 ? (values[(i - 1) * 2 + 1] || 0) * 1.2 : values[i * 2 + 1] || 0;
      ranges.push({ min, max });
    }
    return ranges;
  }

  function getZoneBarSegments(values: number[], numZones: number, colors: string[]): { grow: number; color: string; label: string; range: string }[] {
    const ranges = getZoneRanges(values, numZones);
    if (ranges.length === 0) return [];
    return ranges.map((r, i) => {
      const size = r.max - r.min || 1;
      const range = i === 0 ? `< ${r.max}` : i === numZones - 1 ? `${r.min}+` : `${r.min}–${r.max}`;
      return { grow: size, color: colors[i], label: `Z${i + 1}`, range };
    });
  }

  // Auto-save profile on change (debounced)
  let profileSaveTimeout: ReturnType<typeof setTimeout> | null = null;

  function scheduleProfileSave() {
    checkProfileDirty();
    if (!profileDirty) return;
    if (profileSaveTimeout) clearTimeout(profileSaveTimeout);
    profileSaveTimeout = setTimeout(saveProfile, 1500);
  }

  async function saveProfile() {
    saving = true;
    error = '';
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
      const fresh = await userApi.me();
      name = fresh.name ?? '';
      preferredUnits = fresh.preferred_units ?? 'metric';
      weightKg = fresh.weight_kg?.toString() ?? '';
      ftpWatts = fresh.ftp_watts?.toString() ?? '';
      maxHr = fresh.max_hr?.toString() ?? '';
      restingHr = fresh.resting_hr?.toString() ?? '';
      snapshotProfile();
      profileDirty = false;
      onUserUpdated?.(fresh);
      showToast('Profile saved');
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save';
      showToast(error, 'error');
    } finally {
      saving = false;
    }
  }

  function buildPayload(values: number[], numZones: number, zoneType: string) {
    return {
      zone_type: zoneType,
      num_zones: numZones,
      zone_1_min: values[0] || undefined,
      zone_1_max: values[1] || undefined,
      zone_2_min: values[2] || undefined,
      zone_2_max: values[3] || undefined,
      zone_3_min: values[4] || undefined,
      zone_3_max: values[5] || undefined,
      zone_4_min: values[6] || undefined,
      zone_4_max: values[7] || undefined,
      zone_5_min: values[8] || undefined,
      zone_5_max: values[9] || undefined,
      zone_6_min: numZones >= 6 ? values[10] || undefined : undefined,
      zone_6_max: numZones >= 6 ? values[11] || undefined : undefined,
      zone_7_min: numZones >= 7 ? values[12] || undefined : undefined,
      zone_7_max: numZones >= 7 ? values[13] || undefined : undefined,
    };
  }

  // Auto-save zones on change (debounced)
  let hrSaveTimeout: ReturnType<typeof setTimeout> | null = null;
  let powerSaveTimeout: ReturnType<typeof setTimeout> | null = null;

  function scheduleHrSave() {
    checkHrDirty();
    if (!hrDirty) return;
    if (hrSaveTimeout) clearTimeout(hrSaveTimeout);
    hrSaveTimeout = setTimeout(saveHrZones, 1500);
  }

  function schedulePowerSave() {
    checkPowerDirty();
    if (!powerDirty) return;
    if (powerSaveTimeout) clearTimeout(powerSaveTimeout);
    powerSaveTimeout = setTimeout(savePowerZones, 1500);
  }

  async function saveHrZones() {
    try {
      const payload = buildPayload(hrValues, hrNumZones, 'hr');
      if (hrZone) {
        await zonesApi.update(hrZone.id, payload);
      } else {
        await zonesApi.create(payload);
      }
      await loadZones();
      showToast('HR zones saved');
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save HR zones';
      showToast(error, 'error');
    }
  }

  async function savePowerZones() {
    try {
      const payload = buildPayload(powerValues, powerNumZones, 'power');
      if (powerZone) {
        await zonesApi.update(powerZone.id, payload);
      } else {
        await zonesApi.create(payload);
      }
      await loadZones();
      showToast('Power zones saved');
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save power zones';
      showToast(error, 'error');
    }
  }

  function switchHrZones(target: number) {
    if (target === hrNumZones) return;
    if (target === 7 && !maxHr) {
      error = 'Set your Max HR first before using 7 HR zones.';
      showToast(error, 'error');
      return;
    }
    hrNumZones = target;
    checkHrDirty();
    scheduleHrSave();
  }

  function switchPowerZones(target: number) {
    if (target === powerNumZones) return;
    if (target === 7 && !ftpWatts) {
      error = 'Set your FTP first before using 7 power zones.';
      showToast(error, 'error');
      return;
    }
    powerNumZones = target;
    checkPowerDirty();
    schedulePowerSave();
  }

  // Immediate save for zone input changes
  function onHrInputChange() {
    checkHrDirty();
    scheduleHrSave();
  }

  function onPowerInputChange() {
    checkPowerDirty();
    schedulePowerSave();
  }

  function formatKm(m: number): string {
    return (m / 1000).toFixed(0);
  }

  function formatHours(s: number): string {
    const h = Math.floor(s / 3600);
    if (h >= 1000) return (h / 1000).toFixed(1) + 'k';
    return String(h);
  }

  function memberSince(dateStr: string): string {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  function userInitial(): string {
    const n = user?.name ?? user?.email ?? '?';
    return n.charAt(0).toUpperCase();
  }
</script>

<div class="page">
  <div class="hero">
    <div class="hero-main">
      <div class="avatar">{userInitial()}</div>
      <div class="hero-info">
        <h1>{user?.name || user?.email}</h1>
        {#if user?.created_at}
          <span class="member-since">Member since {memberSince(user.created_at)}</span>
        {/if}
      </div>
    </div>
    {#if dashboard}
      <div class="hero-stats">
        <div class="hero-stat">
          <span class="hero-stat-value">{dashboard.all_time.activity_count}</span>
          <span class="hero-stat-label">Activities</span>
        </div>
        <div class="hero-stat-divider"></div>
        <div class="hero-stat">
          <span class="hero-stat-value">{formatKm(dashboard.all_time.distance_m)}<span class="hero-stat-unit"> km</span></span>
          <span class="hero-stat-label">Total distance</span>
        </div>
        <div class="hero-stat-divider"></div>
        <div class="hero-stat">
          <span class="hero-stat-value">{formatHours(dashboard.all_time.duration_s)}<span class="hero-stat-unit"> h</span></span>
          <span class="hero-stat-label">Total time</span>
        </div>
        <div class="hero-stat-divider"></div>
        <div class="hero-stat">
          <span class="hero-stat-value">{(dashboard.all_time.elevation_gain / 1000).toFixed(1)}<span class="hero-stat-unit"> km</span></span>
          <span class="hero-stat-label">Elevation gain</span>
        </div>
      </div>
    {/if}
  </div>

  <Toast {toasts} ondismiss={dismissToast} />

  <div class="card">
    <div class="card-header">
      <Icon name="activity" size={20} />
      <span>Account</span>
      {#if profileDirty}
        <span class="dirty-dot" title="Unsaved changes"></span>
      {/if}
    </div>
    <div class="card-body">
      <div class="field">
        <label for="email">Email</label>
        <input id="email" type="email" value={user?.email ?? ''} disabled />
      </div>
      <div class="field">
        <label for="name">Name</label>
        <input id="name" type="text" bind:value={name} oninput={scheduleProfileSave} placeholder="Your name" />
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <Icon name="speed" size={20} />
      <span>Benchmarks</span>
      {#if profileDirty}
        <span class="dirty-dot" title="Unsaved changes"></span>
      {/if}
    </div>
    <div class="card-body">
      <div class="benchmarks-grid">
        <div class="benchmark-card">
          <div class="benchmark-icon" style="background: var(--primary-light); color: var(--primary);">
            <Icon name="chart" size={16} />
          </div>
          <div class="benchmark-info">
            <span class="benchmark-label">FTP</span>
            {#if editingBenchmark === 'ftp'}
              <input class="benchmark-input" type="number" bind:value={ftpWatts} oninput={scheduleProfileSave} onblur={() => editingBenchmark = null} placeholder="—" autofocus />
            {:else}
              <button class="benchmark-value" onclick={() => { editingBenchmark = 'ftp'; }}>
                {latestTest('ftp') ? `${Math.round(latestTest('ftp')!.value)} W` : ftpWatts ? `${ftpWatts} W` : '—'}
              </button>
            {/if}
          </div>
          {#if latestTest('ftp')}
            <span class="benchmark-date" title={latestTest('ftp')!.created_at}>{formatDate(latestTest('ftp')!.created_at)}</span>
          {/if}
        </div>

        <div class="benchmark-card">
          <div class="benchmark-icon" style="background: var(--danger-bg); color: var(--danger);">
            <Icon name="insights" size={16} />
          </div>
          <div class="benchmark-info">
            <span class="benchmark-label">LTHR</span>
            {#if latestTest('lthr')}
              <span class="benchmark-value">{Math.round(latestTest('lthr')!.value)} bpm</span>
            {:else}
              <span class="benchmark-value benchmark-empty">—</span>
            {/if}
          </div>
          {#if latestTest('lthr')}
            <span class="benchmark-date" title={latestTest('lthr')!.created_at}>{formatDate(latestTest('lthr')!.created_at)}</span>
          {/if}
        </div>

        <div class="benchmark-card">
          <div class="benchmark-icon" style="background: var(--danger-bg); color: var(--danger);">
            <Icon name="heart" size={16} />
          </div>
          <div class="benchmark-info">
            <span class="benchmark-label">Max HR</span>
            {#if editingBenchmark === 'maxhr'}
              <input class="benchmark-input" type="number" bind:value={maxHr} oninput={scheduleProfileSave} onblur={() => editingBenchmark = null} placeholder="—" autofocus />
            {:else}
              <button class="benchmark-value" onclick={() => { editingBenchmark = 'maxhr'; }}>
                {latestTest('max_hr') ? `${Math.round(latestTest('max_hr')!.value)} bpm` : maxHr ? `${maxHr} bpm` : '—'}
              </button>
            {/if}
          </div>
          {#if latestTest('max_hr')}
            <span class="benchmark-date" title={latestTest('max_hr')!.created_at}>{formatDate(latestTest('max_hr')!.created_at)}</span>
          {/if}
        </div>

        <div class="benchmark-card">
          <div class="benchmark-icon" style="background: var(--danger-bg); color: var(--danger);">
            <Icon name="heart" size={16} />
          </div>
          <div class="benchmark-info">
            <span class="benchmark-label">Resting HR</span>
            {#if editingBenchmark === 'resthr'}
              <input class="benchmark-input" type="number" bind:value={restingHr} oninput={scheduleProfileSave} onblur={() => editingBenchmark = null} placeholder="—" autofocus />
            {:else}
              <button class="benchmark-value" onclick={() => { editingBenchmark = 'resthr'; }}>
                {restingHr ? `${restingHr} bpm` : '—'}
              </button>
            {/if}
          </div>
        </div>

        <div class="benchmark-card">
          <div class="benchmark-icon" style="background: var(--bg-subtle); color: #8b5cf6;">
            <Icon name="activity" size={16} />
          </div>
          <div class="benchmark-info">
            <span class="benchmark-label">Weight</span>
            {#if editingBenchmark === 'weight'}
              <input class="benchmark-input" type="number" bind:value={weightKg} oninput={scheduleProfileSave} onblur={() => editingBenchmark = null} placeholder="—" step="0.1" autofocus />
            {:else}
              <button class="benchmark-value" onclick={() => { editingBenchmark = 'weight'; }}>
                {weightKg ? `${weightKg} kg` : '—'}
              </button>
            {/if}
          </div>
        </div>
      </div>
      <div class="benchmark-footer">
        <select class="units-select" bind:value={preferredUnits} onchange={scheduleProfileSave}>
          <option value="metric">Metric</option>
          <option value="imperial">Imperial</option>
        </select>
      </div>
    </div>
  </div>

  {#if !zonesLoading}
    <div class="card">
      <button class="card-header card-header-toggle" class:expanded={hrExpanded} onclick={() => { hrExpanded = !hrExpanded }}>
        <Icon name="heart" size={20} />
        <span>Heart Rate Zones (bpm)</span>
        {#if hrDirty}
          <span class="dirty-dot" title="Unsaved changes"></span>
        {/if}
        <Icon name="chevronDown" size={16} class="chevron-toggle {hrExpanded ? 'chevron-open' : ''}" />
      </button>
      {#if hrExpanded}
      <div class="card-body">
        <div class="zone-bar">
          {#each getZoneBarSegments(hrValues, hrNumZones, HR_ZONE_COLORS) as seg}
            <div class="zone-bar-seg" style="flex-grow: {seg.grow}; background: {seg.color}" title="{seg.label}: {seg.range}">
              <span class="zone-bar-label">{seg.label}</span>
            </div>
          {/each}
        </div>
        <div class="zones-grid">
          <div class="zones-header-row">
            <span class="zone-label">Zone</span>
            <span class="zone-col">Min</span>
            <span class="zone-col">Max</span>
          </div>
          {#each Array.from({length: hrNumZones}, (_, i) => i + 1) as zi}
            <div class="zone-row">
              <span class="zone-label">Z{zi}</span>
              {#if zi === 1}
                <span class="zone-placeholder">—</span>
              {:else}
                <input class="zone-input" type="number" bind:value={hrValues[(zi - 1) * 2]} oninput={onHrInputChange} placeholder="—" />
              {/if}
              {#if zi === hrNumZones}
                <span class="zone-placeholder">—</span>
              {:else}
                <input class="zone-input" type="number" bind:value={hrValues[(zi - 1) * 2 + 1]} oninput={onHrInputChange} placeholder="—" />
              {/if}
            </div>
          {/each}
        </div>
        <div class="zone-actions">
          <div class="zone-count-toggle">
            <button class="toggle-btn" class:active={hrNumZones === 5} onclick={() => switchHrZones(5)}>5 zones</button>
            <button class="toggle-btn" class:active={hrNumZones === 7} onclick={() => switchHrZones(7)}>7 zones</button>
          </div>
        </div>
      </div>
      {/if}
    </div>

    <div class="card">
      <button class="card-header card-header-toggle" class:expanded={powerExpanded} onclick={() => { powerExpanded = !powerExpanded }}>
        <Icon name="power" size={20} />
        <span>Power Zones (watts)</span>
        {#if powerDirty}
          <span class="dirty-dot" title="Unsaved changes"></span>
        {/if}
        <Icon name="chevronDown" size={16} class="chevron-toggle {powerExpanded ? 'chevron-open' : ''}" />
      </button>
      {#if powerExpanded}
      <div class="card-body">
        <div class="zone-bar">
          {#each getZoneBarSegments(powerValues, powerNumZones, POWER_ZONE_COLORS) as seg}
            <div class="zone-bar-seg" style="flex-grow: {seg.grow}; background: {seg.color}" title="{seg.label}: {seg.range}">
              <span class="zone-bar-label">{seg.label}</span>
            </div>
          {/each}
        </div>
        <div class="zones-grid">
          <div class="zones-header-row">
            <span class="zone-label">Zone</span>
            <span class="zone-col">Min</span>
            <span class="zone-col">Max</span>
          </div>
          {#each Array.from({length: powerNumZones}, (_, i) => i + 1) as zi}
            <div class="zone-row">
              <span class="zone-label">Z{zi}</span>
              {#if zi === 1}
                <span class="zone-placeholder">—</span>
              {:else}
                <input class="zone-input" type="number" bind:value={powerValues[(zi - 1) * 2]} oninput={onPowerInputChange} placeholder="—" />
              {/if}
              {#if zi === powerNumZones}
                <span class="zone-placeholder">—</span>
              {:else}
                <input class="zone-input" type="number" bind:value={powerValues[(zi - 1) * 2 + 1]} oninput={onPowerInputChange} placeholder="—" />
              {/if}
            </div>
          {/each}
        </div>
        <div class="zone-actions">
          <div class="zone-count-toggle">
            <button class="toggle-btn" class:active={powerNumZones === 5} onclick={() => switchPowerZones(5)}>5 zones</button>
            <button class="toggle-btn" class:active={powerNumZones === 7} onclick={() => switchPowerZones(7)}>7 zones</button>
          </div>
        </div>
      </div>
      {/if}
    </div>
  {/if}

  {#if error}
    <ErrorBanner message={error} />
  {/if}

  <div class="actions">
    {#if profileDirty}
      <button class="btn btn-primary" onclick={saveProfile} disabled={saving}>
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
    {/if}
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
  .hero {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 28px 28px 20px;
    margin-bottom: 20px;
  }
  .hero-main {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }
  .avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--primary);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .hero-info h1 {
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 2px;
    line-height: 1.2;
  }
  .member-since {
    font-size: 13px;
    color: var(--text-secondary);
  }
  .hero-stats {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 14px 0 0;
    border-top: 1px solid var(--border);
  }
  .hero-stat {
    flex: 1;
    text-align: center;
  }
  .hero-stat-divider {
    width: 1px;
    height: 28px;
    background: var(--border);
    flex-shrink: 0;
  }
  .hero-stat-value {
    display: block;
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.2;
  }
  .hero-stat-unit {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
  }
  .hero-stat-label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-top: 2px;
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
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid var(--danger-border);
  }
  .btn-danger:hover {
    background: color-mix(in srgb, var(--danger) 15%, transparent);
  }
  .danger-zone {
    border-color: var(--danger-border);
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
    align-items: center;
    gap: 12px;
    margin-top: 8px;
  }
  .dirty-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--warning);
    flex-shrink: 0;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .zone-count-toggle {
    display: flex;
    border: 1px solid var(--border-color, #333);
    border-radius: 6px;
    overflow: hidden;
  }
  .toggle-btn {
    padding: 4px 12px;
    font-size: 12px;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    cursor: pointer;
    transition: all 0.15s;
  }
  .toggle-btn.active {
    background: var(--primary);
    color: #fff;
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
  background: var(--primary-light);
  color: var(--primary);
}
  .btn-sm {
    padding: 6px 12px;
    font-size: 12px;
  }
  .benchmarks-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
  }
  .benchmark-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
    background: var(--bg);
    border-radius: 8px;
    position: relative;
  }
  .benchmark-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    flex-shrink: 0;
  }
  .benchmark-info {
    flex: 1;
    min-width: 0;
  }
  .benchmark-label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--text-secondary);
    margin-bottom: 2px;
  }
  .benchmark-value {
    display: block;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    line-height: 1.2;
  }
  .benchmark-value:hover {
    color: var(--primary);
  }
  .benchmark-empty {
    color: var(--text-secondary);
    opacity: 0.5;
    cursor: default;
  }
  .benchmark-input {
    width: 100%;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--primary);
    border-radius: 4px;
    padding: 2px 4px;
    font-family: inherit;
    line-height: 1.2;
  }
  .benchmark-input:focus {
    outline: none;
    border-color: var(--primary);
  }
  .benchmark-date {
    font-size: 11px;
    color: var(--text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
  }
  .benchmark-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 4px;
  }
  .units-select {
    padding: 4px 8px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 12px;
    background: var(--bg);
    color: var(--text-secondary);
  }
  .zone-bar {
    display: flex;
    height: 28px;
    border-radius: 6px;
    gap: 1px;
    overflow: visible;
  }
  .zone-bar-seg {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    flex-shrink: 0;
    border-radius: 3px;
    overflow: hidden;
    transition: width 0.2s ease;
  }
  .zone-bar-label {
    font-size: 10px;
    font-weight: 600;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    line-height: 1;
    white-space: nowrap;
  }
  @media (max-width: 768px) {
    .page { padding: 16px; }
    h1 { font-size: 22px; }
    .field-row { flex-direction: column; }
    .card-body { padding: 16px; }
  }
</style>
