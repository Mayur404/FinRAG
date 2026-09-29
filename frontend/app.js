const byId = (id) => document.getElementById(id);

// Persistent document selection storage so selections never reset
let selectedDocIds = new Set();
try {
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem('finrag_selected_doc_ids') : null;
  if (saved) {
    const parsed = JSON.parse(saved);
    if (Array.isArray(parsed)) {
      selectedDocIds = new Set(parsed);
    }
  }
} catch (_) {}

function saveSelectedDocIds() {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('finrag_selected_doc_ids', JSON.stringify(Array.from(selectedDocIds)));
    }
  } catch (_) {}
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function element(tag, value, className = '') {
  const node = document.createElement(tag);
  if (value) node.textContent = value;
  if (className) node.className = className;
  return node;
}

function setAskState(text, isPulse = false) {
  const el = byId('ask-state');
  if (!text) {
    el.innerHTML = '';
    return;
  }
  if (isPulse) {
    el.innerHTML = `<span class="pulse-dot"></span> <span>${escapeHtml(text)}</span>`;
  } else {
    el.textContent = text;
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    const isActive = btn.getAttribute('data-tab') === tabId;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-selected', String(isActive));
  });
  document.querySelectorAll('.tab-pane').forEach((pane) => {
    pane.classList.toggle('active', pane.id === tabId);
  });
}

function wireTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      if (tabId) switchTab(tabId);
    });
  });
}

function formatInline(str) {
  if (!str) return '';
  let escaped = escapeHtml(str);

  // Inline code: `code`
  escaped = escaped.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

  // Markdown links: [Text](url)
  escaped = escaped.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1 ↗</a>');

  // Bold & Italic: ***text***
  escaped = escaped.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');

  // Bold: **text** or __text__
  escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  escaped = escaped.replace(/__([^_]+)__/g, '<strong>$1</strong>');

  // Italic: *text* or _text_
  escaped = escaped.replace(/(^|[^\*])\*([^\*]+)\*([^\*]|$)/g, '$1<em>$2</em>$3');
  escaped = escaped.replace(/(^|[^_])_([^_]+)_([^_]|$)/g, '$1<em>$2</em>$3');

  // Interactive Citation Pills: [E1], [E2], [E1, E2], [P1], etc.
  escaped = escaped.replace(/\[((?:[EPC]\d+)(?:\s*,\s*(?:[EPC]\d+))*)\]/g, (match, ids) => {
    const parts = ids.split(',').map((s) => s.trim());
    return parts.map((id) => `<button type="button" class="cite-pill" data-cite="${id}">[${id}]</button>`).join(' ');
  });

  return escaped;
}

function renderMarkdown(md) {
  if (!md) return '';

  let text = md.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // Extract fenced code blocks first so inner content is untouched
  const codeBlocks = [];
  text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre class="code-block"><code>${escapeHtml(code.trim())}</code></pre>`);
    return `__CODE_BLOCK_${idx}__`;
  });

  const lines = text.split('\n');
  const output = [];
  let inList = false;
  let listType = '';
  let inTable = false;
  let tableHeader = [];
  let tableRows = [];
  let currentPara = [];

  function flushPara() {
    if (currentPara.length > 0) {
      output.push(`<p>${formatInline(currentPara.join(' '))}</p>`);
      currentPara = [];
    }
  }

  function closeList() {
    if (inList) {
      output.push(`</${listType}>`);
      inList = false;
      listType = '';
    }
  }

  function closeTable() {
    if (inTable) {
      let html = '<div class="table-container"><table class="md-table">';
      if (tableHeader.length > 0) {
        html += '<thead><tr>';
        for (const cell of tableHeader) {
          html += `<th>${cell}</th>`;
        }
        html += '</tr></thead>';
      }
      if (tableRows.length > 0) {
        html += '<tbody>';
        for (const row of tableRows) {
          html += '<tr>';
          for (const cell of row) {
            html += `<td>${cell}</td>`;
          }
          html += '</tr>';
        }
        html += '</tbody>';
      }
      html += '</table></div>';
      output.push(html);
      inTable = false;
      tableHeader = [];
      tableRows = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Code block placeholder
    if (/^__CODE_BLOCK_\d+__$/.test(trimmed)) {
      flushPara();
      closeList();
      closeTable();
      output.push(trimmed);
      continue;
    }

    // Markdown table row: | a | b | c |
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 2) {
      flushPara();
      closeList();
      const isSeparator = /^\|(\s*:?-+:?\s*\|)+$/.test(trimmed);
      if (isSeparator) {
        continue;
      }
      const cells = trimmed
        .slice(1, -1)
        .split('|')
        .map((c) => formatInline(c.trim()));

      if (!inTable) {
        inTable = true;
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    } else {
      closeTable();
    }

    // Blank line
    if (!trimmed) {
      flushPara();
      closeList();
      continue;
    }

    // Blockquote: > text
    if (trimmed.startsWith('>')) {
      flushPara();
      closeList();
      const content = formatInline(trimmed.replace(/^>\s*/, ''));
      output.push(`<blockquote>${content}</blockquote>`);
      continue;
    }

    // Headers: #, ##, ###, ####
    const headerMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headerMatch) {
      flushPara();
      closeList();
      const level = headerMatch[1].length;
      const content = formatInline(headerMatch[2]);
      output.push(`<h${level}>${content}</h${level}>`);
      continue;
    }

    // Unordered list item: -, *, +
    const ulMatch = trimmed.match(/^[-*+]\s+(.+)$/);
    if (ulMatch) {
      flushPara();
      if (!inList || listType !== 'ul') {
        closeList();
        inList = true;
        listType = 'ul';
        output.push('<ul class="md-list">');
      }
      output.push(`<li>${formatInline(ulMatch[1])}</li>`);
      continue;
    }

    // Ordered list item: 1.
    const olMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (olMatch) {
      flushPara();
      if (!inList || listType !== 'ol') {
        closeList();
        inList = true;
        listType = 'ol';
        output.push('<ol class="md-list">');
      }
      output.push(`<li>${formatInline(olMatch[2])}</li>`);
      continue;
    }

    // Regular text line
    closeList();
    currentPara.push(trimmed);
  }

  flushPara();
  closeList();
  closeTable();

  let resultHtml = output.join('\n');
  resultHtml = resultHtml.replace(/__CODE_BLOCK_(\d+)__/g, (match, idx) => {
    return codeBlocks[Number(idx)] || '';
  });

  return resultHtml;
}

function attachCitationListeners() {
  document.querySelectorAll('.cite-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      e.preventDefault();
      const cite = pill.getAttribute('data-cite');
      if (!cite) return;

      // Automatically switch to the Evidence tab
      switchTab('tab-evidence');

      setTimeout(() => {
        const target = byId(`evidence-${cite}`);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
          target.classList.remove('highlight-flash');
          void target.offsetWidth;
          target.classList.add('highlight-flash');
        }
      }, 50);
    });
  });
}

async function refreshStatus() {
  try {
    const [statusResponse, documentsResponse] = await Promise.all([
      fetch('/api/status'),
      fetch('/api/documents'),
    ]);
    if (!statusResponse.ok) throw new Error(`Status request failed (${statusResponse.status})`);
    if (!documentsResponse.ok) throw new Error(`Documents request failed (${documentsResponse.status})`);
    const [status, documents] = await Promise.all([
      statusResponse.json(),
      documentsResponse.json(),
    ]);
    const count = status.corpus_files;
    const dot = '<span class="status-dot"></span> ';
    const text = count === 0
      ? `No PDFs in corpus`
      : `${count} PDF${count === 1 ? '' : 's'} indexed`;
    byId('corpus-status').innerHTML = dot + escapeHtml(text);
    renderDocuments(documents);
  } catch (error) {
    byId('corpus-status').innerHTML = '<span class="status-dot" style="background:#e55353"></span> Offline';
    byId('document-options').replaceChildren(element('span', 'Reports unavailable', 'loading-hint'));
  }
}

function updateDocCardStyles() {
  const allCards = document.querySelectorAll('.sidebar-doc-card');
  const allCheckboxes = Array.from(document.querySelectorAll('input[name="document_ids"]'));
  const allChecked = allCheckboxes.length > 0 && allCheckboxes.every((cb) => cb.checked);

  allCards.forEach((card) => {
    const cb = card.querySelector('input[type="checkbox"]');
    if (cb && cb.checked) {
      card.classList.add('selected');
    } else {
      card.classList.remove('selected');
    }
  });

  const selectAllBtn = byId('select-all-btn');
  if (selectAllBtn) {
    selectAllBtn.textContent = allChecked ? 'Deselect All' : 'Select All';
  }
}

function renderDocuments(documents) {
  const container = byId('document-options');
  const running = byId('ask-button') ? byId('ask-button').disabled : false;
  container.replaceChildren();

  if (!Array.isArray(documents) || documents.length === 0) {
    container.append(element('span', 'No indexed reports found', 'loading-hint'));
    return;
  }

  for (const report of documents) {
    const card = element('label', '', 'sidebar-doc-card');
    card.setAttribute('data-id', report.document_id);

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'document_ids';
    checkbox.value = report.document_id;
    // Checked if in persistent selectedDocIds
    checkbox.checked = selectedDocIds.has(report.document_id);
    checkbox.disabled = running;

    const info = element('div', '', 'doc-card-info');
    const nameEl = element('span', report.name || report.document_id, 'doc-card-name');
    info.append(nameEl);

    if (typeof report.pages === 'number') {
      const metaEl = element('span', `${report.pages} pages · 10-K`, 'doc-card-meta');
      info.append(metaEl);
    }

    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        selectedDocIds.add(report.document_id);
      } else {
        selectedDocIds.delete(report.document_id);
      }
      saveSelectedDocIds();
      updateDocCardStyles();
    });

    card.append(checkbox, info);
    container.append(card);
  }

  updateDocCardStyles();
}

function renderAnswer(result) {
  byId('answer-panel').classList.remove('hidden');

  // Verdict badge
  const badge = byId('answer-badge');
  if (badge) {
    if (result.status === 'verified') {
      badge.textContent = 'VERIFIED';
      badge.className = 'verdict-badge';
    } else if (result.status === 'no_answer') {
      badge.textContent = 'NO SUFFICIENT EVIDENCE';
      badge.className = 'verdict-badge no-answer';
    } else {
      badge.textContent = (result.status || 'UNVERIFIED').toUpperCase();
      badge.className = 'verdict-badge no-answer';
    }
  }

  // Always show Answer tab by default for a new answer
  switchTab('tab-answer');

  // Render markdown answer
  const answerContainer = byId('answer-text');
  answerContainer.innerHTML = renderMarkdown(result.answer || 'No answer provided.');

  const evidence = Array.isArray(result.evidence) ? result.evidence : [];
  const metadata = result.metadata || {};
  const details = [];
  if (typeof metadata.latency_seconds === 'number') {
    details.push(`${metadata.latency_seconds.toFixed(1)}s`);
  }
  if (metadata.model) {
    details.push(metadata.model);
  }
  if (typeof metadata.tool_calls === 'number' && metadata.tool_calls > 0) {
    details.push(`${metadata.tool_calls} tool call${metadata.tool_calls === 1 ? '' : 's'}`);
  }
  byId('answer-meta').textContent = details.join(' · ');

  // Verified Calculations Tab
  const calcs = Array.isArray(result.calculations) ? result.calculations : [];
  const calcsTabBtn = byId('tab-btn-calcs');
  const calcsTabBadge = byId('calcs-count-tab');
  const calcsList = byId('calculations-list');
  if (calcs.length > 0) {
    if (calcsTabBtn) calcsTabBtn.classList.remove('hidden');
    if (calcsTabBadge) calcsTabBadge.textContent = String(calcs.length);
    calcsList.replaceChildren();
    for (const calc of calcs) {
      const card = element('div', '', 'calc-card');
      const label = element('div', calc.label || 'Verified Calculation', 'calc-label');
      const eq = document.createElement('div');
      eq.className = 'calc-equation';
      eq.append(document.createTextNode(`${calc.expression} = `));
      const resSpan = element('span', String(calc.result), 'calc-result');
      eq.append(resSpan);
      card.append(label, eq);

      const notes = [];
      if (Array.isArray(calc.scale_constants) && calc.scale_constants.length > 0) {
        notes.push(`Scale: ${calc.scale_constants.join(', ')}`);
      }
      if (Array.isArray(calc.operand_evidence_ids) && calc.operand_evidence_ids.length > 0) {
        notes.push(`Evidence: ${calc.operand_evidence_ids.join(', ')}`);
      }
      if (notes.length > 0) {
        card.append(element('div', notes.join(' · '), 'calc-notes'));
      }
      calcsList.append(card);
    }
  } else {
    if (calcsTabBtn) calcsTabBtn.classList.add('hidden');
    calcsList.replaceChildren();
  }

  // Evidence Tab
  const evidenceCountTab = byId('evidence-count-tab');
  if (evidenceCountTab) {
    evidenceCountTab.textContent = String(evidence.length);
  }
  const list = byId('evidence-list');
  list.replaceChildren();

  evidence.forEach((item, index) => {
    const card = element('article', '', 'evidence-card');
    const label = item.citation_label || `E${index + 1}`;
    card.id = `evidence-${label}`;

    const top = element('div', '', 'evidence-top');
    top.append(element('span', label, 'evidence-tag'));

    const locParts = [];
    if (item.document_id) locParts.push(item.document_id);
    if (typeof item.page === 'number') locParts.push(`Page ${item.page}`);
    if (item.element_type) locParts.push(item.element_type);
    top.append(element('span', locParts.join(' · '), 'evidence-location'));
    card.append(top);

    if (Array.isArray(item.section_path) && item.section_path.length > 0) {
      card.append(element('div', item.section_path.join(' › '), 'evidence-path'));
    }

    const bodyEl = element('div', '', 'evidence-body');
    bodyEl.innerHTML = renderMarkdown(item.text || '');
    card.append(bodyEl);

    if (item.source_url) {
      const link = document.createElement('a');
      link.href = item.source_url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = `${item.source_title || item.source_url} ↗`;
      card.append(link);
    }

    list.append(card);
  });

  // Wire citation button clicks
  attachCitationListeners();

  // Smooth scroll to answer
  byId('answer-panel').scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
}

async function ask(event) {
  event.preventDefault();
  const question = byId('question').value.trim();
  if (!question) return;

  // Use persistent selectedDocIds: if empty, send [] to search all documents by default
  const documentIds = Array.from(selectedDocIds);

  byId('ask-button').disabled = true;
  const selectAllBtn = byId('select-all-btn');
  if (selectAllBtn) selectAllBtn.disabled = true;
  document.querySelectorAll('input[name="document_ids"]').forEach((checkbox) => { checkbox.disabled = true; });
  byId('answer-panel').classList.add('hidden');
  setAskState('Checking corpus…', true);

  try {
    const response = await fetch('/api/ask/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, document_ids: documentIds }),
    });

    if (!response.ok || !response.body) {
      const body = await response.text();
      let message = body;
      try { message = JSON.parse(body).detail || body; } catch (_) {}
      throw new Error(message || `Request failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let receivedAnswer = false;

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const messages = buffer.split('\n\n');
      buffer = messages.pop() || '';

      for (const message of messages) {
        const line = message.split('\n').find((part) => part.startsWith('data: '));
        if (!line) continue;
        const update = JSON.parse(line.slice(6));
        if (update.event === 'error') throw new Error(update.error);
        if (update.event === 'indexing') {
          setAskState(update.files > 0 ? 'Indexing corpus…' : 'Checking corpus…', true);
        } else if (update.event === 'indexed') {
          setAskState('Researching answer…', true);
          await refreshStatus();
        } else if (update.event === 'step' && update.node) {
          const stepName = update.node.replaceAll('_', ' ');
          setAskState(`${stepName} in progress…`, true);
        } else if (update.event === 'answer') {
          renderAnswer(update.data);
          setAskState('');
          receivedAnswer = true;
        }
      }
      if (done) break;
    }
    if (!receivedAnswer) throw new Error('The answer stream ended without a result');
  } catch (error) {
    setAskState(`Unable to answer: ${error.message}`);
  } finally {
    byId('ask-button').disabled = false;
    const selectAllBtn = byId('select-all-btn');
    if (selectAllBtn) selectAllBtn.disabled = false;
    document.querySelectorAll('input[name="document_ids"]').forEach((checkbox) => {
      checkbox.disabled = false;
    });
  }
}

const selectAllBtn = byId('select-all-btn');
if (selectAllBtn) {
  selectAllBtn.addEventListener('click', () => {
    const allBoxes = Array.from(document.querySelectorAll('input[name="document_ids"]'));
    if (allBoxes.length === 0) return;
    const allChecked = allBoxes.every((cb) => cb.checked);
    const targetState = !allChecked;
    allBoxes.forEach((cb) => {
      cb.checked = targetState;
      if (targetState) {
        selectedDocIds.add(cb.value);
      } else {
        selectedDocIds.delete(cb.value);
      }
    });
    saveSelectedDocIds();
    updateDocCardStyles();
  });
}

const formEl = byId('question-form');
if (formEl) {
  formEl.addEventListener('submit', ask);
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  wireTabs();
  refreshStatus();
}
