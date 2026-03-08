/**
 * LeaderAtWorship — Subtitle Sync Player
 *
 * Loads song metadata + subtitle lines, sets up HTML5 audio player,
 * and synchronizes subtitle highlighting with audio playback.
 *
 * Requires: SONG_ID global variable set by the template.
 */

let song = null;
let subtitleLines = [];
let currentLineIndex = -1;
let isSeeking = false;

// ── Helpers ────────────────────────────────────────────────

function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatTimeFromSeconds(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Binary Search for Current Subtitle Line ────────────────

function findCurrentLine(currentMs) {
    if (subtitleLines.length === 0) return -1;

    let lo = 0;
    let hi = subtitleLines.length - 1;
    let result = -1;

    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (subtitleLines[mid].start_ms <= currentMs) {
            result = mid;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }

    // Check if we're still within this line's end_ms
    if (result >= 0 && currentMs > subtitleLines[result].end_ms) {
        return -1; // In a gap between lines
    }
    return result;
}

// ── Render ──────────────────────────────────────────────────

function renderSongHeader(song) {
    document.getElementById('song-title').textContent = song.title;
    const parts = [];
    if (song.artist) parts.push(song.artist);
    if (song.key_signature) parts.push(`調性: ${song.key_signature}`);
    if (song.tempo_bpm) parts.push(`${song.tempo_bpm} BPM`);
    document.getElementById('song-meta').textContent = parts.join(' | ');
}

function renderSubtitleLines(lines) {
    const container = document.getElementById('subtitle-lines');
    container.innerHTML = lines.map((line, i) => `
        <div class="subtitle-line" data-index="${i}" data-start-ms="${line.start_ms}"
             data-source="${line.source_type || ''}">
            <span class="line-time">${formatTime(line.start_ms)}</span>
            <span class="line-text">${line.text}</span>
            ${line.text_secondary ? `<span class="line-text-secondary">${line.text_secondary}</span>` : ''}
        </div>
    `).join('');

    // Click to seek
    container.addEventListener('click', (e) => {
        const lineEl = e.target.closest('.subtitle-line');
        if (lineEl) {
            const startMs = parseInt(lineEl.dataset.startMs);
            const audio = document.getElementById('audio-player');
            audio.currentTime = startMs / 1000;
            if (audio.paused) audio.play();
        }
    });
}

function renderLyrics(lyrics) {
    if (lyrics.length === 0) return;
    const primary = lyrics.find(l => l.is_primary) || lyrics[0];
    document.getElementById('lyrics-content').textContent = primary.content;
    document.getElementById('lyrics-section').classList.remove('hidden');
}

function renderAlignmentBadge(subtitleFile) {
    const info = document.getElementById('alignment-info');
    if (!info || !subtitleFile.alignment_source) return;

    const confidence = subtitleFile.alignment_confidence || 0;
    const matched = subtitleFile.alignment_matched || 0;
    const total = subtitleFile.alignment_total || 0;
    const pct = Math.round(confidence * 100);

    let badgeClass = 'badge-low';
    if (pct >= 80) badgeClass = 'badge-good';
    else if (pct >= 60) badgeClass = 'badge-ok';

    const algo = subtitleFile.alignment_algorithm;
    const algoLabel = algo === 'anchor' ? '錨點對齊' : '逐行匹配';
    info.innerHTML = `<span class="alignment-badge ${badgeClass}">${algoLabel} ${pct}% (${matched}/${total} 行匹配)</span>`;
    info.classList.remove('hidden');
}

// ── Subtitle Sync ───────────────────────────────────────────

function highlightLine(index) {
    const lines = document.querySelectorAll('.subtitle-line');
    lines.forEach((el, i) => {
        el.classList.toggle('active', i === index);
    });
}

function scrollToLine(index) {
    if (index < 0) return;
    const el = document.querySelectorAll('.subtitle-line')[index];
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function setupSubtitleSync(audio) {
    audio.addEventListener('timeupdate', () => {
        if (isSeeking) return;
        const currentMs = audio.currentTime * 1000;
        const newIndex = findCurrentLine(currentMs);
        if (newIndex !== currentLineIndex) {
            highlightLine(newIndex);
            scrollToLine(newIndex);
            currentLineIndex = newIndex;
        }
    });
}

// ── Player Controls ─────────────────────────────────────────

function setupPlayerControls(audio) {
    const playBtn = document.getElementById('play-btn');
    const seekBar = document.getElementById('seek-bar');
    const currentTimeEl = document.getElementById('current-time');
    const durationEl = document.getElementById('duration');

    // Play/pause
    playBtn.addEventListener('click', () => {
        if (audio.paused) {
            audio.play();
        } else {
            audio.pause();
        }
    });

    audio.addEventListener('play', () => {
        playBtn.innerHTML = '&#10074;&#10074;'; // pause icon
    });

    audio.addEventListener('pause', () => {
        playBtn.innerHTML = '&#9654;'; // play icon
    });

    // Duration
    audio.addEventListener('loadedmetadata', () => {
        durationEl.textContent = formatTimeFromSeconds(audio.duration);
        seekBar.max = audio.duration;
    });

    // Time update → seek bar + time display
    audio.addEventListener('timeupdate', () => {
        if (!isSeeking) {
            seekBar.value = audio.currentTime;
            currentTimeEl.textContent = formatTimeFromSeconds(audio.currentTime);
        }
    });

    // Seek bar interaction
    seekBar.addEventListener('mousedown', () => { isSeeking = true; });
    seekBar.addEventListener('touchstart', () => { isSeeking = true; });

    seekBar.addEventListener('input', () => {
        currentTimeEl.textContent = formatTimeFromSeconds(seekBar.value);
    });

    seekBar.addEventListener('change', () => {
        audio.currentTime = parseFloat(seekBar.value);
        isSeeking = false;
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') {
            e.preventDefault();
            if (audio.paused) audio.play();
            else audio.pause();
        }
        if (e.code === 'ArrowLeft') {
            e.preventDefault();
            audio.currentTime = Math.max(0, audio.currentTime - 5);
        }
        if (e.code === 'ArrowRight') {
            e.preventDefault();
            audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
        }
    });
}

// ── Track Switching ─────────────────────────────────────────

function setupTrackSwitch(audio) {
    document.querySelectorAll('input[name="track"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const currentTime = audio.currentTime;
            const wasPlaying = !audio.paused;
            audio.src = `/api/v1/audio/stream/${SONG_ID}?track=${radio.value}`;

            audio.addEventListener('loadedmetadata', function restore() {
                audio.currentTime = currentTime;
                if (wasPlaying) audio.play();
                audio.removeEventListener('loadedmetadata', restore);
            });

            audio.load();
        });
    });
}

// ── Init ────────────────────────────────────────────────────

async function init() {
    // 1. Load song metadata
    const songResp = await fetch(`/api/v1/songs/${SONG_ID}`);
    if (!songResp.ok) {
        document.getElementById('song-title').textContent = '歌曲不存在';
        return;
    }
    song = await songResp.json();
    renderSongHeader(song);

    // 2. Show lyrics if available
    if (song.lyrics && song.lyrics.length > 0) {
        renderLyrics(song.lyrics);
    }

    // 3. Setup audio player if audio exists
    if (!song.audio_path) {
        document.getElementById('no-audio-msg').classList.remove('hidden');
        return;
    }

    const audio = document.getElementById('audio-player');
    audio.src = `/api/v1/audio/stream/${SONG_ID}?track=original`;
    document.getElementById('player-section').classList.remove('hidden');

    // Show vocals option if available
    if (song.vocals_path) {
        document.getElementById('vocals-option').classList.remove('hidden');
    }

    setupPlayerControls(audio);
    setupTrackSwitch(audio);

    // 4. Load subtitles
    const subResp = await fetch(`/api/v1/subtitles/by-song/${SONG_ID}`);
    if (subResp.ok) {
        const subtitleFiles = await subResp.json();
        if (subtitleFiles.length > 0 && subtitleFiles[0].lines.length > 0) {
            const subFile = subtitleFiles[0];
            subtitleLines = subFile.lines.sort((a, b) => a.start_ms - b.start_ms);
            renderSubtitleLines(subtitleLines);
            renderAlignmentBadge(subFile);
            document.getElementById('subtitle-section').classList.remove('hidden');
            // Hide lyrics section when we have timed subtitles
            document.getElementById('lyrics-section').classList.add('hidden');
            setupSubtitleSync(audio);
        }
    }
}

init();
