<script lang="ts">
  import { getTileList, getSelectedTile, setSelectedTile, type TileProvider } from '$lib/map/tiles';

  interface Props {
    onTileChange: (provider: TileProvider) => void;
  }

  let { onTileChange }: Props = $props();

  let isOpen = $state(false);
  let current = $state(getSelectedTile());
  const tiles = getTileList();

  function select(tile: TileProvider) {
    current = tile;
    setSelectedTile(tile.key);
    onTileChange(tile);
    isOpen = false;
  }

  function toggle() {
    isOpen = !isOpen;
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest('.tile-selector')) {
      isOpen = false;
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="tile-selector">
  <button class="tile-toggle" onclick={toggle} title="Change map style">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z"/>
    </svg>
    <span>{current.name}</span>
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" class="chevron" class:open={isOpen}>
      <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>
    </svg>
  </button>
  {#if isOpen}
    <div class="tile-dropdown">
      {#each tiles as tile}
        <button
          class="tile-option"
          class:active={current.key === tile.key}
          onclick={() => select(tile)}
        >
          {tile.name}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .tile-selector {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1000;
  }
  .tile-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: var(--surface, #fff);
    border: 0.5px solid var(--border, #e2e8f0);
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: var(--text, #1e293b);
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
    font-family: var(--font-sans, system-ui);
  }
  .tile-toggle:hover {
    background: var(--hover, #f1f5f9);
  }
  .chevron {
    transition: transform 0.15s;
  }
  .chevron.open {
    transform: rotate(180deg);
  }
  .tile-dropdown {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    background: var(--surface, #fff);
    border: 0.5px solid var(--border, #e2e8f0);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    overflow: hidden;
    min-width: 140px;
  }
  .tile-option {
    display: block;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    color: var(--text, #1e293b);
    text-align: left;
    font-family: var(--font-sans, system-ui);
  }
  .tile-option:hover {
    background: var(--hover, #f1f5f9);
  }
  .tile-option.active {
    color: #3b82f6;
    font-weight: 500;
  }
</style>
