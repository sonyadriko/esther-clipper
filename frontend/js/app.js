let currentJobId = null;
let currentUrl = null;
let pollInterval = null;
let highlightsRendered = false;

function resetApp() {
    currentJobId = null;
    currentUrl = null;
    highlightsRendered = false;
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

    highlightsRendered = false;
    hideAllSteps();
    showStep('step-processing');
    updateProgressBar(0, 'Starting...');

    try {
        const { job_id } = await apiStartProcess(currentUrl, clipDuration, subtitleLang, aspectRatio, numHighlights);
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

    if (status.highlights && status.highlights.length > 0 && !highlightsRendered) {
        renderHighlights(status.highlights);
        highlightsRendered = true;
    }

    if (status.stage === 'complete') {
        clearInterval(pollInterval);
        showPreview(currentJobId, status.outputs || []);
    } else if (status.stage === 'error') {
        clearInterval(pollInterval);
        showError(status.message);
    }
}

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

    showStep('step-highlights');
    showStep('step-preview');
}

document.getElementById('url-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') fetchVideoInfo();
});

resetApp();
