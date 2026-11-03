(() => {
  const $ = (selector) => document.querySelector(selector);
  const docSearch = $('#doc-search');
  const docList = $('#doc-list');
  const documentSelect = $('#document');
  const methodSelect = $('#method');
  const methodDescription = $('#method-description');
  const question = $('#question');
  const askButton = $('#ask-button');
  const status = $('#status');
  let documents = [];
  let methods = {};
  let selectedDoc = '';

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));

  function renderDocs(filter = '') {
    const matches = documents.filter((name) => name.toLowerCase().includes(filter.trim().toLowerCase()));
    docList.innerHTML = matches.length ? matches.map((name) => `
      <button class="doc-option ${name === selectedDoc ? 'active' : ''}" type="button" data-doc="${escapeHtml(name)}" aria-pressed="${name === selectedDoc}">
        <span class="doc-indicator" aria-hidden="true"></span><span>${escapeHtml(name.replaceAll('_', ' '))}</span>
      </button>`).join('') : '<p class="muted">No filings match your search.</p>';
    docList.querySelectorAll('[data-doc]').forEach((button) => button.addEventListener('click', () => selectDocument(button.dataset.doc)));
  }

  function selectDocument(name) {
    selectedDoc = name;
    documentSelect.value = name;
    renderDocs(docSearch.value);
  }

  function updateMethod() {
    methodDescription.textContent = methods[methodSelect.value]?.description || '';
  }

  function showSources(sources) {
    $('#source-count').textContent = sources.length;
    $('#sources').innerHTML = sources.length ? sources.map((source) => {
      const page = source.page ? `Page ${escapeHtml(source.page)}` : 'Page unavailable';
      const tags = [source.kind, ...(source.methods || [])].filter(Boolean);
      const score = source.score != null && Number.isFinite(Number(source.score)) ? `Score ${Number(source.score).toFixed(3)}` : '';
      if (score) tags.push(score);
      return `<details class="source"><summary><span class="rank">#${escapeHtml(source.rank)}</span><span>${page} · ${escapeHtml(source.kind || 'Evidence')}</span></summary>
        <div class="source-tags">${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>
        <pre class="source-text">${escapeHtml(source.text || '')}</pre>${source.truncated ? '<p class="truncated">Passage shortened for display.</p>' : ''}</details>`;
    }).join('') : '<p class="empty-evidence">No evidence passages were returned.</p>';
  }

  function showAgent(agent) {
    const panel = $('#agent-status');
    if (!agent) { panel.hidden = true; panel.textContent = ''; return; }
    const verification = agent.verification_supported === true ? 'Supported by the retrieved evidence' :
      agent.verification_supported === false ? 'Verifier flagged unsupported claims' : 'Verification status unavailable';
    const sufficiency = agent.evidence_sufficient === true ? 'Evidence coverage: sufficient' : 'Evidence coverage: gaps remained';
    const queries = (agent.retrieval_queries || []).map(escapeHtml).join(' · ');
    const issues = (agent.verification_issues || []).map(escapeHtml).join(' · ');
    panel.innerHTML = `<strong>Agent review</strong><br>${sufficiency} · ${Number(agent.retrieval_rounds || 0)} follow-up rounds<br>${verification}${issues ? `<br>Review notes: ${issues}` : ''}${queries ? `<br>Searches: ${queries}` : ''}`;
    panel.hidden = false;
  }

  async function initialize() {
    try {
      const response = await fetch('/api/config');
      if (!response.ok) throw new Error('Could not load the local FinanceBench configuration.');
      const data = await response.json();
      documents = data.documents || [];
      methods = data.methods || {};
      $('#doc-count').textContent = documents.length;
      documentSelect.innerHTML = documents.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name.replaceAll('_', ' '))}</option>`).join('');
      methodSelect.innerHTML = Object.entries(methods).map(([key, method]) => `<option value="${escapeHtml(key)}">${escapeHtml(method.label)}</option>`).join('');
      selectedDoc = documents[0] || '';
      if (selectedDoc) documentSelect.value = selectedDoc;
      renderDocs();
      updateMethod();
    } catch (error) {
      docList.innerHTML = `<p class="muted">${escapeHtml(error.message)}</p>`;
      setStatus(error.message, true);
    }
  }

  function setStatus(message, isError = false, isLoading = false) {
    status.textContent = message;
    status.className = `status-message${isError ? ' error' : ''}${isLoading ? ' loading' : ''}`;
    status.hidden = !message;
  }

  async function ask(event) {
    event.preventDefault();
    const prompt = question.value.trim();
    if (!prompt) { question.focus(); return; }
    askButton.disabled = true;
    askButton.querySelector('span:first-child').textContent = 'Searching the filing…';
    setStatus('Preparing the selected method and searching for supporting passages. First use may take longer while indexes are built.', false, true);
    try {
      const response = await fetch('/api/ask', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({method: methodSelect.value, document: documentSelect.value, question: prompt})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
      $('#answer').textContent = data.answer || 'No answer returned.';
      $('#result-title').textContent = 'Answer';
      $('#result-meta').textContent = `${data.method} · ${data.document.replaceAll('_', ' ')} · ${data.elapsed_seconds}s`;
      showSources(data.sources || []);
      showAgent(data.agent);
      $('#result').hidden = false;
      $('#result').scrollIntoView({behavior: 'smooth', block: 'start'});
      setStatus('Answer ready. Expand a passage to inspect its source text.');
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      askButton.disabled = false;
      askButton.querySelector('span:first-child').textContent = 'Ask question';
    }
  }

  docSearch.addEventListener('input', () => renderDocs(docSearch.value));
  documentSelect.addEventListener('change', () => { selectedDoc = documentSelect.value; renderDocs(docSearch.value); });
  methodSelect.addEventListener('change', updateMethod);
  $('#ask-form').addEventListener('submit', ask);
  question.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('#ask-form').requestSubmit(); }
  });
  initialize();
})();
