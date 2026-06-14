<script lang="ts">
  import { authApi } from '$lib/api/types';
  import { setToken } from '$lib/stores/auth';

  interface Props {
    onLogin: () => void;
  }

  let { onLogin }: Props = $props();

  let email = $state('');
  let password = $state('');
  let name = $state('');
  let isRegister = $state(false);
  let error = $state('');
  let loading = $state(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    loading = true;
    error = '';

    try {
      const tokens = isRegister
        ? await authApi.register(email, password, name || undefined)
        : await authApi.login(email, password);

      setToken(tokens.access_token);
      onLogin();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Authentication failed';
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-page">
  <div class="login-card">
    <h1>Trace</h1>
    <p class="subtitle">Activity tracking & training platform</p>

    <form onsubmit={handleSubmit}>
      {#if isRegister}
        <div class="field">
          <label for="name">Name</label>
          <input id="name" type="text" bind:value={name} placeholder="Your name" />
        </div>
      {/if}

      <div class="field">
        <label for="email">Email</label>
        <input id="email" type="email" bind:value={email} placeholder="you@example.com" required />
      </div>

      <div class="field">
        <label for="password">Password</label>
        <input id="password" type="password" bind:value={password} placeholder="Password" required />
      </div>

      {#if error}
        <p class="error">{error}</p>
      {/if}

      <button type="submit" class="submit-btn" disabled={loading}>
        {loading ? 'Loading...' : isRegister ? 'Register' : 'Login'}
      </button>
    </form>

    <button class="toggle-btn" onclick={() => isRegister = !isRegister}>
      {isRegister ? 'Already have an account? Login' : "Don't have an account? Register"}
    </button>
  </div>
</div>

<style>
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
  }
  .login-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 40px;
    width: 360px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }
  h1 {
    text-align: center;
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 4px 0;
    color: var(--primary);
  }
  .subtitle {
    text-align: center;
    color: var(--text-secondary);
    font-size: 14px;
    margin: 0 0 24px 0;
  }
  .field {
    margin-bottom: 16px;
  }
  label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--text);
  }
  input {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
    box-sizing: border-box;
  }
  input:focus {
    outline: none;
    border-color: var(--primary);
  }
  .submit-btn {
    width: 100%;
    padding: 10px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 8px;
  }
  .submit-btn:hover {
    opacity: 0.9;
  }
  .submit-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .toggle-btn {
    width: 100%;
    padding: 8px;
    background: none;
    border: none;
    color: var(--primary);
    font-size: 13px;
    cursor: pointer;
    margin-top: 12px;
  }
  .error {
    color: #ef4444;
    font-size: 13px;
    margin: 8px 0;
  }
</style>
