<script lang="ts">
  interface Props {
    label: string;
    onPrev: () => void;
    onNext: () => void;
  }

  let { label, onPrev, onNext }: Props = $props();
</script>

<div class="period-nav">
  <button class="nav-btn" onclick={onPrev}>‹</button>
  <span class="label">{label}</span>
  <button class="nav-btn" onclick={onNext}>›</button>
</div>

<style>
  .period-nav {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .nav-btn {
    width: 32px;
    height: 32px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .nav-btn:hover {
    background: var(--hover);
  }
  .label {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    min-width: 120px;
    text-align: center;
  }
</style>
