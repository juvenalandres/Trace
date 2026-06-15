<script lang="ts">
  import { isLoggedIn, clearToken } from '$lib/stores/auth';
  import { userApi, authApi } from '$lib/api/types';
  import type { User } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import Login from './pages/Login.svelte';
  import Dashboard from './pages/Dashboard.svelte';
  import Activities from './pages/Activities.svelte';
  import ActivityDetail from './pages/ActivityDetail.svelte';
  import Gear from './pages/Gear.svelte';
  import Segments from './pages/Segments.svelte';
  import MonthlyStats from './pages/MonthlyStats.svelte';
  import Eddington from './pages/Eddington.svelte';
  import Heatmap from './pages/Heatmap.svelte';
  import Statistics from './pages/Statistics.svelte';
  import Milestones from './pages/Milestones.svelte';
  import Upload from './pages/Upload.svelte';
  import Profile from './pages/Profile.svelte';
  import TrainingPlans from './pages/TrainingPlans.svelte';
  import TrainingCalendar from './pages/TrainingCalendar.svelte';
  import TrainingInsights from './pages/TrainingInsights.svelte';
  import RoutePlanner from './pages/RoutePlanner.svelte';
  import { onMount } from 'svelte';

  type Page = 'dashboard' | 'activities' | 'activity' | 'gear' | 'segments' | 'monthly' | 'eddingtong' | 'heatmap' | 'statistics' | 'milestones' | 'upload' | 'profile' | 'training-plans' | 'training-calendar' | 'training-insights' | 'route-planner';

  let loggedIn = $state(isLoggedIn());
  let currentPage = $state<Page>('dashboard');
  let activityId = $state<number | null>(null);
  let collapsed = $state(false);
  let mobileMenuOpen = $state(false);
  let user = $state<User | null>(null);

  onMount(async () => {
    if (loggedIn) {
      try {
        user = await userApi.me();
      } catch {
        // Token might be expired
      }
    }
  });

  function handleLogin() {
    loggedIn = true;
    userApi.me().then(u => user = u).catch(() => {});
  }

  function handleLogout() {
    authApi.logout().catch(() => {});
    clearToken();
    loggedIn = false;
    user = null;
  }

  function navigate(page: Page, id?: number) {
    currentPage = page;
    if (id !== undefined) activityId = id;
    mobileMenuOpen = false;
  }

  function getUserInitial(): string {
    if (user?.name) return user.name.charAt(0).toUpperCase();
    if (user?.email) return user.email.charAt(0).toUpperCase();
    return '?';
  }
</script>

{#if !loggedIn}
  <Login onLogin={handleLogin} />
{:else}
  <div class="app">
    <header class="topbar">
      <div class="topbar-left">
        <button class="toggle-btn" onclick={() => { if (window.innerWidth <= 768) { mobileMenuOpen = !mobileMenuOpen; } else { collapsed = !collapsed; } }} title="Menu">
          <Icon name={collapsed || mobileMenuOpen ? 'chevronRight' : 'chevronLeft'} size={18} />
        </button>
        <div class="brand">
          <img src="/brand.svg" alt="Trace" class="brand-logo" width="22" height="22" />
          <span class="brand-name">Trace</span>
        </div>
      </div>
      <div class="topbar-right">
        <button class="user-badge" onclick={() => navigate('profile')} title="Profile">
          <div class="avatar">{getUserInitial()}</div>
          {#if user?.name}
            <span class="user-name">{user.name}</span>
          {/if}
        </button>
      </div>
    </header>

    <div class="body">
      {#if mobileMenuOpen}
        <div class="sidebar-backdrop" onclick={() => mobileMenuOpen = false}></div>
      {/if}
      <nav class="sidebar" class:collapsed class:mobile-open={mobileMenuOpen}>
        <div class="nav-links">
          <button
            class="nav-link"
            class:active={currentPage === 'dashboard'}
            onclick={() => navigate('dashboard')}
            title="Dashboard"
          >
            <span class="nav-icon"><Icon name="dashboard" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Dashboard</span>{/if}
          </button>

          <div class="nav-separator"></div>

          <button
            class="nav-link"
            class:active={currentPage === 'activities'}
            onclick={() => navigate('activities')}
            title="Activities"
          >
            <span class="nav-icon"><Icon name="activities" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Activities</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'gear'}
            onclick={() => navigate('gear')}
            title="Gear"
          >
            <span class="nav-icon"><Icon name="gear" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Gear</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'segments'}
            onclick={() => navigate('segments')}
            title="Segments"
          >
            <span class="nav-icon"><Icon name="segments" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Segments</span>{/if}
          </button>

          <div class="nav-separator"></div>

          <button
            class="nav-link"
            class:active={currentPage === 'monthly'}
            onclick={() => navigate('monthly')}
            title="Monthly Stats"
          >
            <span class="nav-icon"><Icon name="monthly" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Monthly Stats</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'statistics'}
            onclick={() => navigate('statistics')}
            title="Statistics"
          >
            <span class="nav-icon"><Icon name="chart" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Statistics</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'heatmap'}
            onclick={() => navigate('heatmap')}
            title="Heatmap"
          >
            <span class="nav-icon"><Icon name="heatmap" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Heatmap</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'milestones'}
            onclick={() => navigate('milestones')}
            title="Milestones"
          >
            <span class="nav-icon"><Icon name="eddington" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Milestones</span>{/if}
          </button>

          <div class="nav-separator"></div>
          {#if !collapsed}<div class="nav-section-title">Training</div>{/if}

          <button
            class="nav-link"
            class:active={currentPage === 'training-plans'}
            onclick={() => navigate('training-plans')}
            title="Training Plans"
          >
            <span class="nav-icon"><Icon name="plans" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Plans</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'training-calendar'}
            onclick={() => navigate('training-calendar')}
            title="Training Calendar"
          >
            <span class="nav-icon"><Icon name="calendar" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Calendar</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'training-insights'}
            onclick={() => navigate('training-insights')}
            title="Training Insights"
          >
            <span class="nav-icon"><Icon name="insights" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Insights</span>{/if}
          </button>
          <button
            class="nav-link"
            class:active={currentPage === 'route-planner'}
            onclick={() => navigate('route-planner')}
            title="Route Planner"
          >
            <span class="nav-icon"><Icon name="route" size={20} /></span>
            {#if !collapsed}<span class="nav-label">Route Planner</span>{/if}
          </button>
        </div>
      </nav>

      <main class="content">
        {#if currentPage === 'dashboard'}
          <Dashboard onNavigate={(page, id) => navigate(page as Page, id)} />
        {:else if currentPage === 'activities'}
          <Activities onNavigate={(page, id) => navigate(page as Page, id)} />
        {:else if currentPage === 'activity' && activityId !== null}
          <ActivityDetail
            activityId={activityId}
            onBack={() => navigate('activities')}
          />
        {:else if currentPage === 'gear'}
          <Gear />
        {:else if currentPage === 'segments'}
          <Segments />
        {:else if currentPage === 'monthly'}
          <MonthlyStats onNavigate={(page, id) => navigate(page as Page, id)} />
        {:else if currentPage === 'eddingtong'}
          <Eddington />
        {:else if currentPage === 'heatmap'}
          <Heatmap />
        {:else if currentPage === 'statistics'}
          <Statistics onNavigate={(page, id) => navigate(page as Page, id)} />
        {:else if currentPage === 'milestones'}
          <Milestones />
        {:else if currentPage === 'training-plans'}
          <TrainingPlans />
        {:else if currentPage === 'training-calendar'}
          <TrainingCalendar onNavigate={(page, id) => navigate(page as Page, id)} />
        {:else if currentPage === 'training-insights'}
          <TrainingInsights />
        {:else if currentPage === 'route-planner'}
          <RoutePlanner />
        {:else if currentPage === 'upload'}
          <Upload onUploaded={(a) => navigate('activity', a.id)} />
        {:else if currentPage === 'profile'}
          <Profile {user} onLogout={handleLogout} onUserUpdated={(u) => user = u} />
        {/if}
      </main>
    </div>
  </div>
{/if}

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }
  .topbar {
    height: 56px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    flex-shrink: 0;
    width: 100%;
    box-sizing: border-box;
    z-index: 10;
  }
  .topbar-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .toggle-btn {
    width: 32px;
    height: 32px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .toggle-btn:hover {
    background: var(--hover);
    color: var(--text);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .brand-logo {
    border-radius: 4px;
    flex-shrink: 0;
  }
  .brand-name {
    font-size: 20px;
    font-weight: 700;
    color: var(--primary);
  }
  .topbar-right {
    display: flex;
    align-items: center;
  }
  .user-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border: none;
    background: none;
    cursor: pointer;
    border-radius: 8px;
  }
  .user-badge:hover {
    background: var(--hover);
  }
  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--primary);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
  }
  .user-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }
  .body {
    display: flex;
    flex: 1;
    overflow: hidden;
    min-height: 0;
  }
  .sidebar {
    width: 200px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 12px 0;
    flex-shrink: 0;
    transition: width 0.2s ease;
  }
  .sidebar.collapsed {
    width: 56px;
  }
  .nav-links {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 0 8px;
  }
  .nav-separator {
    height: 1px;
    background: var(--border);
    margin: 6px 4px;
  }
  .nav-section-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    padding: 4px 12px 2px;
  }
  .nav-link {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: none;
    background: none;
    color: #475569;
    font-size: 14px;
    cursor: pointer;
    border-radius: 8px;
    text-align: left;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
  }
  .nav-link:hover {
    background: var(--hover);
    color: var(--text);
  }
  .nav-link.active {
    background: var(--primary-light);
    color: var(--primary);
    font-weight: 500;
  }
  .nav-icon {
    flex-shrink: 0;
    width: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .nav-label {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .content {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }
  @media (max-width: 768px) {
    .brand-name {
      display: none;
    }
    .user-name {
      display: none;
    }
    .sidebar-backdrop {
      position: fixed;
      top: 56px;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.3);
      z-index: 99;
    }
    .sidebar {
      position: fixed;
      top: 56px;
      left: -200px;
      bottom: 0;
      z-index: 100;
      transition: left 0.2s ease;
    }
    .sidebar.mobile-open {
      left: 0;
    }
    .sidebar.collapsed {
      width: 200px;
    }
  }
</style>
