const API_BASE = '/api';

function getToken() {
    return localStorage.getItem('api_token') || '';
}

function setToken(token) {
    localStorage.setItem('api_token', token);
}

function clearToken() {
    localStorage.removeItem('api_token');
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`,
    };
}

async function apiGetVideoInfo(url) {
    const params = new URLSearchParams({ url });
    const res = await fetch(`${API_BASE}/video-info?${params}`, {
        headers: authHeaders(),
    });
    if (res.status === 401) {
        clearToken();
        throw new Error('Invalid token');
    }
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to fetch video info');
    }
    return res.json();
}

async function apiStartProcess(url, clipDuration, subtitleLang, aspectRatio, numHighlights, enhancement, introOutro, detectionMode, llm) {
    const res = await fetch(`${API_BASE}/process`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
            url,
            clip_duration: clipDuration,
            subtitle_lang: subtitleLang,
            aspect_ratio: aspectRatio,
            num_highlights: numHighlights,
            enhancement,
            intro_outro: introOutro,
            detection_mode: detectionMode,
            llm,
        }),
    });
    if (res.status === 401) {
        clearToken();
        throw new Error('Invalid token');
    }
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start processing');
    }
    return res.json();
}

async function apiGetStatus(jobId) {
    const res = await fetch(`${API_BASE}/status/${jobId}`, {
        headers: authHeaders(),
    });
    if (res.status === 401) {
        clearToken();
        throw new Error('Invalid token');
    }
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to get status');
    }
    return res.json();
}

function apiGetPreviewUrl(jobId, index) {
    return `${API_BASE}/preview/${jobId}/${index}?token=${encodeURIComponent(getToken())}`;
}

function apiGetDownloadUrl(jobId, index) {
    return `${API_BASE}/download/${jobId}/${index}?token=${encodeURIComponent(getToken())}`;
}

function apiGetSrtDownloadUrl(jobId, index) {
    return `${API_BASE}/download-srt/${jobId}/${index}?token=${encodeURIComponent(getToken())}`;
}

async function apiConfirmHighlights(jobId, highlights) {
    const res = await fetch(`${API_BASE}/confirm/${jobId}`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ highlights }),
    });
    if (res.status === 401) {
        clearToken();
        throw new Error('Invalid token');
    }
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to confirm highlights');
    }
    return res.json();
}
