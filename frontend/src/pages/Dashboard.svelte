<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';
  import MonthHeatmap from '$lib/components/MonthHeatmap.svelte';
  import SportBreakdown from '$lib/components/SportBreakdown.svelte';
  import { statsApi, userApi, activitiesApi } from '$lib/api/types';
  import type { DashboardResponse, PeriodStats, User, HeatmapDay, VolumeResponse } from '$lib/api/types';

  interface Props {
    onNavigate?: (page: string, id?: number) => void;
  }

  let { onNavigate }: Props = $props();

  let dashboard = $state<DashboardResponse | null>(null);
  let user = $state<User | null>(null);
  let heatmapData = $state<HeatmapDay[]>([]);
  let volumeData = $state<VolumeResponse | null>(null);
  let loading = $state(true);
  let error = $state('');
  let selectedPeriod = $state<'week' | 'month' | 'all_time'>('month');

  const sportColors: Record<string, string> = {
    run: '#22c55e',
    ride: '#3b82f6',
    swim: '#06b6d4',
    hike: '#f97316',
    walk: '#f59e0b',
    other: '#8b5cf6',
  };

  const sportIcons: Record<string, string> = {
    run: 'activity',
    ride: 'ride',
    swim: 'swim',
    hike: 'hike',
    walk: 'activity',
    other: 'activity',
  };

  async function load() {
    loading = true;
    error = '';
    try {
      const [dash, hm, vol, userData] = await Promise.all([
        statsApi.dashboard(),
        statsApi.heatmap(),
        statsApi.volume(),
        userApi.me().catch(() => null),
      ]);
      dashboard = dash;
      heatmapData = hm;
      volumeData = vol;
      user = userData;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load dashboard';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  function getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }

  function formatDate(): string {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return `${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()} · ${now.getFullYear()}`;
  }

  function getUserName(): string {
    if (user?.name) return user.name;
    if (user?.email) return user.email.split('@')[0];
    return 'User';
  }

  function formatKm(m: number): string {
    return (m / 1000).toFixed(1);
  }

  function formatDuration(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  function formatDurationShort(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function formatPace(speed: number | null): string {
    if (!speed || speed === 0) return '-';
    const pace = 1000 / speed / 60;
    const min = Math.floor(pace);
    const sec = Math.floor((pace - min) * 60);
    return `${min}:${sec.toString().padStart(2, '0')}/km`;
  }

  function formatDateShort(iso: string): string {
    const d = new Date(iso);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${d.getDate()} ${months[d.getMonth()]}`;
  }

  function sparklinePath(data: number[], w: number, h: number): string {
    if (data.length < 2) return '';
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;
    const stepX = w / (data.length - 1);
    const pts = data.map((v, i) => {
      const x = i * stepX;
      const y = h - ((v - min) / range) * (h - pad * 2) - pad;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    return `M${pts.join(' L')}`;
  }

  let currentStats = $derived(
    dashboard ? dashboard[selectedPeriod] : null
  );

  let prevPeriod = $derived(
    dashboard ? dashboard[`prev_${selectedPeriod}` as keyof DashboardResponse] as PeriodStats | null ?? null : null
  );

  function calcTrend(current: number, prev: number | null): { value: number; positive: boolean; absolute?: boolean } | null {
    if (prev === null) return null;
    if (prev === 0) {
      if (current === 0) return null;
      return { value: current, positive: true, absolute: true };
    }
    const pct = ((current - prev) / prev) * 100;
    return { value: Math.abs(Math.round(pct)), positive: pct >= 0 };
  }

  function getPrevPeriodLabel(period: string): string {
    switch (period) {
      case 'week': return 'last week';
      case 'month': return 'last month';
      case 'year': return 'last year';
      case 'all_time': return 'all time';
      default: return `last ${period}`;
    }
  }

  let distanceTrend = $derived(
    currentStats && prevPeriod ? calcTrend(currentStats.distance_m, prevPeriod.distance_m) : null
  );
  let durationTrend = $derived(
    currentStats && prevPeriod ? calcTrend(currentStats.duration_s, prevPeriod.duration_s) : null
  );
  let elevationTrend = $derived(
    currentStats && prevPeriod ? calcTrend(currentStats.elevation_gain, prevPeriod.elevation_gain) : null
  );

  let recentActivities = $derived(
    dashboard ? dashboard.recent.slice(0, 5) : []
  );
</script>

<div class="dashboard">
  {#if loading}
    <LoadingSpinner size="lg" />
  {:else if error}
    <ErrorBanner message={error} retry={load} />
  {:else if dashboard}
    <!-- Topbar -->
    <div class="dash-topbar">
      <div class="greeting">
        <h1>{getGreeting()}, {getUserName()}</h1>
        <p class="date-text">{formatDate()}</p>
      </div>
      <div class="topbar-right">
        <button class="log-btn" onclick={() => onNavigate?.('upload')}>
          <Icon name="segments" size={16} />
          Log activity
        </button>
      </div>
    </div>

    <!-- Period Selector -->
    <div class="period-tabs">
      <button
        class="period-tab"
        class:active={selectedPeriod === 'week'}
        onclick={() => selectedPeriod = 'week'}
      >This week</button>
      <button
        class="period-tab"
        class:active={selectedPeriod === 'month'}
        onclick={() => selectedPeriod = 'month'}
      >This month</button>
      <button
        class="period-tab"
        class:active={selectedPeriod === 'all_time'}
        onclick={() => selectedPeriod = 'all_time'}
      >All time</button>
    </div>

    <!-- Metric Cards -->
    {#if currentStats}
      <div class="metric-grid">
        <div class="dash-metric-card">
          <div class="metric-icon" style="background: #3b82f620; color: #3b82f6">
            <Icon name="distance" size={18} />
          </div>
          <div class="metric-label">Distance</div>
          <div class="metric-value">{formatKm(currentStats.distance_m)} <span class="metric-unit">km</span></div>
          {#if distanceTrend}
            <div class="metric-trend" class:positive={distanceTrend.positive} class:negative={!distanceTrend.positive}>
              <span class="trend-arrow">{distanceTrend.positive ? '↑' : '↓'}</span>
              {distanceTrend.absolute ? `${formatKm(distanceTrend.value)} km` : `${distanceTrend.value}%`} vs {getPrevPeriodLabel(selectedPeriod)}
            </div>
          {:else}
            <div class="metric-trend muted">-</div>
          {/if}
          <div class="sparkline-wrap">
            <svg viewBox="0 0 100 16" preserveAspectRatio="none">
              <path d={volumeData ? sparklinePath(volumeData.monthly.map(m => m.distance_m), 100, 16) : ''} stroke="#3b82f6" stroke-width="1.5" fill="none" />
            </svg>
          </div>
        </div>

        <div class="dash-metric-card">
          <div class="metric-icon" style="background: #14b8a620; color: #14b8a6">
            <Icon name="duration" size={18} />
          </div>
          <div class="metric-label">Duration</div>
          <div class="metric-value">{formatDuration(currentStats.duration_s)}</div>
          {#if durationTrend}
            <div class="metric-trend" class:positive={durationTrend.positive} class:negative={!durationTrend.positive}>
              <span class="trend-arrow">{durationTrend.positive ? '↑' : '↓'}</span>
              {durationTrend.absolute ? formatDurationShort(durationTrend.value) : `${durationTrend.value}%`} vs {getPrevPeriodLabel(selectedPeriod)}
            </div>
          {:else}
            <div class="metric-trend muted">-</div>
          {/if}
          <div class="sparkline-wrap">
            <svg viewBox="0 0 100 16" preserveAspectRatio="none">
              <path d={volumeData ? sparklinePath(volumeData.monthly.map(m => m.duration_s), 100, 16) : ''} stroke="#14b8a6" stroke-width="1.5" fill="none" />
            </svg>
          </div>
        </div>

        <div class="dash-metric-card">
          <div class="metric-icon" style="background: #f59e0b20; color: #f59e0b">
            <Icon name="elevation" size={18} />
          </div>
          <div class="metric-label">Elevation</div>
          <div class="metric-value">{Math.round(currentStats.elevation_gain)} <span class="metric-unit">m</span></div>
          {#if elevationTrend}
            <div class="metric-trend" class:positive={elevationTrend.positive} class:negative={!elevationTrend.positive}>
              <span class="trend-arrow">{elevationTrend.positive ? '↑' : '↓'}</span>
              {elevationTrend.absolute ? `${elevationTrend.value} m` : `${elevationTrend.value}%`} vs {getPrevPeriodLabel(selectedPeriod)}
            </div>
          {:else}
            <div class="metric-trend muted">-</div>
          {/if}
          <div class="sparkline-wrap">
            <svg viewBox="0 0 100 16" preserveAspectRatio="none">
              <path d={volumeData ? sparklinePath(volumeData.monthly.map(m => m.elevation_m), 100, 16) : ''} stroke="#f59e0b" stroke-width="1.5" fill="none" />
            </svg>
          </div>
        </div>

        <div class="dash-metric-card">
          <div class="metric-icon" style="background: #f9731620; color: #f97316">
            <Icon name="activity" size={18} />
          </div>
          <div class="metric-label">Activities</div>
          <div class="metric-value">{currentStats.activity_count}</div>
          <div class="metric-trend muted">
            {#if dashboard.by_sport.length > 0}
              {dashboard.by_sport.map(s => `${s.activity_count} ${s.sport_type}${s.activity_count > 1 ? 's' : ''}`).join(' · ')}
            {:else}
              -
            {/if}
          </div>
          <div class="sparkline-wrap">
            <svg viewBox="0 0 100 16" preserveAspectRatio="none">
              <path d={volumeData ? sparklinePath(volumeData.monthly.map(m => m.count), 100, 16) : ''} stroke="#f97316" stroke-width="1.5" fill="none" />
            </svg>
          </div>
        </div>
      </div>
    {/if}

    <!-- Two Column Row -->
    <div class="two-col-row">
      <!-- By Sport Card -->
      <div class="dash-card">
        <div class="card-header">
          <h3>By sport</h3>
        </div>
        {#if dashboard.by_sport.length > 0}
          <SportBreakdown data={dashboard.by_sport} />
        {:else}
          <p class="empty-text">No activity data yet</p>
        {/if}
      </div>

      <!-- Activity Heatmap Card -->
      <div class="dash-card">
        {#if heatmapData.length > 0}
          <MonthHeatmap data={heatmapData} />
        {:else}
          <div class="card-header">
            <h3>Activity heatmap</h3>
          </div>
          <p class="empty-text">No activity data yet</p>
        {/if}
      </div>
    </div>

    <!-- Recent Activities -->
    {#if recentActivities.length > 0}
      <div class="dash-card full-width">
        <div class="card-header">
          <h3>Recent activities</h3>
          <button class="view-all-link" onclick={() => onNavigate?.('activities')}>View all →</button>
        </div>
        <div class="activities-table">
          <div class="table-header">
            <span class="col-activity">Activity</span>
            <span class="col-date">Date</span>
            <span class="col-num">Distance</span>
            <span class="col-num">Duration</span>
            <span class="col-num">Pace</span>
            <span class="col-num">Elevation</span>
          </div>
          {#each recentActivities as act, i}
            <button class="table-row" onclick={() => onNavigate?.('activity', act.id)}>
              <span class="col-activity">
                <span class="activity-dot" style="background: {sportColors[act.sport_type] ?? sportColors.other}"></span>
                <span class="activity-info">
                  <span class="activity-name">{act.name}</span>
                  <span class="activity-sport">{act.sport_type}</span>
                </span>
              </span>
              <span class="col-date">{formatDateShort(act.start_time)}</span>
              <span class="col-num">{act.distance_m ? formatKm(act.distance_m) : '-'} km</span>
              <span class="col-num">{act.duration_s ? formatDuration(act.duration_s) : '-'}</span>
              <span class="col-num">
                <span class="pace-pill">{formatPace(act.avg_speed)}</span>
              </span>
              <span class="col-num">{act.elevation_gain ? Math.round(act.elevation_gain) : '-'} m</span>
            </button>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .dashboard {
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
    font-family: var(--font-sans);
  }

  /* Topbar */
  .dash-topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
  }
  .greeting h1 {
    font-size: 22px;
    font-weight: 500;
    margin: 0;
    color: var(--text);
  }
  .date-text {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
    margin: 4px 0 0;
  }
  .topbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .log-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text);
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 400;
    cursor: pointer;
    transition: all 0.15s;
  }
  .log-btn:hover {
    background: var(--hover);
    border-color: var(--primary);
  }

  /* Period Tabs */
  .period-tabs {
    display: flex;
    gap: 4px;
    background: var(--bg);
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 20px;
    width: fit-content;
  }
  .period-tab {
    padding: 8px 16px;
    border: none;
    border-radius: 8px;
    background: none;
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 400;
    cursor: pointer;
    transition: all 0.15s;
  }
  .period-tab:hover {
    color: var(--text);
  }
  .period-tab.active {
    background: var(--surface);
    color: var(--text);
    font-weight: 500;
    border: 1px solid var(--border);
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  }

  /* Metric Cards */
  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }
  .dash-metric-card {
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
  .metric-trend {
    font-size: 12px;
    font-weight: 400;
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .metric-trend.positive {
    color: #22c55e;
  }
  .metric-trend.negative {
    color: #ef4444;
  }
  .metric-trend.muted {
    color: var(--text-secondary);
  }
  .trend-arrow {
    font-weight: 500;
  }
  .sparkline-wrap {
    margin-top: 10px;
    height: 16px;
  }
  .sparkline-wrap svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  /* Two Column Row */
  .two-col-row {
    display: grid;
    grid-template-columns: 3fr 2fr;
    gap: 12px;
    margin-bottom: 20px;
  }

  /* Dash Card */
  .dash-card {
    margin-bottom: 0;
  }
  .dash-card.full-width {
    width: 100%;
  }

  .view-all-link {
    font-size: 13px;
    font-weight: 400;
    color: var(--primary);
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
  }
  .view-all-link:hover {
    text-decoration: underline;
  }

  /* Recent Activities Table */
  .activities-table {
    width: 100%;
  }
  .table-header {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 0.5px solid var(--border);
  }
  .table-header span {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }
  .table-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr;
    gap: 8px;
    padding: 12px 0;
    border-bottom: 0.5px solid var(--border);
    align-items: center;
    background: none;
    border-left: none;
    border-right: none;
    border-top: none;
    width: 100%;
    cursor: pointer;
    font-family: var(--font-sans);
    text-align: left;
  }
  .table-row:last-child {
    border-bottom: none;
  }
  .table-row:hover {
    background: var(--hover);
  }
  .col-activity {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .activity-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .activity-info {
    display: flex;
    flex-direction: column;
  }
  .activity-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
  }
  .activity-sport {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    text-transform: capitalize;
  }
  .col-date {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
    text-align: right;
  }
  .col-num {
    font-size: 13px;
    font-weight: 400;
    color: var(--text);
    text-align: right;
  }
  .pace-pill {
    display: inline-block;
    background: var(--bg);
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
  }
  .empty-text {
    font-size: 13px;
    font-weight: 400;
    color: var(--text-secondary);
    text-align: center;
    padding: 20px 0;
  }

  @media (max-width: 768px) {
    .dashboard { padding: 16px; }
    .dash-topbar { flex-wrap: wrap; gap: 12px; }
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .two-col-row { grid-template-columns: 1fr; }
    .table-header, .table-row {
      grid-template-columns: 2fr 1fr 1fr 1fr;
    }
    .col-num:nth-child(5),
    .col-num:nth-child(6) {
      display: none;
    }
    .table-header span:nth-child(5),
    .table-header span:nth-child(6) {
      display: none;
    }
  }
</style>
