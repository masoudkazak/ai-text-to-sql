<script>
  import { onMount } from 'svelte';
  import { apiRequest } from './lib/api.js';

  const roles = ['viewer', 'analyst', 'developer', 'restricted', 'admin'];

  let booting = true;
  let loading = false;
  let user = null;
  let usage = null;
  let activeTab = 'query';

  let email = '';
  let password = '';
  let registerName = '';
  let registerEmail = '';
  let registerPassword = '';

  let queryText = '';
  let queryResult = null;
  let requestId = '';
  let requestResult = null;

  let approvals = [];
  let approvalLoading = false;

  let auditLogs = [];
  let auditLoading = false;

  let users = [];
  let usersLoading = false;
  let newUser = {
    name: '',
    email: '',
    password: '',
    role: 'viewer',
    daily_query_limit: 100,
    allowed_tables: '',
  };

  let alert = { type: '', text: '' };

  const queryHints = [
    'Show me all users',
    'Show me 10 rows of travel planner',
    'Count the total number of bookings',
    'List all destinations with their budgets',
  ];

  function showAlert(type, text) {
    alert = { type, text };
  }

  function insertHint(hint) {
    queryText = hint;
  }

  function clearAlert() {
    alert = { type: '', text: '' };
  }

  function hasRole(...accepted) {
    return user && accepted.includes(user.role);
  }

  async function refreshSession() {
    const me = await apiRequest('GET', '/api/v1/auth/me');
    if (!me.ok) {
      user = null;
      usage = null;
      return false;
    }
    user = me.data;
    await refreshUsage();
    return true;
  }

  async function refreshUsage() {
    if (!user) return;
    const summary = await apiRequest('GET', '/api/v1/auth/usage-summary');
    if (summary.ok) {
      usage = summary.data;
    }
  }

  async function runAuth(path, payload, successText) {
    clearAlert();
    loading = true;
    try {
      const result = await apiRequest('POST', path, payload ? { body: payload } : {});
      if (!result.ok) {
        showAlert('error', result.error);
        return;
      }
      user = result.data;
      await refreshUsage();
      activeTab = 'query';
      showAlert('success', successText);
    } finally {
      loading = false;
    }
  }

  async function login() {
    await runAuth('/api/v1/auth/login', { email, password }, 'Logged in successfully.');
  }

  async function register() {
    await runAuth(
      '/api/v1/auth/register',
      { name: registerName, email: registerEmail, password: registerPassword },
      'Viewer account created and logged in.'
    );
  }

  async function demoLogin() {
    await runAuth('/api/v1/auth/demo', null, 'Demo account created and logged in.');
  }

  async function logout() {
    clearAlert();
    await apiRequest('POST', '/api/v1/auth/logout');
    user = null;
    usage = null;
    queryResult = null;
    requestResult = null;
    showAlert('success', 'Logged out.');
  }

  async function submitQuery() {
    if (!queryText.trim()) return;
    clearAlert();
    loading = true;
    queryResult = null;
    try {
      const result = await apiRequest('POST', '/api/v1/query', { body: { text: queryText } });
      if (!result.ok) {
        if (result.status === 401 || result.status === 403) {
          user = null;
        }
        showAlert('error', result.error);
        return;
      }
      queryResult = result.data;
      showAlert('success', 'Query request processed.');
      await refreshUsage();
    } finally {
      loading = false;
    }
  }

  async function checkRequest() {
    const id = Number(requestId);
    if (!id) return;
    clearAlert();
    loading = true;
    requestResult = null;
    try {
      const result = await apiRequest('GET', `/api/v1/query/${id}`);
      if (!result.ok) {
        showAlert('error', result.error);
        return;
      }
      requestResult = result.data;
    } finally {
      loading = false;
    }
  }

  async function loadApprovals() {
    if (!hasRole('admin')) return;
    approvalLoading = true;
    const result = await apiRequest('GET', '/api/v1/approvals/pending');
    approvals = result.ok ? result.data : [];
    approvalLoading = false;
  }

  async function decideApproval(queryRequestId, approve) {
    clearAlert();
    const result = await apiRequest('POST', '/api/v1/approvals/decision', {
      body: { query_request_id: queryRequestId, approve, comment: 'Reviewed from Svelte UI' },
    });
    if (!result.ok) {
      showAlert('error', result.error);
      return;
    }
    showAlert('success', `Decision saved for request #${queryRequestId}.`);
    await loadApprovals();
  }

  async function loadAudit() {
    if (!hasRole('admin', 'developer')) return;
    auditLoading = true;
    const result = await apiRequest('GET', '/api/v1/audit');
    auditLogs = result.ok ? result.data : [];
    auditLoading = false;
  }

  async function loadUsers() {
    if (!hasRole('admin')) return;
    usersLoading = true;
    const result = await apiRequest('GET', '/api/v1/users');
    users = result.ok ? result.data : [];
    usersLoading = false;
  }

  async function createUser() {
    clearAlert();
    const payload = {
      name: newUser.name.trim(),
      email: newUser.email.trim(),
      password: newUser.password,
      role: newUser.role,
      daily_query_limit: Number(newUser.daily_query_limit),
      allowed_tables: newUser.allowed_tables
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean),
    };

    const result = await apiRequest('POST', '/api/v1/users', { body: payload });
    if (!result.ok) {
      showAlert('error', result.error);
      return;
    }

    showAlert('success', 'User created successfully.');
    newUser = {
      name: '',
      email: '',
      password: '',
      role: 'viewer',
      daily_query_limit: 100,
      allowed_tables: '',
    };
    await loadUsers();
  }

  function isActiveTab(tab) {
    return activeTab === tab ? 'active' : '';
  }

  function visibleTabs() {
    const tabs = [{ key: 'query', label: 'Query Console' }];
    if (hasRole('admin')) tabs.push({ key: 'approvals', label: 'Approvals' });
    if (hasRole('admin', 'developer')) tabs.push({ key: 'audit', label: 'Audit Logs' });
    if (hasRole('admin')) tabs.push({ key: 'users', label: 'Users' });
    return tabs;
  }

  $: if (activeTab === 'approvals' && user?.role === 'admin') {
    loadApprovals();
  }
  $: if (activeTab === 'audit' && (user?.role === 'admin' || user?.role === 'developer')) {
    loadAudit();
  }
  $: if (activeTab === 'users' && user?.role === 'admin') {
    loadUsers();
  }

  onMount(async () => {
    await refreshSession();
    booting = false;
  });
</script>

<div class="app-shell">
  <div class="ambient one"></div>
  <div class="ambient two"></div>

  <main class="panel">
    <header class="topbar">
      <div>
        <p class="eyebrow">Natural Language Database Gateway</p>
        <h1>Governed SQL Workspace</h1>
      </div>
      {#if user}
        <button class="btn ghost" on:click={logout}>Logout</button>
      {/if}
    </header>

    {#if alert.text}
      <section class="alert {alert.type}">{alert.text}</section>
    {/if}

    {#if booting}
      <section class="card">Loading session...</section>
    {:else if !user}
      <section class="auth-grid">
        <article class="card hero">
          <h2>AI-to-SQL with Governance</h2>
          <p>
            Secure gateway for natural language querying, approval workflows, and auditability.
          </p>
          <button class="btn accent" disabled={loading} on:click={demoLogin}>Try Demo Account</button>
        </article>

        <article class="card">
          <h3>Login</h3>
          <label for="login-email">Email</label>
          <input id="login-email" bind:value={email} type="email" placeholder="admin@example.com" />
          <label for="login-password">Password</label>
          <input id="login-password" bind:value={password} type="password" placeholder="••••••••" />
          <button class="btn" disabled={loading} on:click={login}>Login</button>
        </article>

        <article class="card">
          <h3>Register (Viewer)</h3>
          <label for="register-name">Name</label>
          <input id="register-name" bind:value={registerName} type="text" placeholder="Your name" />
          <label for="register-email">Email</label>
          <input id="register-email" bind:value={registerEmail} type="email" placeholder="you@example.com" />
          <label for="register-password">Password</label>
          <input id="register-password" bind:value={registerPassword} type="password" placeholder="Choose a password" />
          <button class="btn" disabled={loading} on:click={register}>Create Viewer Account</button>
        </article>
      </section>
    {:else}
      <section class="user-bar">
        <div>
          <strong>{user.email}</strong>
          <span class="pill">{user.role}</span>
        </div>
        {#if usage}
          <div class="usage">
            <span>Global: {usage.global_remaining}/{usage.global_daily_limit}</span>
            <span>Your Limit: {usage.user_remaining}/{usage.user_daily_limit}</span>
          </div>
        {/if}
      </section>

      {#if usage?.available_tables?.length}
        <section class="table-list card">
          <h4>Available Tables</h4>
          <p>{usage.available_tables.join(', ')}</p>
        </section>
      {/if}

      <nav class="tabs">
        {#each visibleTabs() as tab}
          <button class={isActiveTab(tab.key)} on:click={() => (activeTab = tab.key)}>{tab.label}</button>
        {/each}
      </nav>

      {#if activeTab === 'query'}
        <section class="card">
          <h3>Query Console</h3>
          <label for="query-text">Natural language request</label>
          <textarea id="query-text" bind:value={queryText} rows="7" placeholder="Show top 10 destinations by budget in 2024"></textarea>
          <div class="hints-container">
            <p class="hints-label">Quick Examples:</p>
            <div class="hints">
              {#each queryHints as hint}
                <button class="hint-btn" on:click={() => insertHint(hint)}>{hint}</button>
              {/each}
            </div>
          </div>
          <button class="btn accent" disabled={loading} on:click={submitQuery}>Submit Query</button>

          {#if queryResult}
            <div class="result-block">
              <h4>Generated SQL</h4>
              <pre>{queryResult.generated_sql}</pre>
              <p>
                Decision: <strong>{queryResult.governance.decision}</strong>
                ({queryResult.governance.reason})
              </p>
              {#if queryResult.result}
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {#each Object.keys(queryResult.result[0] || {}) as col}
                          <th>{col}</th>
                        {/each}
                      </tr>
                    </thead>
                    <tbody>
                      {#each queryResult.result as row}
                        <tr>
                          {#each Object.values(row) as value}
                            <td>{String(value)}</td>
                          {/each}
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}
            </div>
          {/if}
        </section>

        <section class="card">
          <h3>Check Existing Request</h3>
          <label for="request-id">Query Request ID</label>
          <input id="request-id" type="number" min="1" bind:value={requestId} />
          <button class="btn" disabled={loading} on:click={checkRequest}>Check Status / Fetch Result</button>

          {#if requestResult}
            <div class="result-block">
              <p>Status: <strong>{requestResult.status}</strong></p>
              <pre>{requestResult.generated_sql}</pre>
              {#if requestResult.result}
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {#each Object.keys(requestResult.result[0] || {}) as col}
                          <th>{col}</th>
                        {/each}
                      </tr>
                    </thead>
                    <tbody>
                      {#each requestResult.result as row}
                        <tr>
                          {#each Object.values(row) as value}
                            <td>{String(value)}</td>
                          {/each}
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}
            </div>
          {/if}
        </section>
      {/if}

      {#if activeTab === 'approvals' && hasRole('admin')}
        <section class="card">
          <h3>Pending Approvals</h3>
          {#if approvalLoading}
            <p>Loading approvals...</p>
          {:else if approvals.length === 0}
            <p>No pending approvals.</p>
          {:else}
            <div class="list">
              {#each approvals as row}
                <article class="list-item">
                  <div>
                    <strong>Request #{row.query_request_id}</strong>
                    <p>Status: {row.status}</p>
                  </div>
                  <div class="actions">
                    <button class="btn success" on:click={() => decideApproval(row.query_request_id, true)}>Approve</button>
                    <button class="btn danger" on:click={() => decideApproval(row.query_request_id, false)}>Reject</button>
                  </div>
                </article>
              {/each}
            </div>
          {/if}
        </section>
      {/if}

      {#if activeTab === 'audit' && hasRole('admin', 'developer')}
        <section class="card">
          <h3>Audit Logs</h3>
          {#if auditLoading}
            <p>Loading logs...</p>
          {:else if auditLogs.length === 0}
            <p>No logs found.</p>
          {:else}
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>User</th>
                    <th>Event</th>
                    <th>Timestamp</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {#each auditLogs as row}
                    <tr>
                      <td>{row.id}</td>
                      <td>{row.user_id}</td>
                      <td>{row.event_type}</td>
                      <td>{row.timestamp}</td>
                      <td>{row.ip_address || '-'}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>
      {/if}

      {#if activeTab === 'users' && hasRole('admin')}
        <section class="card">
          <h3>Create User</h3>
          <div class="form-grid">
            <div>
              <label for="new-user-name">Name</label>
              <input id="new-user-name" bind:value={newUser.name} type="text" />
            </div>
            <div>
              <label for="new-user-email">Email</label>
              <input id="new-user-email" bind:value={newUser.email} type="email" />
            </div>
            <div>
              <label for="new-user-password">Password</label>
              <input id="new-user-password" bind:value={newUser.password} type="password" />
            </div>
            <div>
              <label for="new-user-role">Role</label>
              <select id="new-user-role" bind:value={newUser.role}>
                {#each roles as role}
                  <option value={role}>{role}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="new-user-limit">Daily Query Limit</label>
              <input id="new-user-limit" bind:value={newUser.daily_query_limit} type="number" min="0" />
            </div>
            <div>
              <label for="new-user-tables">Allowed Tables (comma separated)</label>
              <input id="new-user-tables" bind:value={newUser.allowed_tables} type="text" placeholder="travel_planner, bookings" />
            </div>
          </div>
          <button class="btn accent" on:click={createUser}>Create User</button>
        </section>

        <section class="card">
          <h3>Users List</h3>
          {#if usersLoading}
            <p>Loading users...</p>
          {:else if users.length === 0}
            <p>No users found.</p>
          {:else}
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Limit</th>
                    <th>Today</th>
                    <th>Active</th>
                  </tr>
                </thead>
                <tbody>
                  {#each users as item}
                    <tr>
                      <td>{item.id}</td>
                      <td>{item.name}</td>
                      <td>{item.email}</td>
                      <td>{item.role}</td>
                      <td>{item.daily_query_limit}</td>
                      <td>{item.queries_today}</td>
                      <td>{item.is_active ? 'yes' : 'no'}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>
      {/if}
    {/if}
  </main>
</div>
