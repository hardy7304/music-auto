const songs = [
    {
        title: "歸隱雲深處",
        artist: "AURORA AI v9 Engine",
        cover: "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=2070&auto=format&fit=crop",
        src: "https://pub-64e3ab309dec4a519038599498fbb431.r2.dev/20260510%20%E5%BC%B5%E5%98%89%E8%B1%AA%20%E6%AD%B8%E9%9A%B1%E9%9B%B2%E6%B7%B1%E8%99%95.mp3"
    },
    {
        title: "極光之境 (Ambient)",
        artist: "AURORA AI v9 Engine",
        cover: "https://images.unsplash.com/photo-1464802686167-b939a6910659?q=80&w=2070&auto=format&fit=crop",
        src: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
    },
    {
        title: "城市霓虹",
        artist: "AURORA AI v9 Engine",
        cover: "https://images.unsplash.com/photo-1514525253344-f85653b7419a?q=80&w=1974&auto=format&fit=crop",
        src: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"
    }
];

let currentSongIndex = 0;
let isPlaying = false;

const audio = document.getElementById('audio-element');
const playBtn = document.getElementById('play-btn');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const progressFill = document.getElementById('progress-fill');
const progressBar = document.getElementById('progress-bar');
const currentTimeEl = document.getElementById('current-time');
const durationEl = document.getElementById('total-duration');
const currentTitle = document.getElementById('current-title');
const currentArtist = document.getElementById('current-artist');
const currentCover = document.getElementById('current-cover');
const playlistContainer = document.getElementById('playlist');

function initPlayer() {
    loadSong(currentSongIndex);
    renderPlaylist();
}

function loadSong(index) {
    const song = songs[index];
    currentTitle.textContent = song.title;
    currentArtist.textContent = song.artist;
    currentCover.style.backgroundImage = `url(${song.cover})`;
    audio.src = song.src;
    
    // Update active state in playlist
    const items = document.querySelectorAll('.playlist-item');
    items.forEach((item, i) => {
        if (i === index) item.classList.add('active');
        else item.classList.remove('active');
    });
}

function togglePlay() {
    if (isPlaying) {
        audio.pause();
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
    } else {
        audio.play();
        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
    }
    isPlaying = !isPlaying;
}

function updateProgress(e) {
    const { duration, currentTime } = e.srcElement;
    const progressPercent = (currentTime / duration) * 100;
    progressFill.style.width = `${progressPercent}%`;
    
    // Update time displays
    currentTimeEl.textContent = formatTime(currentTime);
    if (duration) durationEl.textContent = formatTime(duration);
}

function setProgress(e) {
    const width = this.clientWidth;
    const clickX = e.offsetX;
    const duration = audio.duration;
    audio.currentTime = (clickX / width) * duration;
}

function formatTime(time) {
    const min = Math.floor(time / 60);
    const sec = Math.floor(time % 60);
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

function renderPlaylist() {
    playlistContainer.innerHTML = '';
    songs.forEach((song, index) => {
        const item = document.createElement('div');
        item.className = `playlist-item ${index === currentSongIndex ? 'active' : ''}`;
        item.innerHTML = `
            <img src="${song.cover}" alt="cover">
            <div class="item-info">
                <h4>${song.title}</h4>
                <p>${song.artist}</p>
            </div>
            <span class="item-duration">---</span>
        `;
        item.addEventListener('click', () => {
            currentSongIndex = index;
            loadSong(index);
            if (isPlaying) audio.play();
            else togglePlay();
        });
        playlistContainer.appendChild(item);
    });
}

playBtn.addEventListener('click', togglePlay);
prevBtn.addEventListener('click', () => {
    currentSongIndex = (currentSongIndex - 1 + songs.length) % songs.length;
    loadSong(currentSongIndex);
    if (isPlaying) audio.play();
});
nextBtn.addEventListener('click', () => {
    currentSongIndex = (currentSongIndex + 1) % songs.length;
    loadSong(currentSongIndex);
    if (isPlaying) audio.play();
});

audio.addEventListener('timeupdate', updateProgress);
audio.addEventListener('ended', () => {
    currentSongIndex = (currentSongIndex + 1) % songs.length;
    loadSong(currentSongIndex);
    audio.play();
});
progressBar.addEventListener('click', setProgress);

initPlayer();
