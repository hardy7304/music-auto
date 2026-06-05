const config = {
    audioPath: '',
    lyricPath: '',
    defaultTitle: '未選擇歌曲',
    defaultCover: 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=2070&auto=format&fit=crop'
};

let playlistData = [];
let lyricData = [];
let currentTrackIndex = 0;
let isPlaying = false;

const audio = document.getElementById('audio-element');
const playBtn = document.getElementById('play-btn');
const seekSlider = document.getElementById('seek-slider');
const currentTimeEl = document.getElementById('current-time');
const totalDurationEl = document.getElementById('total-duration');

// 簡化字轉繁體 (如果需要)
function s2t(text) {
    if (!text) return "";
    return text; // 此處可擴充簡轉繁邏輯
}

function formatTime(seconds) {
    if (isNaN(seconds)) return "00:00";
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
}

async function loadLyrics() {
    const container = document.getElementById('lyrics-container');
    container.innerHTML = '<div class="lyric-line loading">正在尋找歌詞...</div>';
    
    // 這裡未來可以擴充讀取 .lrc 或 .srt 的邏輯
    setTimeout(() => {
        container.innerHTML = '<div class="lyric-line empty">暫無歌詞數據</div>';
    }, 500);
}

function renderLyrics() {
    // 渲染邏輯
}

function renderPlaylist() {
    const container = document.getElementById('playlist-container');
    const countTag = document.getElementById('song-count');
    container.innerHTML = '';
    countTag.textContent = `${playlistData.length} SONGS`;

    playlistData.forEach((track, index) => {
        const item = document.createElement('div');
        item.className = `playlist-item ${index === currentTrackIndex ? 'active' : ''}`;
        item.innerHTML = `
            <div class="item-index">${(index + 1).toString().padStart(2, '0')}</div>
            <div class="item-info">
                <div class="item-title">${s2t(track.title)}</div>
                <div class="item-meta">
                    <span class="genre-tag">${track.genre}</span>
                </div>
            </div>
        `;
        item.onclick = () => loadTrack(index, true);
        container.appendChild(item);
    });
}

function loadTrack(index, shouldPlay = false) {
    currentTrackIndex = index;
    const track = playlistData[index];
    
    // 更新 UI
    document.getElementById('current-title').textContent = s2t(track.title);
    document.getElementById('current-cover').style.backgroundImage = `url('${track.cover || config.defaultCover}')`;
    
    audio.src = track.audioPath;
    
    // 更新清單選取狀態
    const items = document.querySelectorAll('.playlist-item');
    items.forEach((item, i) => {
        item.classList.toggle('active', i === index);
    });

    // 重設進度條
    seekSlider.value = 0;
    currentTimeEl.textContent = "00:00";

    if (shouldPlay) {
        isPlaying = true;
        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
        audio.play().catch(e => console.error("Playback failed:", e));
    } else {
        isPlaying = false;
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
        audio.pause();
    }

    loadLyrics();

    // 顯示下載按鈕並綁定目前歌曲的 audioPath
    updateDownloadButton(track);
}

function updateDownloadButton(track) {
    const row = document.getElementById('download-row');
    const hint = document.getElementById('download-hint');

    if (track && track.audioPath) {
        row.style.display = 'flex';
        if (hint) hint.textContent = track.title || '';
    } else {
        row.style.display = 'none';
    }
}

function downloadCurrentSong() {
    const track = playlistData[currentTrackIndex];
    if (!track || !track.audioPath) return;

    const a = document.createElement('a');
    a.href = track.audioPath;
    // 從 audioPath 提取原始檔名，或使用歌曲標題
    const urlParts = track.audioPath.split('/');
    const rawName = urlParts[urlParts.length - 1] || track.title + '.mp3';
    a.download = decodeURIComponent(rawName);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function togglePlay() {
    if (audio.paused) {
        audio.play().then(() => {
            isPlaying = true;
            playBtn.innerHTML = '<i class="fas fa-pause"></i>';
        }).catch(e => console.error(e));
    } else {
        audio.pause();
        isPlaying = false;
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
    }
}

function nextTrack() {
    let nextIndex = (currentTrackIndex + 1) % playlistData.length;
    loadTrack(nextIndex, true);
}

function prevTrack() {
    let prevIndex = (currentTrackIndex - 1 + playlistData.length) % playlistData.length;
    loadTrack(prevIndex, true);
}

function init() {
    // 進度條控制
    audio.addEventListener('timeupdate', () => {
        if (!isNaN(audio.duration)) {
            const progress = (audio.currentTime / audio.duration) * 100;
            seekSlider.value = progress;
            currentTimeEl.textContent = formatTime(audio.currentTime);
            
            // 更新進度條背景色 (CSS 變數)
            seekSlider.style.setProperty('--progress', `${progress}%`);
        }
    });

    audio.addEventListener('loadedmetadata', () => {
        totalDurationEl.textContent = formatTime(audio.duration);
    });

    audio.addEventListener('ended', nextTrack);

    // 拖曳進度條
    seekSlider.addEventListener('input', () => {
        const time = (seekSlider.value / 100) * audio.duration;
        audio.currentTime = time;
    });

    playBtn.addEventListener('click', togglePlay);
    document.getElementById('next-btn').addEventListener('click', nextTrack);
    document.getElementById('prev-btn').addEventListener('click', prevTrack);
    document.getElementById('download-btn').addEventListener('click', downloadCurrentSong);

    // 載入資料
    fetch('playlist.json')
        .then(res => res.json())
        .then(data => {
            playlistData = data;
            renderPlaylist();
            loadTrack(0, false);
        })
        .catch(err => console.error('Error loading playlist:', err));
}

document.addEventListener('DOMContentLoaded', init);
