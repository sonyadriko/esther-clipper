function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDuration(seconds) {
    seconds = Math.floor(seconds);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function showError(message) {
    hideAllSteps();
    document.getElementById('error-message').textContent = message;
    document.getElementById('step-error').classList.remove('hidden');
}

function hideAllSteps() {
    document.querySelectorAll('.step').forEach(el => el.classList.add('hidden'));
}

function showStep(id) {
    document.getElementById(id).classList.remove('hidden');
}

function updateProgressBar(progress, label) {
    document.getElementById('progress-bar').style.width = `${progress}%`;
    document.getElementById('progress-percent').textContent = `${progress}%`;
    if (label) {
        document.getElementById('progress-label').textContent = label;
    }
}

function updateStageIndicators(currentStage) {
    const stages = ['downloading', 'transcribing', 'analyzing', 'ready_for_review', 'editing'];
    const currentIndex = stages.indexOf(currentStage);

    stages.forEach((stage, i) => {
        const el = document.getElementById(`stage-${stage}`);
        el.classList.remove('stage-active', 'stage-done');
        if (i < currentIndex) {
            el.classList.add('stage-done');
        } else if (i === currentIndex) {
            el.classList.add('stage-active');
        }
    });
}

function renderVideoInfo(info) {
    document.getElementById('video-thumb').src = info.thumbnail;
    document.getElementById('video-title').textContent = info.title;
    document.getElementById('video-channel').textContent = info.channel;
    document.getElementById('video-duration').textContent = `Duration: ${formatDuration(info.duration)}`;
}

function renderHighlights(highlights) {
    const container = document.getElementById('highlights-list');
    container.innerHTML = '';
    for (const h of highlights) {
        const item = document.createElement('div');
        item.className = 'highlight-item flex items-center justify-between p-3 rounded-lg bg-dark-800';

        const info = document.createElement('div');
        info.className = 'flex-1';

        const time = document.createElement('span');
        time.className = 'text-blue-400 font-mono text-sm';
        time.textContent = `${formatTime(h.start)} — ${formatTime(h.end)}`;

        const text = document.createElement('p');
        text.className = 'text-dark-300 text-sm mt-1 line-clamp-2';
        text.textContent = h.text || 'No transcript';

        info.appendChild(time);
        info.appendChild(text);

        const score = document.createElement('span');
        score.className = 'text-dark-500 text-xs ml-3';
        score.textContent = `Score: ${h.score}`;

        item.appendChild(info);
        item.appendChild(score);
        container.appendChild(item);
    }
}

function renderClipCard(jobId, output) {
    const card = document.createElement('div');
    card.className = 'bg-dark-800 rounded-xl p-4 border border-dark-600';

    const header = document.createElement('div');
    header.className = 'flex items-center justify-between mb-3';

    const title = document.createElement('h3');
    title.className = 'font-semibold text-lg';
    title.textContent = `Highlight ${output.index + 1}`;

    const time = document.createElement('span');
    time.className = 'text-blue-400 font-mono text-sm';
    const hl = output.highlight;
    time.textContent = `${formatTime(hl.start)} — ${formatTime(hl.end)}`;

    header.appendChild(title);
    header.appendChild(time);

    const text = document.createElement('p');
    text.className = 'text-dark-300 text-sm mb-3 line-clamp-2';
    text.textContent = hl.text || '';

    const video = document.createElement('video');
    video.controls = true;
    video.className = 'w-full rounded-lg bg-black mb-3';
    video.style.maxHeight = '300px';
    video.src = apiGetPreviewUrl(jobId, output.index);

    const btnRow = document.createElement('div');
    btnRow.className = 'flex gap-3';

    const downloadBtn = document.createElement('a');
    downloadBtn.href = apiGetDownloadUrl(jobId, output.index);
    downloadBtn.download = true;
    downloadBtn.className = 'flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-medium text-center transition-colors text-sm';
    downloadBtn.textContent = 'Download MP4';

    btnRow.appendChild(downloadBtn);

    card.appendChild(header);
    if (hl.text) card.appendChild(text);
    card.appendChild(video);
    card.appendChild(btnRow);

    return card;
}
