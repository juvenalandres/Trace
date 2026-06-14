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
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 10px;
    color: #991b1b;
  }
  .error-icon {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fee2e2;
    border-radius: 50%;
    color: #dc2626;
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
    border: 1px solid #fecaca;
    border-radius: 6px;
    background: white;
    color: #dc2626;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s;
  }
  .retry-btn:hover {
    background: #fee2e2;
  }
</style>
