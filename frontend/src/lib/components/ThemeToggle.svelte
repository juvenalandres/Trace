<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';

  let dark = $state(false);

  onMount(() => {
    const saved = localStorage.getItem('trace_theme');
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      dark = true;
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  });

  function toggle() {
    dark = !dark;
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    localStorage.setItem('trace_theme', dark ? 'dark' : 'light');
  }
</script>

<button class="theme-toggle" onclick={toggle} title={dark ? 'Switch to light mode' : 'Switch to dark mode'}>
  <Icon name={dark ? 'sun' : 'moon'} size={18} />
</button>

<style>
  .theme-toggle {
    width: 36px;
    height: 36px;
    border: none;
    background: none;
    color: var(--text-secondary);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background var(--transition-fast), color var(--transition-fast);
  }
  .theme-toggle:hover {
    background: var(--hover);
    color: var(--text);
  }
</style>
