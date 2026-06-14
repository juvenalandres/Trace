<script lang="ts">
  import Icon from './Icon.svelte';

  interface Props {
    icon?: string;
    message: string;
    action?: string;
    onAction?: () => void;
  }

  let { icon = 'dashboard', message, action, onAction }: Props = $props();
</script>

<div class="empty-state">
  <div class="empty-icon">
    <Icon name={icon} size={40} />
  </div>
  <p class="empty-message">{message}</p>
  {#if action && onAction}
    <button class="empty-action" onclick={onAction}>{action}</button>
  {/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 20px;
    text-align: center;
  }
  .empty-icon {
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
    border-radius: 50%;
    color: var(--text-secondary);
    margin-bottom: 16px;
  }
  .empty-message {
    font-size: 15px;
    color: var(--text-secondary);
    margin: 0 0 16px 0;
    max-width: 360px;
    line-height: 1.5;
  }
  .empty-action {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
  }
  .empty-action:hover {
    background: var(--hover);
  }
</style>
