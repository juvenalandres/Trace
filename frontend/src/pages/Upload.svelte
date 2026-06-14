<script lang="ts">
  import { onMount } from 'svelte';
  import { activitiesApi, gearApi } from '$lib/api/types';
  import type { Activity, Gear } from '$lib/api/types';
  import ErrorBanner from '$lib/components/ErrorBanner.svelte';

  interface Props {
    onUploaded?: (activity: Activity) => void;
  }

  let { onUploaded }: Props = $props();

  let dragging = $state(false);
  let uploading = $state(false);
  let error = $state('');
  let fileInput: HTMLInputElement;
  let gearList = $state<Gear[]>([]);
  let selectedGearId = $state<number | null>(null);

  onMount(async () => {
    try {
      const all = await gearApi.list();
      gearList = all.filter(g => !g.retired);
    } catch {
      // silently ignore — gear is optional
    }
  });

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    dragging = true;
  }

  function handleDragLeave() {
    dragging = false;
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragging = false;
    const file = e.dataTransfer?.files[0];
    if (file) uploadFile(file);
  }

  function handleFileSelect(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) uploadFile(file);
  }

  async function uploadFile(file: File) {
    if (!file.name.endsWith('.gpx') && !file.name.endsWith('.fit')) {
      error = 'Please select a GPX or FIT file';
      return;
    }

    uploading = true;
    error = '';

    try {
      const activity = await activitiesApi.upload(file, selectedGearId ?? undefined);
      onUploaded?.(activity);
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Upload failed';
    } finally {
      uploading = false;
    }
  }
</script>

<div class="upload-page">
  <h1>Upload Activity</h1>

  <div
    class="drop-zone"
    class:dragging
    class:uploading
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
    onclick={() => fileInput?.click()}
    role="button"
    tabindex="0"
    onkeydown={(e) => { if (e.key === 'Enter') fileInput?.click(); }}
  >
    {#if uploading}
      <div class="spinner"></div>
      <p>Uploading...</p>
    {:else}
      <div class="icon">📁</div>
      <p>Drag & drop a GPX or FIT file here, or click to select</p>
      <span class="hint">Supports .gpx and .fit files from any device</span>
    {/if}
  </div>

  <input
    bind:this={fileInput}
    type="file"
    accept=".gpx,.fit"
    onchange={handleFileSelect}
    hidden
  />

  {#if gearList.length > 0}
    <div class="gear-select">
      <label for="gear-dropdown">Gear used</label>
      <select id="gear-dropdown" bind:value={selectedGearId}>
        <option value={null}>None</option>
        {#each gearList as g}
          <option value={g.id}>{g.name}</option>
        {/each}
      </select>
    </div>
  {/if}

  {#if error}
    <div style="margin-top: 16px;">
      <ErrorBanner message={error} />
    </div>
  {/if}
</div>

<style>
  .upload-page {
    max-width: 600px;
    margin: 0 auto;
    padding: 24px;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 24px;
  }
  .drop-zone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 60px 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    background: var(--surface);
  }
  .drop-zone:hover, .drop-zone.dragging {
    border-color: var(--primary);
    background: var(--primary-light);
  }
  .drop-zone.uploading {
    opacity: 0.6;
    pointer-events: none;
  }
  .icon {
    font-size: 48px;
    margin-bottom: 12px;
  }
  p {
    font-size: 16px;
    color: var(--text);
    margin: 0 0 8px 0;
  }
  .hint {
    font-size: 13px;
    color: var(--text-secondary);
  }
  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 12px;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  .gear-select {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .gear-select label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
  }
  .gear-select select {
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
    font-family: inherit;
  }
  .gear-select select:focus {
    outline: none;
    border-color: var(--primary);
  }
  @media (max-width: 768px) {
    .upload-page { padding: 16px; }
    h1 { font-size: 22px; }
    .drop-zone { padding: 40px 16px; }
  }
</style>
