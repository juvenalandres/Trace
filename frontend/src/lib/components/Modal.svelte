<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    open: boolean;
    title?: string;
    onClose: () => void;
    children: Snippet;
  }

  let { open, title = '', onClose, children }: Props = $props();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }

  function handleBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div class="backdrop" onclick={handleBackdrop} role="dialog" aria-modal="true">
    <div class="modal">
      {#if title}
        <div class="header">
          <h2>{title}</h2>
          <button class="close-btn" onclick={onClose}>×</button>
        </div>
      {/if}
      <div class="body">
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .modal {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    min-width: 400px;
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 0.5px solid var(--border);
  }
  h2 {
    margin: 0;
    font-size: var(--font-size-xl, 18px);
    font-weight: var(--font-weight-medium, 500);
    font-family: var(--font-sans);
  }
  .close-btn {
    width: 32px;
    height: 32px;
    border: none;
    background: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-secondary);
    border-radius: 6px;
    font-family: var(--font-sans);
  }
  .close-btn:hover {
    background: var(--hover);
  }
  .body {
    padding: 20px;
    font-family: var(--font-sans);
  }
</style>
