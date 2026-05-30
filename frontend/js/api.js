const API_BASE = '/api';

async function apiGetVideoInfo(url) {
    const params = new URLSearchParams({ url });
    const res = await fetch(`${API_BASE}/video-info?${params}`);
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to fetch video info');
    }
    return res.json();
}

async function apiStartProcess(url, clipDuration, subtitleLang, aspectRatio, numHighlights) {
    const res = await fetch(`${API_BASE}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            url,
            clip_duration: clipDuration,
            subtitle_lang: subtitleLang,
            aspect_ratio: aspectRatio,
            num_highlights: numHighlights,
        }),
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start processing');
    }
    return res.json();
}

async function apiGetStatus(jobId) {
    const res = await fetch(`${API_BASE}/status/${jobId}`);
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to get status');
    }
    return res.json();
}

function apiGetPreviewUrl(jobId, index) {
    return `${API_BASE}/preview/${jobId}/${index}`;
}

function apiGetDownloadUrl(jobId, index) {
    return `${API_BASE}/download/${jobId}/${index}`;
}
