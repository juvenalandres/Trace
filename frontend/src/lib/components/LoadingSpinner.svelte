<script lang="ts">
  interface Props {
    message?: string;
    size?: 'sm' | 'md' | 'lg';
  }

  let { message = 'Loading...', size = 'md' }: Props = $props();
</script>

<div class="loading-spinner" class:sm={size === 'sm'} class:lg={size === 'lg'}>
  <div class="spinner"></div>
  {#if message}
    <p class="message">{message}</p>
  {/if}
</div>

<style>
  .loading-spinner {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 20px;
    gap: 16px;
  }
  .loading-spinner.sm {
    padding: 24px 16px;
    gap: 10px;
  }
  .loading-spinner.lg {
    padding: 80px 20px;
    gap: 20px;
  }
  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .sm .spinner {
    width: 20px;
    height: 20px;
    border-width: 2px;
  }
  .lg .spinner {
    width: 40px;
    height: 40px;
  }
  .message {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
