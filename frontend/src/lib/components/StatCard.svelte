<script lang="ts">
  import Icon from './Icon.svelte';

  interface Props {
    label: string;
    value: string | number;
    unit?: string;
    icon?: string;
    subtitle?: string;
    color?: string;
    bg?: string;
  }

  let { label, value, unit = '', icon = '', subtitle = '', color = '', bg = '' }: Props = $props();
</script>

<div class="stat-card">
  {#if icon}
    <div class="stat-icon" style={color && bg ? `background: ${bg}; color: ${color}` : ''}>
      <Icon name={icon} size={18} />
    </div>
  {/if}
  <div class="stat-label">{label}</div>
  <div class="stat-value">{value}{#if unit}<span class="stat-unit">{unit}</span>{/if}</div>
  {#if subtitle}
    <div class="stat-subtitle">{subtitle}</div>
  {/if}
</div>

<style>
  .stat-card {
    background: var(--card-bg, var(--surface));
    border: var(--card-border, 0.5px solid var(--border));
    border-radius: var(--card-radius, 10px);
    padding: var(--card-padding, 16px);
  }
  .stat-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: color-mix(in srgb, var(--primary) 12%, transparent);
    color: var(--primary);
    margin-bottom: 10px;
  }
  .stat-label {
    font-size: var(--font-size-xs, 11px);
    font-weight: var(--font-weight-medium, 500);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }
  .stat-value {
    font-size: var(--font-size-3xl, 26px);
    font-weight: var(--font-weight-medium, 500);
    color: var(--text);
    line-height: 1.1;
  }
  .stat-unit {
    font-size: var(--font-size-base, 13px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-left: 4px;
  }
  .stat-subtitle {
    font-size: var(--font-size-sm, 12px);
    font-weight: var(--font-weight-regular, 400);
    color: var(--text-secondary);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
