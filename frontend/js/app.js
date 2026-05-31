let currentJobId = null;
let currentUrl = null;
let pollInterval = null;
let editorHighlights = [];
let appConfig = null;

async function initToken() {
    if (getToken()) return;
    try {
        const res = await fetch('/api/config');
        if (res.ok) {
            appConfig = await res.json();
            if (appConfig.token) {
                setToken(appConfig.token);
            }
            updateProviderHints();
        }
    } catch (_) {
        // ignore
    }
}

function updateProviderHints() {
    if (!appConfig) return;
    const openaiOpt = document.querySelector('#llm-provider option[value="openai"]');
    const anthropicOpt = document.querySelector('#llm-provider option[value="anthropic"]');

    if (openaiOpt) {
        openaiOpt.textContent = appConfig.has_openai_key
            ? "OpenAI (GPT-4o-mini) ✓"
            : "OpenAI (GPT-4o-mini)";
    }
    if (anthropicOpt) {
        anthropicOpt.textContent = appConfig.has_anthropic_key
            ? "Anthropic (Claude Sonnet) ✓"
            : "Anthropic (Claude Sonnet)";
    }
}

function resetApp() {
    currentJobId = null;
    currentUrl = null;
    editorHighlights = [];
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
    hideAllSteps();
    document.getElementById('url-input').value = '';
    document.getElementById('url-error').classList.add('hidden');
    showStep('step-url');
}

async function fetchVideoInfo() {
    const input = document.getElementById('url-input');
    const btn = document.getElementById('btn-fetch');
    const errorEl = document.getElementById('url-error');
    const url = input.value.trim();

    errorEl.classList.add('hidden');

    if (!url) {
        errorEl.textContent = 'Please enter a YouTube URL';
        errorEl.classList.remove('hidden');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
        const info = await apiGetVideoInfo(url);
        currentUrl = url;
        renderVideoInfo(info);
        hideAllSteps();
        showStep('step-url');
        showStep('step-settings');
    } catch (err) {
        errorEl.textContent = err.message;
        errorEl.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze';
    }
}

async function startProcessing() {
    if (!currentUrl) {
        showError('Please analyze a YouTube URL first');
        return;
    }

    const clipDuration = document.getElementById('clip-duration').value;
    const subtitleLang = document.getElementById('subtitle-lang').value;
    const aspectRatio = document.getElementById('aspect-ratio').value;
    const numHighlights = parseInt(document.getElementById('num-highlights').value, 10);
    const detectionMode = document.querySelector('input[name="detection-mode"]:checked').value;
    const enhancement = {
        upscale: document.getElementById('enh-upscale').checked,
        color_correct: document.getElementById('enh-color').checked,
        denoise: document.getElementById('enh-denoise').checked,
        audio_normalize: document.getElementById('enh-audio').checked,
        karaoke_subs: document.getElementById('enh-karaoke').checked,
        add_intro: document.getElementById('use-intro').checked,
        add_outro: document.getElementById('use-outro').checked,
    };
    const intro_outro = {
        intro_text: document.getElementById('intro-text').value.trim(),
        outro_text: document.getElementById('outro-text').value.trim(),
    };
    const llm = {
        provider: document.getElementById('llm-provider').value,
        api_key: document.getElementById('llm-api-key').value.trim(),
        model: document.getElementById('llm-model').value.trim(),
    };

    editorHighlights = [];
    hideAllSteps();
    showStep('step-processing');
    updateProgressBar(0, 'Starting...');

    try {
        const { job_id } = await apiStartProcess(currentUrl, clipDuration, subtitleLang, aspectRatio, numHighlights, enhancement, intro_outro, detectionMode, llm);
        currentJobId = job_id;
        startPolling(job_id);
    } catch (err) {
        showError(err.message);
    }
}

function startPolling(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const status = await apiGetStatus(jobId);
            handleStatusUpdate(status);
        } catch (err) {
            clearInterval(pollInterval);
            showError(err.message);
        }
    }, 1500);
}

function handleStatusUpdate(status) {
    updateProgressBar(status.progress, status.message);
    updateStageIndicators(status.stage);

    if (status.stage === 'ready_for_review') {
        clearInterval(pollInterval);
        showEditor(status.highlights || []);
    } else if (status.stage === 'complete') {
        clearInterval(pollInterval);
        showPreview(currentJobId, status.outputs || []);
    } else if (status.stage === 'error') {
        clearInterval(pollInterval);
        showError(status.message);
    }
}

// ── Highlight Editor ─────────────────────────────────────────────

function showEditor(highlights) {
    editorHighlights = highlights.map(h => ({ ...h }));
    renderEditor();
    hideAllSteps();
    showStep('step-review');
}

function renderEditor() {
    const container = document.getElementById('editor-list');
    container.innerHTML = '';

    editorHighlights.forEach((hl, i) => {
        const row = document.createElement('div');
        row.className = 'flex items-center gap-2 bg-dark-800 rounded-lg p-3 border border-dark-600';

        row.innerHTML = `
            <span class="text-dark-500 text-sm font-mono w-6">${i + 1}</span>
            <div class="flex gap-2 flex-1">
                <div class="flex flex-col">
                    <label class="text-xs text-dark-500">Start</label>
                    <input type="number" step="0.1" min="0" value="${hl.start.toFixed(1)}"
                        class="editor-start w-24 bg-dark-700 border border-dark-500 rounded px-2 py-1 text-sm text-dark-100 font-mono"
                        data-index="${i}">
                </div>
                <span class="text-dark-500 self-end pb-1">—</span>
                <div class="flex flex-col">
                    <label class="text-xs text-dark-500">End</label>
                    <input type="number" step="0.1" min="0" value="${hl.end.toFixed(1)}"
                        class="editor-end w-24 bg-dark-700 border border-dark-500 rounded px-2 py-1 text-sm text-dark-100 font-mono"
                        data-index="${i}">
                </div>
                <div class="flex flex-col flex-1">
                    <label class="text-xs text-dark-500">Text</label>
                    <input type="text" value="${escapeHtml(hl.text || '')}"
                        class="editor-text flex-1 bg-dark-700 border border-dark-500 rounded px-2 py-1 text-sm text-dark-100"
                        data-index="${i}">
                </div>
            </div>
            <button onclick="removeHighlight(${i})" class="text-red-400 hover:text-red-300 px-2 py-1 text-sm">✕</button>
        `;

        container.appendChild(row);
    });

    container.querySelectorAll('.editor-start, .editor-end, .editor-text').forEach(input => {
        input.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.index);
            if (e.target.classList.contains('editor-start')) {
                editorHighlights[idx].start = parseFloat(e.target.value) || 0;
            } else if (e.target.classList.contains('editor-end')) {
                editorHighlights[idx].end = parseFloat(e.target.value) || 0;
            } else if (e.target.classList.contains('editor-text')) {
                editorHighlights[idx].text = e.target.value;
            }
        });
    });
}

function addHighlight() {
    const last = editorHighlights[editorHighlights.length - 1];
    const newStart = last ? last.end + 1 : 0;
    editorHighlights.push({
        start: newStart,
        end: newStart + 30,
        score: 0,
        text: '',
    });
    renderEditor();
}

function removeHighlight(index) {
    editorHighlights.splice(index, 1);
    renderEditor();
}

async function confirmHighlights() {
    if (editorHighlights.length === 0) {
        showError('Add at least one highlight');
        return;
    }

    for (let i = 0; i < editorHighlights.length; i++) {
        const hl = editorHighlights[i];
        if (hl.end <= hl.start) {
            showError(`Highlight ${i + 1}: end must be after start`);
            return;
        }
    }

    hideAllSteps();
    showStep('step-processing');
    updateProgressBar(70, 'Processing edited highlights...');

    try {
        await apiConfirmHighlights(currentJobId, editorHighlights);
        startPolling(currentJobId);
    } catch (err) {
        showError(err.message);
    }
}

// ── Preview ──────────────────────────────────────────────────────

function showPreview(jobId, outputs) {
    hideAllSteps();

    const container = document.getElementById('clips-container');
    container.innerHTML = '';

    if (outputs.length === 0) {
        container.innerHTML = '<p class="text-dark-400 text-center">No clips generated.</p>';
    } else {
        for (const output of outputs) {
            const card = renderClipCard(jobId, output);
            container.appendChild(card);
        }
    }

    showStep('step-preview');
}

document.getElementById('url-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') fetchVideoInfo();
});

initToken().then(() => resetApp());
