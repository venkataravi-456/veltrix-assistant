# Clean, Spec-Exact Section 9.1 Web Interface for Veltrix PeopleOps Assistant
# Fully implements the exact Input and Output contract specified in TASK.pdf (Section 9.1)

CHAT_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Veltrix PeopleOps Assistant - Section 9.1 Contract</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --primary: #10b981;
      --primary-hover: #059669;
      --blue: #3b82f6;
      --purple: #8b5cf6;
      --pink: #ec4899;
      --amber: #f59e0b;
      --red: #ef4444;
      --gray: #6b7280;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Top Navigation Header */
    header {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 32px;
      height: 32px;
      background: var(--primary);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-weight: 700;
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }
    .brand-sub {
      font-size: 11px;
      color: var(--text-muted);
    }

    .header-badges {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .status-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
    }
    .spec-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #60a5fa;
    }

    /* Main Container: 2-Column Spec Layout */
    .container {
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 28px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      flex: 1;
    }
    @media (max-width: 1024px) {
      .container { grid-template-columns: 1fr; }
    }

    /* Section Cards */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .card-header {
      padding: 14px 18px;
      background: #1e293b;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .card-title {
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .title-in { color: #60a5fa; }
    .title-out { color: #34d399; }

    .card-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
    }

    /* Form Fields */
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .form-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .form-label code {
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
      font-size: 11px;
    }

    select, input[type="text"], textarea {
      width: 100%;
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-family: inherit;
      outline: none;
      transition: border 0.15s;
    }
    select:focus, input[type="text"]:focus, textarea:focus {
      border-color: var(--primary);
    }

    optgroup {
      background: #1e293b;
      color: var(--primary);
      font-weight: 700;
    }
    option {
      background: #0f172a;
      color: #fff;
    }

    .session-input-row {
      display: flex;
      gap: 8px;
    }
    .btn-small {
      padding: 8px 12px;
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      border-radius: 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }
    .btn-small:hover {
      background: #334155;
      color: #fff;
    }

    /* Test Scenario Prompts */
    .scenarios-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-top: 4px;
    }
    .scenarios-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .scenario-btn {
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 500;
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: #e2e8f0;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .scenario-btn:hover {
      background: #334155;
      border-color: #64748b;
      color: #fff;
    }

    /* Submit Button */
    .btn-submit {
      padding: 12px;
      background: var(--primary);
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: background 0.15s;
      margin-top: 6px;
    }
    .btn-submit:hover {
      background: var(--primary-hover);
    }
    .btn-submit:disabled {
      background: #374151;
      color: #9ca3af;
      cursor: not-allowed;
    }

    /* Error Code Buttons (Section 9.1 Spec) */
    .error-tests {
      padding-top: 12px;
      border-top: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .error-btns {
      display: flex;
      gap: 8px;
    }
    .btn-err {
      flex: 1;
      padding: 6px 10px;
      background: #1e293b;
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-err:hover {
      background: rgba(239, 68, 68, 0.2);
      border-color: var(--red);
    }

    /* Output Column Elements */
    .status-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
    }
    .status-200 { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .status-err { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .status-idle { background: #1f2937; color: var(--text-muted); }

    .output-section {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .output-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .output-value-text {
      font-size: 13.5px;
      line-height: 1.5;
      color: #f8fafc;
      white-space: pre-wrap;
    }

    /* Route Badges (Section 8.1) */
    .route-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      width: fit-content;
    }
    .route-rag { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .route-tool { background: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.4); }
    .route-hybrid { background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.4); }
    .route-clarify { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .route-no_answer { background: rgba(107, 114, 128, 0.2); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.4); }
    .route-refuse { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }

    /* Tables for Citations and Tool Calls */
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 4px;
    }
    .data-table th, .data-table td {
      border: 1px solid var(--card-border);
      padding: 6px 10px;
      text-align: left;
    }
    .data-table th {
      background: #1e293b;
      color: var(--text-muted);
      font-weight: 600;
      font-size: 11px;
    }
    .data-table td code {
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
    }

    /* Section 8.2 Confirmation Banner */
    .confirm-box {
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .confirm-text {
      font-size: 12px;
      color: #fbbf24;
      font-weight: 600;
    }
    .confirm-actions {
      display: flex;
      gap: 8px;
    }
    .btn-action-confirm {
      padding: 6px 12px;
      background: var(--primary);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-action-cancel {
      padding: 6px 12px;
      background: #374151;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    /* Full Raw JSON Box */
    .json-box {
      background: #060911;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #7dd3fc;
      overflow-x: auto;
      white-space: pre;
      line-height: 1.5;
      max-height: 280px;
      overflow-y: auto;
    }

    /* Copy Button */
    .copy-btn {
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
      cursor: pointer;
    }
    .copy-btn:hover { color: #fff; background: #334155; }
  </style>
</head>
<body>

  <!-- Top Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">V</div>
      <div>
        <div class="brand-title">Veltrix PeopleOps Assistant</div>
        <div class="brand-sub">AI/ML Engineer Assessment &bull; Ref Date: 2026-09-15</div>
      </div>
    </div>
    <div class="header-badges">
      <div class="status-pill" id="healthPill">
        <span class="status-dot"></span>
        GET /health: 200 OK
      </div>
      <div class="spec-pill">
        Section 9.1 API Contract
      </div>
    </div>
  </header>

  <!-- Main Container: Section 9.1 Input & Output -->
  <div class="container">

    <!-- LEFT COLUMN: SECTION 9.1 REQUEST INPUT -->
    <div class="card">
      <div class="card-header">
        <div class="card-title title-in">
          <span>1. Section 9.1 Request Input</span>
        </div>
        <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#60a5fa;">POST /chat</span>
      </div>

      <div class="card-body">
        <!-- Header 1: X-Employee-Id -->
        <div class="form-group">
          <label class="form-label">
            <span>Header: X-Employee-Id (required)</span>
            <code>X-Employee-Id</code>
          </label>
          <select id="empSelect" onchange="onEmployeeChange()">
            <optgroup label="── 🇮🇳 India (IN) ──">
              <option value="E2004" selected>E2004 - Sneha Kulkarni (Employee, IN - L3)</option>
              <option value="E2001">E2001 - Arjun Rao (Manager, IN - L7)</option>
              <option value="E2002">E2002 - Divya Menon (Manager, IN - L6)</option>
              <option value="E2003">E2003 - Karthik Iyer (Manager, IN - L5)</option>
              <option value="E2005">E2005 - Vikram Shetty (Employee, IN - L4)</option>
              <option value="E2006">E2006 - Ananya Gowda (Employee, IN - L2)</option>
              <option value="E2007">E2007 - Rahul Nair (Employee, IN - L4)</option>
              <option value="E2008">E2008 - Priya Sharma (Employee, IN - L3)</option>
              <option value="E2009">E2009 - Imran Qureshi (Employee, IN - L5)</option>
              <option value="E2010">E2010 - Lakshmi Prasad (Employee, IN - L1)</option>
              <option value="E2011">E2011 - Nikhil Joshi (Employee, IN - L3)</option>
              <option value="E2012">E2012 - Fatima Sheikh (Employee, IN - L2)</option>
              <option value="E1001">E1001 - Meera Krishnan (HR Staff, IN - L7)</option>
              <option value="E1002">E1002 - Rohan Bhat (HR Staff, IN - L4)</option>
            </optgroup>
            <optgroup label="── 🇺🇸 United States (US) ──">
              <option value="E3001">E3001 - Michael Turner (Manager, US - L7)</option>
              <option value="E3002">E3002 - Jessica Alvarez (Manager, US - L6)</option>
              <option value="E3003">E3003 - Brandon Lee (Manager, US - L5)</option>
              <option value="E3004">E3004 - Emily Carter (Employee, US - L3)</option>
              <option value="E3005">E3005 - Marcus Johnson (Employee, US - L4)</option>
              <option value="E3006">E3006 - Olivia Nguyen (Employee, US - L2)</option>
              <option value="E3007">E3007 - Daniel Kim (Employee, US - L4)</option>
              <option value="E3008">E3008 - Sophia Martinez (Employee, US - L3)</option>
              <option value="E3009">E3009 - Tyler Brooks (Employee, US - L3)</option>
              <option value="E3010">E3010 - Hannah Patel (Employee, US - L1)</option>
              <option value="E1003">E1003 - Dana Whitfield (HR Staff, US - L5)</option>
            </optgroup>
            <optgroup label="── 🇩🇪 Germany (DE) ──">
              <option value="E4001">E4001 - Stefan Wagner (Manager, DE - L7)</option>
              <option value="E4002">E4002 - Julia Becker (Manager, DE - L6)</option>
              <option value="E4003">E4003 - Tobias Schmitt (Manager, DE - L5)</option>
              <option value="E4004">E4004 - Lena Hoffmann (Employee, DE - L3)</option>
              <option value="E4005">E4005 - Maximilian Fischer (Employee, DE - L4)</option>
              <option value="E4006">E4006 - Anna Schulz (Employee, DE - L2)</option>
              <option value="E4007">E4007 - Jonas Weber (Employee, DE - L5)</option>
              <option value="E4008">E4008 - Sarah Klein (Employee, DE - L3)</option>
              <option value="E4009">E4009 - Felix Richter (Employee, DE - L4)</option>
              <option value="E4010">E4010 - Mia Neumann (Employee, DE - L1)</option>
              <option value="E1004">E1004 - Katrin Vogel (HR Staff, DE - L5)</option>
            </optgroup>
          </select>
        </div>

        <!-- Header 2: Content-Type -->
        <div class="form-group">
          <label class="form-label">
            <span>Header: Content-Type</span>
            <code>Content-Type: application/json</code>
          </label>
        </div>

        <!-- Body Field 1: session_id -->
        <div class="form-group">
          <label class="form-label">
            <span>Request Body: session_id</span>
            <code>{"session_id": "string"}</code>
          </label>
          <div class="session-input-row">
            <input type="text" id="sessionIdInput" value="session_1">
            <button class="btn-small" onclick="generateNewSession()">New Session</button>
          </div>
        </div>

        <!-- Body Field 2: message -->
        <div class="form-group">
          <label class="form-label">
            <span>Request Body: message</span>
            <code>{"message": "string"}</code>
          </label>
          <textarea id="messageInput" rows="3" placeholder="Type an employee question or request..."></textarea>
        </div>

        <!-- Quick Sample Queries (from Assessment PDF) -->
        <div class="scenarios-title">Quick Test Prompts (Assessment Scenarios):</div>
        <div class="scenarios-list">
          <button class="scenario-btn" onclick="setQuery('What is my leave balance?')">🏖️ Check My Balance</button>
          <button class="scenario-btn" onclick="setQuery('What is our hybrid remote work policy?')">🏢 Hybrid Policy (Memo)</button>
          <button class="scenario-btn" onclick="setQuery('I want to apply for annual leave from 2026-11-03 to 2026-11-04')">📅 Apply Leave (2-Step)</button>
          <button class="scenario-btn" onclick="setQuery('Show team leave for my direct reports next week')">👥 Team Leave (Manager)</button>
          <button class="scenario-btn" onclick="setQuery('Show me Divya Menon\'s leave balance')">🔒 Leave RBAC Check</button>
          <button class="scenario-btn" onclick="setQuery('What was the sick leave allowance in 2025?')">⏳ Reference Date 2025</button>
          <button class="scenario-btn" onclick="setQuery('How many annual leave days will I have by December?')">🧮 Future Accrual (Hybrid)</button>
          <button class="scenario-btn" onclick="setQuery('What is our policy on pet adoption allowances?')">❓ Missing Policy</button>
        </div>

        <!-- Execute Button -->
        <button class="btn-submit" id="submitBtn" onclick="executePostChat()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          Execute POST /chat
        </button>

        <!-- Section 9.1 Error Code Tests -->
        <div class="error-tests">
          <div class="scenarios-title" style="color:#f87171;">Section 9.1 Error Code Automated Tests:</div>
          <div class="error-btns">
            <button class="btn-err" onclick="testError(400)">400 Bad Body</button>
            <button class="btn-err" onclick="testError(401)">401 Bad Header</button>
            <button class="btn-err" onclick="testError(403)">403 Session Hijack</button>
          </div>
        </div>
      </div>
    </div>

    <!-- RIGHT COLUMN: SECTION 9.1 RESPONSE OUTPUT -->
    <div class="card">
      <div class="card-header">
        <div class="card-title title-out">
          <span>2. Section 9.1 Response Output</span>
        </div>
        <span class="status-badge status-idle" id="resStatusBadge">Status: Ready</span>
      </div>

      <div class="card-body" id="outputBody">

        <!-- 1. Answer -->
        <div class="output-section">
          <div class="output-label">
            <span>answer (string)</span>
            <span style="font-size:10px; color:#9ca3af;">Primary Human-Readable Answer</span>
          </div>
          <div class="output-value-text" id="outAnswer">Click 'Execute POST /chat' or choose a quick prompt to see the live output.</div>
        </div>

        <!-- 2. Route & Pending Confirmation -->
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
          <div class="output-section">
            <div class="output-label">route (string)</div>
            <div id="outRoute"><span class="route-pill route-no_answer">-</span></div>
          </div>
          <div class="output-section">
            <div class="output-label">pending_confirmation (bool)</div>
            <div id="outPending" style="font-family:'JetBrains Mono',monospace; font-size:13px; color:#fff; font-weight:600;">false</div>
          </div>
        </div>

        <!-- Two-Step Confirmation Box (Section 8.2) -->
        <div class="confirm-box" id="confirmBox" style="display:none;">
          <div class="confirm-text">⚠️ Action pending user confirmation (Section 8.2)</div>
          <div class="confirm-actions">
            <button class="btn-action-confirm" onclick="confirmAction('confirm')">✅ Confirm Action</button>
            <button class="btn-action-cancel" onclick="confirmAction('cancel')">❌ Discard</button>
          </div>
        </div>

        <!-- 3. Citations -->
        <div class="output-section">
          <div class="output-label">
            <span>citations (array of { doc_id, locator })</span>
            <span id="citationCount" style="color:#60a5fa; font-size:10px;">0 items</span>
          </div>
          <div id="outCitations">
            <div style="font-size:12px; color:var(--text-muted); font-style:italic;">No citations (Empty [])</div>
          </div>
        </div>

        <!-- 4. Tool Calls -->
        <div class="output-section">
          <div class="output-label">
            <span>tool_calls (array of { name, args, status })</span>
            <span id="toolCount" style="color:#c084fc; font-size:10px;">0 items</span>
          </div>
          <div id="outToolCalls">
            <div style="font-size:12px; color:var(--text-muted); font-style:italic;">No tool calls (Empty [])</div>
          </div>
        </div>

        <!-- 5. Request ID -->
        <div class="output-section" style="padding:8px 12px;">
          <div class="output-label">request_id (string)</div>
          <div id="outReqId" style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#94a3b8;">-</div>
        </div>

        <!-- 6. Raw JSON Response (Section 9.1 Contract) -->
        <div class="output-section">
          <div class="output-label">
            <span>Raw Response Body (Exact Section 9.1 Schema)</span>
            <button class="copy-btn" onclick="copyJson()">Copy JSON</button>
          </div>
          <div class="json-box" id="outJson">{}</div>
        </div>

      </div>
    </div>

  </div>

  <script>
    let currentSessionId = "session_" + Math.random().toString(36).substring(2, 9);
    document.getElementById("sessionIdInput").value = currentSessionId;

    function generateNewSession() {
      currentSessionId = "session_" + Math.random().toString(36).substring(2, 9);
      document.getElementById("sessionIdInput").value = currentSessionId;
    }

    function onEmployeeChange() {
      generateNewSession();
    }

    function setQuery(text) {
      document.getElementById("messageInput").value = text;
      executePostChat();
    }

    async function executePostChat() {
      const empId = document.getElementById("empSelect").value;
      const sessId = document.getElementById("sessionIdInput").value.trim() || currentSessionId;
      const message = document.getElementById("messageInput").value.trim();
      
      if (!message) {
        alert("Please enter a message.");
        return;
      }

      const submitBtn = document.getElementById("submitBtn");
      submitBtn.disabled = true;
      submitBtn.innerText = "Executing POST /chat...";

      try {
        const resp = await fetch("/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Employee-Id": empId
          },
          body: JSON.stringify({
            session_id: sessId,
            message: message
          })
        });

        const statusBadge = document.getElementById("resStatusBadge");
        statusBadge.innerText = `HTTP ${resp.status} ${resp.statusText || (resp.ok ? 'OK' : 'Error')}`;
        statusBadge.className = "status-badge " + (resp.ok ? "status-200" : "status-err");

        if (resp.ok) {
          const data = await resp.json();
          renderOutput(data);
        } else {
          const errText = await resp.text();
          let parsed; try { parsed = JSON.parse(errText); } catch(e) { parsed = { detail: errText }; }
          renderErrorOutput(resp.status, parsed);
        }
      } catch (err) {
        alert("Connection error: " + err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          Execute POST /chat
        `;
      }
    }

    function renderOutput(data) {
      // 1. Answer
      document.getElementById("outAnswer").innerText = data.answer || "";

      // 2. Route
      const route = data.route || "no_answer";
      document.getElementById("outRoute").innerHTML = `<span class="route-pill route-${route}">${route.toUpperCase()}</span>`;

      // 3. Pending Confirmation
      const pending = !!data.pending_confirmation;
      document.getElementById("outPending").innerText = String(pending);
      document.getElementById("outPending").style.color = pending ? "#fbbf24" : "#fff";
      document.getElementById("confirmBox").style.display = pending ? "flex" : "none";

      // 4. Citations
      const citations = data.citations || [];
      document.getElementById("citationCount").innerText = `${citations.length} item(s)`;
      if (citations.length > 0) {
        let html = '<table class="data-table"><thead><tr><th>doc_id</th><th>locator</th></tr></thead><tbody>';
        citations.forEach(c => {
          html += `<tr><td><code>${c.doc_id}</code></td><td>${c.locator}</td></tr>`;
        });
        html += '</tbody></table>';
        document.getElementById("outCitations").innerHTML = html;
      } else {
        document.getElementById("outCitations").innerHTML = '<div style="font-size:12px; color:var(--text-muted); font-style:italic;">No citations (Empty [])</div>';
      }

      // 5. Tool Calls
      const tools = data.tool_calls || [];
      document.getElementById("toolCount").innerText = `${tools.length} item(s)`;
      if (tools.length > 0) {
        let html = '<table class="data-table"><thead><tr><th>name</th><th>status</th><th>args</th></tr></thead><tbody>';
        tools.forEach(t => {
          const statusColor = t.status === 'error' ? '#f87171' : (t.status === 'pending_confirmation' ? '#fbbf24' : '#34d399');
          html += `<tr><td><code>${t.name}</code></td><td style="color:${statusColor}; font-weight:600;">${t.status}</td><td><code>${JSON.stringify(t.args)}</code></td></tr>`;
        });
        html += '</tbody></table>';
        document.getElementById("outToolCalls").innerHTML = html;
      } else {
        document.getElementById("outToolCalls").innerHTML = '<div style="font-size:12px; color:var(--text-muted); font-style:italic;">No tool calls (Empty [])</div>';
      }

      // 6. Request ID
      document.getElementById("outReqId").innerText = data.request_id || "-";

      // 7. Full JSON Box
      document.getElementById("outJson").innerText = JSON.stringify(data, null, 2);
    }

    function renderErrorOutput(statusCode, errData) {
      document.getElementById("outAnswer").innerText = `Error: ${JSON.stringify(errData, null, 2)}`;
      document.getElementById("outRoute").innerHTML = `<span class="route-pill route-refuse">HTTP ${statusCode}</span>`;
      document.getElementById("outPending").innerText = "false";
      document.getElementById("confirmBox").style.display = "none";
      document.getElementById("outCitations").innerHTML = '<div style="font-size:12px; color:var(--text-muted);">[]</div>';
      document.getElementById("outToolCalls").innerHTML = '<div style="font-size:12px; color:var(--text-muted);">[]</div>';
      document.getElementById("outReqId").innerText = "-";
      document.getElementById("outJson").innerText = JSON.stringify(errData, null, 2);
    }

    function confirmAction(decision) {
      document.getElementById("messageInput").value = decision;
      executePostChat();
    }

    function copyJson() {
      const text = document.getElementById("outJson").innerText;
      navigator.clipboard.writeText(text);
      alert("Section 9.1 JSON copied to clipboard!");
    }

    // Section 9.1 Error Code Automated Tests
    async function testError(code) {
      const empId = document.getElementById("empSelect").value;
      const sessId = document.getElementById("sessionIdInput").value;

      if (code === 400) {
        // Send invalid body syntax
        try {
          const resp = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Employee-Id": empId },
            body: "{ invalid_json: true " // malformed
          });
          const text = await resp.text();
          let data; try { data = JSON.parse(text); } catch(e) { data = { detail: text }; }
          document.getElementById("resStatusBadge").innerText = `HTTP ${resp.status} BAD REQUEST`;
          document.getElementById("resStatusBadge").className = "status-badge status-err";
          renderErrorOutput(resp.status, data);
        } catch(e) { alert(e.message); }
      } else if (code === 401) {
        // Send unknown employee ID header
        try {
          const resp = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Employee-Id": "UNKNOWN_ID" },
            body: JSON.stringify({ session_id: sessId, message: "Hello" })
          });
          const text = await resp.text();
          let data; try { data = JSON.parse(text); } catch(e) { data = { detail: text }; }
          document.getElementById("resStatusBadge").innerText = `HTTP ${resp.status} UNAUTHORIZED`;
          document.getElementById("resStatusBadge").className = "status-badge status-err";
          renderErrorOutput(resp.status, data);
        } catch(e) { alert(e.message); }
      } else if (code === 403) {
        // Hijack another employee's session
        try {
          // 1. Init with E2004
          await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Employee-Id": "E2004" },
            body: JSON.stringify({ session_id: "session_belonging_to_e2004", message: "Hi" })
          });
          // 2. Call with E1001 using the same session
          const resp = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Employee-Id": "E1001" },
            body: JSON.stringify({ session_id: "session_belonging_to_e2004", message: "Hi" })
          });
          const text = await resp.text();
          let data; try { data = JSON.parse(text); } catch(e) { data = { detail: text }; }
          document.getElementById("resStatusBadge").innerText = `HTTP ${resp.status} FORBIDDEN`;
          document.getElementById("resStatusBadge").className = "status-badge status-err";
          renderErrorOutput(resp.status, data);
        } catch(e) { alert(e.message); }
      }
    }
  </script>
</body>
</html>
"""
