/**
 * DealShield – Enterprise M&A Due Diligence AI Dashboard
 * Vanilla JS Application (No React, Zero Emojis)
 */

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  activeTab: 'analysis',
  targetCompany: 'Northwind Microsystems Inc.',
  activeDeal: {
    name: 'Project Aegis',
    deal_value_usd: 850_000_000,
    acquirer_name: 'Helix Acquisition Corp',
  },
  availableTargets: [],
  graphStats: null,
  neo4jStatus: 'checking',
  pipelineRunning: false,
  pipelineResult: null,
  sessionId: 'sess_' + Math.random().toString(36).substring(2, 11),
  chatLoading: false,

  // Graph visualization
  graphViewMode: 'all',
  graphNetwork: null,
  graphNodes: [],
  graphEdges: [],

  // Contracts
  contractsData: [],
};

// ── Formatting Utilities ───────────────────────────────────────────────────
function fmtUsd(val) {
  if (val === null || val === undefined || isNaN(val)) return '$0';
  const num = Number(val);
  if (Math.abs(num) >= 1_000_000_000) {
    return '$' + (num / 1_000_000_000).toFixed(1) + 'B';
  }
  if (Math.abs(num) >= 1_000_000) {
    return '$' + (num / 1_000_000).toFixed(1) + 'M';
  }
  return '$' + num.toLocaleString();
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function getSeverityClass(sev) {
  const s = String(sev || '').toUpperCase();
  if (s === 'CRITICAL') return 'severity-critical';
  if (s === 'HIGH') return 'severity-high';
  if (s === 'MEDIUM') return 'severity-medium';
  return 'severity-low';
}

// ── API Client ─────────────────────────────────────────────────────────────
const api = {
  async request(path, options = {}) {
    const res = await fetch(`/api${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `API Error ${res.status}`);
    }
    return res.json();
  },

  health() {
    return this.request('/health');
  },

  graphStats() {
    return this.request('/graph/stats');
  },

  targets() {
    return this.request('/targets');
  },

  visualizeGraph(target, viewMode = 'all') {
    return this.request(`/graph/visualize?target_company=${encodeURIComponent(target)}&view_mode=${encodeURIComponent(viewMode)}`);
  },

  contracts(target) {
    return this.request(`/contracts?target_company=${encodeURIComponent(target)}`);
  },

  analyzeCoc(target) {
    return this.request('/analyze/coc', {
      method: 'POST',
      body: JSON.stringify({ target_company: target }),
    });
  },

  analyzeSecondary(target) {
    return this.request('/analyze/secondary', {
      method: 'POST',
      body: JSON.stringify({ target_company: target }),
    });
  },

  scoreRisk(payload) {
    return this.request('/analyze/score', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  runFullPipeline(target) {
    return this.request('/analyze/full', {
      method: 'POST',
      body: JSON.stringify({ target_company: target }),
    });
  },

  chat(payload) {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

// ── DOM References ─────────────────────────────────────────────────────────
const dom = {
  targetSelect: document.getElementById('targetCompanySelect'),
  dealName: document.getElementById('dealContextName'),
  dealValue: document.getElementById('dealContextValue'),
  displayTarget: document.getElementById('displayTargetCompany'),

  statCompanies: document.getElementById('statCompanies'),
  statExecutives: document.getElementById('statExecutives'),
  statClauses: document.getElementById('statClauses'),
  statDocs: document.getElementById('statDocs'),
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),

  tabBtns: document.querySelectorAll('.tab-btn'),
  tabPanes: {
    analysis: document.getElementById('tabAnalysis'),
    graph: document.getElementById('tabGraph'),
    contracts: document.getElementById('tabContracts'),
  },

  btnRun: document.getElementById('btnRunPipeline'),
  stageTracker: document.getElementById('stageTracker'),
  stageCoc: document.getElementById('stageItemCoc'),
  stageSecondary: document.getElementById('stageItemSecondary'),
  stageScoring: document.getElementById('stageItemScoring'),
  stageDetailCoc: document.getElementById('stageDetailCoc'),
  stageDetailSecondary: document.getElementById('stageDetailSecondary'),
  stageDetailScoring: document.getElementById('stageDetailScoring'),
  pipelineErrorBox: document.getElementById('pipelineErrorBox'),
  pipelineErrorMsg: document.getElementById('pipelineErrorMsg'),
  analysisEmptyState: document.getElementById('analysisEmptyState'),
  resultsContainer: document.getElementById('resultsContainer'),

  bannerDealValue: document.getElementById('bannerDealValue'),
  bannerRiskDeductions: document.getElementById('bannerRiskDeductions'),
  bannerAdjustedValue: document.getElementById('bannerAdjustedValue'),

  kpiTotalExposure: document.getElementById('kpiTotalExposure'),
  kpiCriticalCount: document.getElementById('kpiCriticalCount'),
  kpiHighCount: document.getElementById('kpiHighCount'),
  kpiConflictsCount: document.getElementById('kpiConflictsCount'),
  riskCardsContainer: document.getElementById('riskCardsContainer'),
  conflictsContainer: document.getElementById('conflictsContainer'),
  secondaryContainer: document.getElementById('secondaryContainer'),

  // Graph
  graphCanvasContainer: document.getElementById('graphCanvasContainer'),
  graphFilterPills: document.querySelectorAll('.filter-pill[data-view]'),
  graphSearchInput: document.getElementById('graphSearchInput'),
  btnGraphFit: document.getElementById('btnGraphFit'),
  nodeInspectorPanel: document.getElementById('nodeInspectorPanel'),
  btnInspectorClose: document.getElementById('btnInspectorClose'),
  inspectorCategoryBadge: document.getElementById('inspectorCategoryBadge'),
  inspectorNodeName: document.getElementById('inspectorNodeName'),
  inspectorNodeId: document.getElementById('inspectorNodeId'),
  inspectorPropertiesList: document.getElementById('inspectorPropertiesList'),
  inspectorConnectionsList: document.getElementById('inspectorConnectionsList'),

  // Contracts
  contractSearchInput: document.getElementById('contractSearchInput'),
  contractCountLabel: document.getElementById('contractCountLabel'),
  contractsContainer: document.getElementById('contractsContainer'),

  // Chatbot
  chatbotFab: document.getElementById('chatbotFab'),
  chatbotWindow: document.getElementById('chatbotWindow'),
  chatbotCloseBtn: document.getElementById('chatbotCloseBtn'),
  chatbotMessages: document.getElementById('chatbotMessages'),
  chatbotInput: document.getElementById('chatbotInput'),
  chatbotSendBtn: document.getElementById('chatbotSendBtn'),
};

// ── Tab Navigation ─────────────────────────────────────────────────────────
function setupTabs() {
  dom.tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      dom.tabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      Object.entries(dom.tabPanes).forEach(([id, pane]) => {
        if (!pane) return;
        if (id === tabId) {
          pane.style.display = 'block';
          pane.classList.add('active');
        } else {
          pane.style.display = 'none';
          pane.classList.remove('active');
        }
      });
      state.activeTab = tabId;

      if (tabId === 'graph') {
        if (state.graphNetwork) {
          setTimeout(() => state.graphNetwork.fit(), 100);
        } else {
          loadGraphVisualization();
        }
      } else if (tabId === 'contracts') {
        if (state.contractsData.length === 0) {
          loadContracts();
        }
      }
    });
  });
}

// ── Targets Dropdown ───────────────────────────────────────────────────────
async function loadTargets() {
  try {
    const data = await api.targets();
    state.availableTargets = data.targets || [];
    dom.targetSelect.innerHTML = '';

    state.availableTargets.forEach((t) => {
      const opt = document.createElement('option');
      opt.value = t.name;
      opt.textContent = `${t.name} (${t.deal_name || 'M&A'} - ${fmtUsd(t.deal_value_usd)})`;
      dom.targetSelect.appendChild(opt);
    });

    if (state.availableTargets.length > 0) {
      dom.targetSelect.value = state.availableTargets[0].name;
      onTargetChange(state.availableTargets[0].name);
    }
  } catch (err) {
    onTargetChange('Northwind Microsystems Inc.');
  }
}

function onTargetChange(targetName) {
  state.targetCompany = targetName;
  dom.displayTarget.textContent = targetName;

  const found = state.availableTargets.find((t) => t.name === targetName);
  if (found) {
    state.activeDeal = found;
    dom.dealName.textContent = found.deal_name || 'M&A Due Diligence';
    dom.dealValue.textContent = `Deal Value: ${fmtUsd(found.deal_value_usd)}`;
    dom.bannerDealValue.textContent = fmtUsd(found.deal_value_usd);
  } else {
    dom.dealName.textContent = targetName.includes('Aurora') ? 'Project Vector' : 'Project Aegis';
    const val = targetName.includes('Aurora') ? 640_000_000 : 850_000_000;
    dom.dealValue.textContent = `Deal Value: ${fmtUsd(val)}`;
    dom.bannerDealValue.textContent = fmtUsd(val);
  }

  // Reload current active tab view
  if (state.activeTab === 'graph') {
    loadGraphVisualization();
  } else if (state.activeTab === 'contracts') {
    loadContracts();
  }
}

// ── Knowledge Graph Stats & Health ─────────────────────────────────────────
async function loadGraphStats() {
  try {
    const data = await api.graphStats();
    state.graphStats = data;
    dom.statCompanies.textContent = data.companies ?? 0;
    dom.statExecutives.textContent = data.executives ?? 0;
    dom.statClauses.textContent = data.clauses ?? 0;
    dom.statDocs.textContent = data.doc_chunks ?? 0;

    dom.statusDot.className = 'status-dot connected';
    dom.statusText.textContent = 'Connected to Aura';
    dom.statusText.style.color = 'var(--text-secondary)';
    state.neo4jStatus = 'connected';
  } catch (err) {
    dom.statusDot.className = 'status-dot error';
    dom.statusText.textContent = 'Connection Error';
    dom.statusText.style.color = 'var(--accent-red)';
    state.neo4jStatus = 'error';
  }
}

// ── Interactive Graph Visualization (Vis-Network) ──────────────────────────
async function loadGraphVisualization() {
  const container = dom.graphCanvasContainer;
  if (!container) return;

  container.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; height:100%; color:var(--text-muted); font-size:0.9rem;">
      <svg width="16" height="16" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Rendering relationship graph...
    </div>`;

  try {
    const data = await api.visualizeGraph(state.targetCompany, state.graphViewMode);
    state.graphNodes = data.nodes || [];
    state.graphEdges = data.edges || [];

    container.innerHTML = '';

    if (typeof vis === 'undefined' || !vis.Network) {
      renderCanvasFallback(container, state.graphNodes, state.graphEdges);
      return;
    }

    const visNodes = new vis.DataSet(
      state.graphNodes.map((n) => ({
        id: n.id,
        label: n.label,
        color: {
          background: n.color,
          border: '#ffffff',
          highlight: { background: n.color, border: '#ffffff' },
        },
        font: { color: '#ffffff', size: 12, face: 'Inter', strokeWidth: 2, strokeColor: '#09090b' },
        size: n.size || 22,
        shape: 'dot',
        borderWidth: 2,
        shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 8, x: 2, y: 2 },
      }))
    );

    const visEdges = new vis.DataSet(
      state.graphEdges.map((e, idx) => ({
        id: `e_${idx}`,
        from: e.from,
        to: e.to,
        label: e.label,
        font: { color: '#a1a1aa', size: 9, face: 'Inter', align: 'middle', background: '#18181b', strokeWidth: 0 },
        color: { color: e.color || '#52525b', highlight: '#ffffff' },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        smooth: { type: 'continuous' },
      }))
    );

    const options = {
      physics: {
        forceAtlas2Based: {
          gravitationalConstant: -40,
          centralGravity: 0.005,
          springLength: 90,
          springConstant: 0.08,
        },
        maxVelocity: 50,
        solver: 'forceAtlas2Based',
        stabilization: { iterations: 120 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        zoomView: true,
        dragView: true,
        dragNodes: true,
      },
    };

    state.graphNetwork = new vis.Network(container, { nodes: visNodes, edges: visEdges }, options);

    // Node click listener -> Inspector Panel
    state.graphNetwork.on('click', (params) => {
      if (params.nodes && params.nodes.length > 0) {
        const clickedId = params.nodes[0];
        const nodeObj = state.graphNodes.find((n) => n.id === clickedId);
        if (nodeObj) {
          openNodeInspector(nodeObj);
        }
      } else {
        closeNodeInspector();
      }
    });
  } catch (err) {
    container.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:center; height:100%; color:var(--accent-red); font-size:0.9rem;">
        Failed to render graph: ${escapeHtml(err.message)}
      </div>`;
  }
}

// Fallback HTML5 Canvas Force Layout if CDN script fails
function renderCanvasFallback(container, nodes, edges) {
  const canvas = document.createElement('canvas');
  canvas.width = container.clientWidth || 800;
  canvas.height = 580;
  container.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = '#09090b';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = '#a1a1aa';
  ctx.font = '14px Inter';
  ctx.textAlign = 'center';
  ctx.fillText('Relationship Network Loaded (' + nodes.length + ' entities, ' + edges.length + ' relations)', canvas.width / 2, 40);

  // Position nodes in a circular layout
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const radius = Math.min(cx, cy) - 90;

  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2;
    n._x = cx + Math.cos(angle) * radius;
    n._y = cy + Math.sin(angle) * radius;
  });

  // Draw edges
  edges.forEach((e) => {
    const u = nodes.find((n) => n.id === e.from);
    const v = nodes.find((n) => n.id === e.to);
    if (u && v) {
      ctx.strokeStyle = e.color || '#3f3f46';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(u._x, u._y);
      ctx.lineTo(v._x, v._y);
      ctx.stroke();
    }
  });

  // Draw nodes
  nodes.forEach((n) => {
    ctx.fillStyle = n.color || '#3b82f6';
    ctx.beginPath();
    ctx.arc(n._x, n._y, 14, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = '#fafafa';
    ctx.font = '11px Inter';
    ctx.fillText(n.label.substring(0, 16), n._x, n._y + 24);
  });
}

function openNodeInspector(node) {
  dom.inspectorNodeName.textContent = node.label;
  dom.inspectorNodeId.textContent = node.id;
  dom.inspectorCategoryBadge.textContent = node.category || 'Entity';
  dom.inspectorCategoryBadge.className = `severity-badge ${node.category.includes('Conflicted') ? 'severity-critical' : node.category.includes('Target') ? 'severity-high' : 'severity-low'}`;

  // Properties
  const props = node.properties || {};
  const propKeys = Object.keys(props).filter((k) => !k.startsWith('_') && k !== 'id');

  if (propKeys.length === 0) {
    dom.inspectorPropertiesList.innerHTML = '<div style="font-size:0.8rem; color:var(--text-muted);">No extra metadata recorded.</div>';
  } else {
    dom.inspectorPropertiesList.innerHTML = propKeys
      .map((k) => {
        let val = props[k];
        if (typeof val === 'number' && (k.toLowerCase().includes('usd') || k.toLowerCase().includes('val') || k.toLowerCase().includes('spend') || k.toLowerCase().includes('revenue'))) {
          val = fmtUsd(val);
        } else if (typeof val === 'object') {
          val = JSON.stringify(val);
        }
        return `
        <div class="inspector-prop-row">
          <div class="inspector-prop-label">${escapeHtml(k)}</div>
          <div class="inspector-prop-val">${escapeHtml(String(val))}</div>
        </div>`;
      })
      .join('');
  }

  // Connections
  const connectedEdges = state.graphEdges.filter((e) => e.from === node.id || e.to === node.id);
  if (connectedEdges.length === 0) {
    dom.inspectorConnectionsList.innerHTML = '<div>Isolated node</div>';
  } else {
    dom.inspectorConnectionsList.innerHTML = connectedEdges
      .map((e) => {
        const isOutgoing = e.from === node.id;
        const otherId = isOutgoing ? e.to : e.from;
        const otherNode = state.graphNodes.find((n) => n.id === otherId);
        const otherLabel = otherNode ? otherNode.label : otherId;
        return `
        <div style="margin-bottom:6px;">
          ${isOutgoing ? '&rarr;' : '&larr;'} <strong style="color:var(--text-primary);">${escapeHtml(e.label)}</strong> ${escapeHtml(otherLabel)}
        </div>`;
      })
      .join('');
  }

  dom.nodeInspectorPanel.style.display = 'block';
}

function closeNodeInspector() {
  dom.nodeInspectorPanel.style.display = 'none';
}

// ── Contract & Covenant Audit ──────────────────────────────────────────────
async function loadContracts() {
  const container = dom.contractsContainer;
  if (!container) return;

  container.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; padding:3rem; color:var(--text-muted); font-size:0.9rem;">
      <svg width="16" height="16" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Loading contract covenants...
    </div>`;

  try {
    const data = await api.contracts(state.targetCompany);
    state.contractsData = data.contracts || [];
    renderContractsList(state.contractsData);
  } catch (err) {
    container.innerHTML = `
      <div style="color:var(--accent-red); font-size:0.9rem; padding:1.5rem;">
        Failed to load contracts: ${escapeHtml(err.message)}
      </div>`;
  }
}

function renderContractsList(list) {
  dom.contractCountLabel.textContent = `Showing ${list.length} covenants`;

  if (list.length === 0) {
    dom.contractsContainer.innerHTML = `
      <div style="background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-lg); padding:2rem; text-align:center; color:var(--text-secondary);">
        No contract covenants recorded for this target company.
      </div>`;
    return;
  }

  dom.contractsContainer.innerHTML = list
    .map((item) => {
      const title = item.clause_title || item.clause_id;
      const agreement = item.agreement_title || 'General Agreement';
      const ctype = item.clause_type || 'Restrictive Covenant';
      const section = item.section ? `Section ${item.section}` : '';
      const exposure = item.exposure_usd || item.penalty_usd || 0;
      const sevClass = getSeverityClass(item.severity);
      const excerpt = item.clause_text || '';
      const evidence = item.evidence_chunks || [];

      return `
      <div class="contract-audit-card">
        <div class="contract-audit-top">
          <div>
            <span class="severity-badge ${sevClass}" style="margin-right:8px;">${escapeHtml(ctype)}</span>
            <span style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(section)}</span>
            <div class="contract-audit-title">${escapeHtml(title)}</div>
            <div class="contract-audit-agreement">${escapeHtml(agreement)}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Liabilities at Risk</div>
            <div class="contract-audit-exposure">${exposure > 0 ? fmtUsd(exposure) : 'Non-Monetary Injunction'}</div>
          </div>
        </div>

        ${excerpt ? `
        <div class="contract-audit-excerpt">
          &ldquo;${escapeHtml(excerpt)}&rdquo;
        </div>` : ''}

        ${evidence.length > 0 ? `
        <div style="margin-top:0.75rem; font-size:0.75rem; color:var(--text-muted);">
          Evidence Lineage: DocumentChunk ${escapeHtml(evidence[0].id)} ${evidence[0].page ? `(Page ${evidence[0].page})` : ''}
        </div>` : ''}
      </div>`;
    })
    .join('');
}

// ── Pipeline Runner (Executive Dashboard) ──────────────────────────────────
function setStageStatus(stageEl, status, detail = '') {
  stageEl.className = `stage-item ${status}`;
  const iconDiv = stageEl.querySelector('.stage-icon');
  const detailSpan = stageEl.querySelector('.stage-detail');

  if (status === 'running') {
    iconDiv.innerHTML = '<svg width="18" height="18" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>';
  } else if (status === 'complete') {
    iconDiv.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
  } else if (status === 'error') {
    iconDiv.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
  } else {
    iconDiv.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>';
  }

  if (detailSpan) {
    detailSpan.textContent = detail;
  }
}

async function runPipeline() {
  const target = state.targetCompany;

  state.pipelineRunning = true;
  dom.btnRun.disabled = true;
  dom.btnRun.innerHTML = '<svg width="16" height="16" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Running Due Diligence...';

  dom.stageTracker.style.display = 'grid';
  dom.pipelineErrorBox.style.display = 'none';
  dom.analysisEmptyState.style.display = 'none';
  dom.resultsContainer.style.display = 'none';

  setStageStatus(dom.stageCoc, 'running', 'Searching multi-hop conflict chains...');
  setStageStatus(dom.stageSecondary, 'pending', '');
  setStageStatus(dom.stageScoring, 'pending', '');

  try {
    // Stage 1
    const cocResult = await api.analyzeCoc(target);
    const conflictCount = cocResult.total_conflicts_detected ?? (cocResult.related_party_conflicts || []).length;
    setStageStatus(dom.stageCoc, 'complete', `${conflictCount} conflict(s) detected`);

    // Stage 2
    setStageStatus(dom.stageSecondary, 'running', 'Scanning antitrust, exclusivity & governance...');
    const secondaryResult = await api.analyzeSecondary(target);
    const risksFound = secondaryResult.risks_found ?? (secondaryResult.risk_details || []).length;
    setStageStatus(dom.stageSecondary, 'complete', `${risksFound} risk factor(s) identified`);

    // Stage 3
    setStageStatus(dom.stageScoring, 'running', 'Calculating deterministic exposure & writing to graph...');
    const fullResult = await api.runFullPipeline(target);
    const scoredList = fullResult?.stages?.scored_risks || [];
    setStageStatus(dom.stageScoring, 'complete', `${scoredList.length} factor(s) persisted`);

    state.pipelineResult = {
      coc: cocResult,
      secondary: secondaryResult,
      scored: scoredList,
      summary: fullResult.summary,
    };

    renderResults(state.pipelineResult);
    loadGraphStats();
  } catch (err) {
    dom.pipelineErrorBox.style.display = 'flex';
    dom.pipelineErrorMsg.textContent = err.message || 'Due diligence pipeline execution failed';
  } finally {
    state.pipelineRunning = false;
    dom.btnRun.disabled = false;
    dom.btnRun.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Due Diligence';
  }
}

function renderResults(result) {
  const { coc, secondary, scored, summary } = result;

  const totalExposure = summary?.total_deal_deduction_usd ?? scored.reduce((sum, r) => sum + (r.calculation?.total_exposure_usd || 0), 0);
  const criticalCount = summary?.critical_count ?? scored.filter((r) => r.calculation?.severity === 'CRITICAL').length;
  const highCount = summary?.high_count ?? scored.filter((r) => r.calculation?.severity === 'HIGH').length;
  const conflictCount = summary?.total_conflicts ?? coc?.total_conflicts_detected ?? (coc?.related_party_conflicts || []).length;

  dom.kpiTotalExposure.textContent = fmtUsd(totalExposure);
  dom.kpiCriticalCount.textContent = criticalCount;
  dom.kpiHighCount.textContent = highCount;
  dom.kpiConflictsCount.textContent = conflictCount;

  // Banner numbers
  const dealVal = state.activeDeal?.deal_value_usd || 850_000_000;
  dom.bannerDealValue.textContent = fmtUsd(dealVal);
  dom.bannerRiskDeductions.textContent = fmtUsd(totalExposure);
  dom.bannerAdjustedValue.textContent = fmtUsd(Math.max(0, dealVal - totalExposure));

  // Render Risk Cards
  dom.riskCardsContainer.innerHTML = scored
    .map((r) => {
      const calc = r.calculation || {};
      const sevClass = getSeverityClass(calc.severity);
      const isRp = calc.is_related_party_conflict;
      const rationale = r.stored_risk?.description || r.rationale || '';
      const sourceChunk = r.stored_risk?.source_chunk_id || r.source_chunk_id || '';

      return `
      <div class="risk-card">
        <div class="risk-card-header">
          <div class="risk-card-title-group">
            <span class="severity-badge ${sevClass}">${escapeHtml(calc.severity || 'HIGH')}</span>
            <h4 class="risk-card-title">${escapeHtml(r.category || 'Risk Factor')}</h4>
          </div>
          <span class="risk-card-id">${escapeHtml(r.risk_id)}</span>
        </div>

        <div style="margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
            <span style="color: var(--text-secondary);">Risk Score: <strong>${calc.risk_score || 0} / 100</strong></span>
            <span style="color: var(--text-muted);">${isRp ? 'Related-Party Conflict' : 'Regulatory / Contractual'}</span>
          </div>
          <div style="background: var(--bg-surface); height: 6px; border-radius: 3px; overflow: hidden;">
            <div style="width: ${Math.min(100, calc.risk_score || 0)}%; height: 100%; background: ${calc.severity === 'CRITICAL' ? 'var(--accent-red)' : calc.severity === 'HIGH' ? 'var(--accent-amber)' : 'var(--accent-blue)'}; border-radius: 3px;"></div>
          </div>
        </div>

        <div class="risk-card-grid">
          <div>
            <div class="risk-metric-label">Total Financial Exposure</div>
            <div class="risk-metric-value" style="color: var(--accent-red); font-size: 1.15rem;">${fmtUsd(calc.total_exposure_usd)}</div>
          </div>
          <div>
            <div class="risk-metric-label">Base Penalty / Liquidated Damages</div>
            <div class="risk-metric-value">${fmtUsd(calc.base_penalty_usd)}</div>
          </div>
          <div>
            <div class="risk-metric-label">Annual Spend / Lock-in Commitment</div>
            <div class="risk-metric-value">${fmtUsd(calc.annual_contract_usd)}</div>
          </div>
          <div>
            <div class="risk-metric-label">Holding Traversal Hops</div>
            <div class="risk-metric-value">${calc.holding_hops || 0} hops</div>
          </div>
        </div>

        ${rationale ? `<div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 1rem; line-height: 1.45;"><strong>Finding:</strong> ${escapeHtml(rationale)}</div>` : ''}

        ${sourceChunk ? `
        <div class="risk-card-footer">
          <span class="evidence-source">Citation: DocumentChunk ${escapeHtml(sourceChunk)}</span>
        </div>` : ''}
      </div>`;
    })
    .join('');

  // Render Conflicts
  const conflicts = coc?.related_party_conflicts || [];
  if (conflicts.length === 0) {
    dom.conflictsContainer.innerHTML = `
      <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem; font-size: 0.875rem; color: var(--text-secondary);">
        No hidden related-party conflict chains detected for this target company.
      </div>`;
  } else {
    dom.conflictsContainer.innerHTML = conflicts
      .map((c, i) => {
        const dName = c.director?.name || 'Insider';
        const dTitle = c.director?.title || 'Executive/Director';
        const rpName = c.related_party?.name || 'Related Party';
        const relType = c.relationship_type || 'Spouse';
        const chain = c.holding_chain || [];
        const citations = c.document_citations || [];

        return `
        <div class="conflict-panel">
          <div class="conflict-header">
            <div>
              <span class="severity-badge severity-critical" style="margin-right: 8px;">CONFLICT #${i + 1}</span>
              <strong style="color: var(--text-primary); font-size: 1rem;">${escapeHtml(dName)} (${escapeHtml(dTitle)})</strong>
              <span style="color: var(--text-muted); font-size: 0.85rem; margin-left: 6px;">&bull; Rel: ${escapeHtml(relType)} (${escapeHtml(rpName)})</span>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 0.8rem; color: var(--text-muted);">Annual Spend:</span>
              <strong style="color: var(--text-primary); margin-left: 4px;">${fmtUsd(c.annual_supplier_value_usd)}</strong>
            </div>
          </div>

          <div style="margin: 1.25rem 0 0.5rem 0; font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">
            Beneficial Ownership Lineage (${c.holding_hops || 2} Hops)
          </div>

          <div class="conflict-chain">
            ${chain
              .map((node, nodeIdx) => {
                const isLast = nodeIdx === chain.length - 1;
                return `
                <div class="chain-node">
                  <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${escapeHtml(node.entity)}</div>
                  <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(node.role || '')}</div>
                  ${node.stake_percentage && node.stake_percentage !== '?' ? `<div style="font-size: 0.75rem; color: var(--accent-emerald); font-weight: 600; margin-top: 2px;">Stake: ${escapeHtml(String(node.stake_percentage))}%</div>` : ''}
                </div>
                ${!isLast ? '<div class="chain-arrow">&rarr;</div>' : ''}`;
              })
              .join('')}
          </div>

          ${citations.length > 0 ? `
          <div style="margin-top: 1rem;">
            ${citations
              .map((cit) => `
              <div class="evidence-card" style="margin-bottom: 0.5rem;">
                <div class="evidence-source">DocumentChunk ${escapeHtml(cit.id)} ${cit.page ? `&bull; Page ${cit.page}` : ''} ${cit.docId ? `(${escapeHtml(cit.docId)})` : ''}</div>
                <div class="evidence-text">&ldquo;${escapeHtml(cit.text)}&rdquo;</div>
              </div>`)
              .join('')}
          </div>` : ''}
        </div>`;
      })
      .join('');
  }

  // Render Secondary Risks
  const secondaryRisks = secondary?.risk_details || [];
  if (secondaryRisks.length === 0) {
    dom.secondaryContainer.innerHTML = `
      <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem; font-size: 0.875rem; color: var(--text-secondary);">
        No secondary restrictive covenants flagged for this target.
      </div>`;
  } else {
    dom.secondaryContainer.innerHTML = secondaryRisks
      .map((item) => {
        const cl = item.clause || {};
        const title = cl.title || cl.id;
        const exposure = cl.financial_exposure_usd || 0;
        const ctype = cl.clauseType || item.category || 'Covenant';
        const summary = cl.summary || cl.text || '';
        const evidence = item.evidence_chunks || [];

        return `
        <div class="secondary-risk-row">
          <div class="secondary-risk-header">
            <div>
              <span class="severity-badge severity-high" style="margin-right: 8px;">${escapeHtml(ctype)}</span>
              <strong style="color: var(--text-primary); font-size: 0.95rem;">${escapeHtml(title)}</strong>
              <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 8px;">(${escapeHtml(cl.id)})</span>
            </div>
            <div class="secondary-risk-exposure">${exposure > 0 ? fmtUsd(exposure) : 'Non-Monetary Breach'}</div>
          </div>
          ${summary ? `<p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem; line-height: 1.4;">${escapeHtml(summary)}</p>` : ''}
          ${evidence.length > 0 ? `
          <div style="margin-top: 0.75rem;">
            ${evidence
              .map((e) => `
              <div class="evidence-card" style="margin-bottom: 0.35rem;">
                <div class="evidence-source">Evidence: ${escapeHtml(e.id)} ${e.page ? `&bull; Page ${e.page}` : ''}</div>
                <div class="evidence-text">&ldquo;${escapeHtml(e.text)}&rdquo;</div>
              </div>`)
              .join('')}
          </div>` : ''}
        </div>`;
      })
      .join('');
  }

  dom.resultsContainer.style.display = 'block';
}

// ── AI Chatbot ─────────────────────────────────────────────────────────────
function setupChatbot() {
  dom.chatbotFab.addEventListener('click', () => {
    dom.chatbotWindow.style.display = 'flex';
    dom.chatbotFab.style.display = 'none';
    dom.chatbotInput.focus();
  });

  dom.chatbotCloseBtn.addEventListener('click', () => {
    dom.chatbotWindow.style.display = 'none';
    dom.chatbotFab.style.display = 'flex';
  });

  dom.chatbotSendBtn.addEventListener('click', handleChatSend);

  dom.chatbotInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSend();
    }
  });
}

async function handleChatSend() {
  const msg = dom.chatbotInput.value.trim();
  if (!msg || state.chatLoading) return;

  dom.chatbotInput.value = '';
  appendChatMessage('user', msg);
  state.chatLoading = true;

  const thinkingId = 'thinking_' + Date.now();
  const thinkingEl = document.createElement('div');
  thinkingEl.id = thinkingId;
  thinkingEl.className = 'chatbot-message assistant';
  thinkingEl.innerHTML = `
    <div class="chatbot-message-content" style="display:flex; align-items:center; gap:8px;">
      <svg width="14" height="14" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Analyzing deal graph...
    </div>`;
  dom.chatbotMessages.appendChild(thinkingEl);
  dom.chatbotMessages.scrollTop = dom.chatbotMessages.scrollHeight;

  try {
    const data = await api.chat({ session_id: state.sessionId, message: msg });
    const removeThinking = document.getElementById(thinkingId);
    if (removeThinking) removeThinking.remove();
    appendChatMessage('assistant', data.response || 'No response available.');
  } catch (err) {
    const removeThinking = document.getElementById(thinkingId);
    if (removeThinking) removeThinking.remove();
    appendChatMessage('assistant', `Error: ${err.message}`);
  } finally {
    state.chatLoading = false;
  }
}

function appendChatMessage(role, text) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `chatbot-message ${role}`;
  msgDiv.innerHTML = `<div class="chatbot-message-content">${escapeHtml(text).replace(/\n/g, '<br/>')}</div>`;
  dom.chatbotMessages.appendChild(msgDiv);
  dom.chatbotMessages.scrollTop = dom.chatbotMessages.scrollHeight;
}

// ── App Init ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupChatbot();
  loadGraphStats();
  loadTargets();

  // Target select listener
  dom.targetSelect.addEventListener('change', (e) => {
    onTargetChange(e.target.value);
  });

  // Run pipeline
  dom.btnRun.addEventListener('click', runPipeline);

  // Inspector close
  dom.btnInspectorClose.addEventListener('click', closeNodeInspector);

  // Fit graph button
  dom.btnGraphFit.addEventListener('click', () => {
    if (state.graphNetwork) state.graphNetwork.fit({ animation: true });
  });

  // Graph filter pills
  dom.graphFilterPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      dom.graphFilterPills.forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      state.graphViewMode = pill.getAttribute('data-view') || 'all';
      loadGraphVisualization();
    });
  });

  // Graph search
  dom.graphSearchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q || !state.graphNetwork) return;
    const match = state.graphNodes.find((n) => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q));
    if (match) {
      state.graphNetwork.focus(match.id, { scale: 1.3, animation: true });
      state.graphNetwork.selectNodes([match.id]);
      openNodeInspector(match);
    }
  });

  // Contract search
  dom.contractSearchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) {
      renderContractsList(state.contractsData);
      return;
    }
    const filtered = state.contractsData.filter((c) => {
      return (
        (c.clause_title || '').toLowerCase().includes(q) ||
        (c.agreement_title || '').toLowerCase().includes(q) ||
        (c.clause_type || '').toLowerCase().includes(q) ||
        (c.clause_text || '').toLowerCase().includes(q)
      );
    });
    renderContractsList(filtered);
  });
});
