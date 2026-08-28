<script lang="ts">
  import Icon from './Icon.svelte';

  interface Props {
    message: string;
    retry?: () => void;
  }

  let { message, retry }: Props = $props();
</script>

<div class="error-banner">
  <div class="error-icon">
    <Icon name="logout" size={18} />
  </div>
  <span class="error-text">{message}</span>
  {#if retry}
    <button class="retry-btn" onclick={retry}>
      <Icon name="bolt" size={14} />
      Retry
    </button>
  {/if}
</div>

<style>
  .error-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    background: var(--danger-bg);
    border: 1px solid var(--danger-border);
    border-radius: 10px;
    color: var(--danger);
  }
  .error-icon {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--danger-bg);
    border-radius: 50%;
    color: var(--danger);
  }
  .error-text {
    flex: 1;
    font-size: 14px;
    font-weight: 500;
  }
  .retry-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border: 1px solid var(--danger-border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--danger);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s;
  }
  .retry-btn:hover {
    background: var(--danger-bg);
  }
</style>
