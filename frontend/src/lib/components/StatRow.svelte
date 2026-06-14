<script lang="ts">
  interface Props {
    label: string;
    value: string | number;
    unit?: string;
  }

  let { label, value, unit = '' }: Props = $props();
</script>

<div class="stat-row">
  <span class="stat-label">{label}</span>
  <span class="stat-value">{value}{#if unit}<span class="stat-unit">{unit}</span>{/if}</span>
</div>

<style>
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .stat-label {
    font-size: 13px;
    color: var(--text-secondary);
  }
  .stat-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }
  .stat-unit {
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-left: 3px;
  }
</style>
