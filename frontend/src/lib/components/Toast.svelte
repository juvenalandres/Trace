<script lang="ts">
  import Icon from './Icon.svelte';

  interface ToastItem {
    id: number;
    message: string;
    type: 'success' | 'error' | 'info';
  }

  interface Props {
    toasts: ToastItem[];
    ondismiss?: (id: number) => void;
  }

  let { toasts, ondismiss }: Props = $props();

  function iconFor(type: string): string {
    if (type === 'success') return 'check';
    if (type === 'error') return 'logout';
    return 'bolt';
  }

  function colorFor(type: string): { bg: string; border: string; text: string; iconBg: string; iconColor: string } {
    if (type === 'success') return { bg: '#f0fdf4', border: '#bbf7d0', text: '#166534', iconBg: '#dcfce7', iconColor: '#16a34a' };
    if (type === 'error') return { bg: '#fef2f2', border: '#fecaca', text: '#991b1b', iconBg: '#fee2e2', iconColor: '#dc2626' };
    return { bg: '#eff6ff', border: '#bfdbfe', text: '#1e40af', iconBg: '#dbeafe', iconColor: '#2563eb' };
  }
</script>

<div class="toast-container">
  {#each toasts as toast (toast.id)}
    {@const c = colorFor(toast.type)}
    <div
      class="toast"
      style="background: {c.bg}; border-color: {c.border}; color: {c.text}"
      role="alert"
    >
      <div class="toast-icon" style="background: {c.iconBg}; color: {c.iconColor}">
        <Icon name={iconFor(toast.type)} size={16} />
      </div>
      <span class="toast-message">{toast.message}</span>
      <button class="toast-close" onclick={() => ondismiss?.(toast.id)} style="color: {c.text}">
        &times;
      </button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
  }
  .toast {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border: 1px solid;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    pointer-events: auto;
    animation: slideIn 0.2s ease-out;
    max-width: 380px;
  }
  .toast-icon {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
  .toast-message {
    flex: 1;
  }
  .toast-close {
    flex-shrink: 0;
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    opacity: 0.6;
    line-height: 1;
    padding: 0 2px;
  }
  .toast-close:hover {
    opacity: 1;
  }
  @keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
</style>
