const config = {
    lyricsPath: 'lyrics/aurora-song.lrc',
    defaultCover: 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=2070&auto=format&fit=crop',
    defaultTitle: '歸隱雲深處',
};

const S_MAP = "爱罢备贝笔毕边变宾标别步仓产长尝场车彻陈尘衬唇聪丛体恶发坟奋复该盖干赶个巩溝構購谷鼓顧刮關觀館慣廣軌櫃國過還孩核轟紅後壺護滬劃懷壞歡環還緩換喚瘓黃謊揮輝匯會夥獲跡繼極際繼家價艱殲繭撿間簡見講醬膠階截潔借緊謹錦盡進驚競靜九舊舉句懼劇據巨絕覺決開凱顆殼課肯庫褲誇塊礦闊蠟臘萊蘭攔欄爛勞撈勞樂離裡禮麗歷隸倆聯蓮鏈臉糧療亮諒輛了龍漏爐陸驢呂鋁侶屢慮濾綠巒攣孿欒亂掄輪倫淪綸論蘿羅邏鑼籮邏馬買賣邁滿貓錨貌麼門們猛夢迷彌覓綿廟廟滅蔑鳴銘謬謀畝納難鳥捏濘寧農濃瘧諾歐盤賠噴鵬騙飄頻貧憑評潑頗撲鋪樸譜齊騎豈啟氣棄遷牽簽前強牆喬僑橋翹竅竊親輕頃請慶窮丘秋曲趨渠驅娶涧";
const T_MAP = "愛罷備貝筆畢邊變賓標別步倉產長嘗場車徹陳塵襯唇聰叢體惡發墳奮複該蓋幹趕個鞏溝構購谷鼓顧刮關觀館慣廣軌櫃國過還孩核轟紅後壺護滬劃懷壞歡環還緩換喚瘓黃謊揮輝匯會夥獲跡繼極際繼家價艱殲繭撿間簡見講醬膠階截潔借緊謹錦盡進驚競靜九舊舉句懼劇據巨絕覺決開凱顆殼課肯庫褲誇塊礦闊蠟臘萊蘭攔欄爛勞撈勞樂離裡禮麗歷隸倆聯蓮鏈臉糧療亮諒輛了龍漏爐陸驢呂鋁侶屢慮濾綠巒攣孿欒亂掄輪倫淪綸論蘿羅邏鑼籮邏馬買賣邁滿貓錨貌麼門們猛夢迷彌覓綿廟廟滅蔑鳴銘謬謀畝納難鳥捏濘寧農濃瘧諾歐盤賠噴鵬騙飄頻貧憑評潑頗撲鋪樸譜齊騎豈啟氣棄遷牽簽前強牆喬僑橋翹竅竊親輕頃請慶窮丘秋曲趨渠驅娶澗";

function s2t(text) {
    if (!text) return '';
    let result = '';
    for (let char of text) {
        const index = S_MAP.indexOf(char);
        result += index > -1 ? T_MAP[index] : char;
    }
    return result;
}

let lyricData = [];
let isPlaying = false;
let isDragging = false;

const audio = document.getElementById('audio-element');
const playBtn = document.getElementById('play-btn');
const progressFill = document.getElementById('progress-fill');
const progressBar = document.getElementById('progress-bar');
const lyricsContainer = document.getElementById('lyrics-container');
const currentTimeEl = document.getElementById('current-time');
const durationEl = document.getElementById('total-duration');
const statusBar = document.getElementById('status-bar');

function togglePlay() {
    if (isPlaying) { audio.pause(); playBtn.innerHTML = '<i class="fas fa-play"></i>'; }
    else { audio.play().then(() => { playBtn.innerHTML = '<i class="fas fa-pause"></i>'; }).catch(() => { document.getElementById('play-overlay').style.display = 'flex'; }); }
    isPlaying = !isPlaying;
}
window.appTogglePlay = togglePlay;

function parseLyrics(text) {
    const result = [];
    const lines = text.split('\n');
    if (text.includes('-->')) {
        lines.forEach(line => {
            const timeMatch = line.match(/(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/);
            if (timeMatch && line.includes('-->')) {
                const time = parseInt(timeMatch[1]) * 3600 + parseInt(timeMatch[2]) * 60 + parseInt(timeMatch[3]) + parseInt(timeMatch[4])/1000;
                const parts = line.split('-->');
                if (parts.length > 1) {
                    const textAfterTime = parts[1].substring(13).trim();
                    if (textAfterTime) result.push({ time, text: textAfterTime });
                }
            } else if (line.trim() && !line.match(/^\d+$/) && !line.includes('-->')) {
                if (result.length > 0) result[result.length - 1].text += " " + line.trim();
            }
        });
    } else {
        const timeReg = /\[(\d+):(\d+(?:\.\d+)?)\](.*)/;
        lines.forEach(line => {
            const match = timeReg.exec(line);
            if (match) result.push({ time: parseInt(match[1]) * 60 + parseFloat(match[2]), text: match[3].trim() });
        });
    }
    return result.sort((a, b) => a.time - b.time);
}

async function loadLyrics() {
    const extensions = ['.srt', '.lrc'];
    const basePath = config.lyricsPath.replace(/\.[^/.]+$/, "");
    for (let ext of extensions) {
        try {
            const response = await fetch(basePath + ext + "?v=" + Math.random());
            if (response.ok) {
                const text = await response.text();
                lyricData = parseLyrics(text);
                renderLyrics();
                statusBar.textContent = `${ext.toUpperCase()} LOADED`;
                return;
            }
        } catch (e) {}
    }
}

function renderLyrics() {
    lyricsContainer.innerHTML = '';
    lyricData.forEach((line, index) => {
        const div = document.createElement('div');
        div.className = 'lyric-line';
        div.id = `lyric-line-${index}`;
        div.textContent = s2t(line.text);
        div.onclick = () => { audio.currentTime = line.time; if (!isPlaying) togglePlay(); };
        lyricsContainer.appendChild(div);
    });
}

function init() {
    document.getElementById('current-cover').style.backgroundImage = `url('${config.defaultCover}')`;
    document.getElementById('current-title').textContent = config.defaultTitle;
    
    const updateSeeking = (e) => {
        const rect = progressBar.getBoundingClientRect();
        const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
        if (audio.duration) audio.currentTime = percent * audio.duration;
    };
    progressBar.addEventListener('mousedown', (e) => { isDragging = true; updateSeeking(e); });
    window.addEventListener('mousemove', (e) => { if (isDragging) updateSeeking(e); });
    window.addEventListener('mouseup', () => { isDragging = false; });
    playBtn.addEventListener('click', togglePlay);
    
    audio.addEventListener('timeupdate', () => {
        if (isDragging) return;
        if (audio.duration) {
            progressFill.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
            durationEl.textContent = formatTime(audio.duration);
        }
        currentTimeEl.textContent = formatTime(audio.currentTime);
        
        // 核心：修正自動捲動邏輯
        let activeIndex = -1;
        for (let i = 0; i < lyricData.length; i++) {
            if (audio.currentTime >= lyricData[i].time) activeIndex = i;
            else break;
        }
        
        if (activeIndex !== -1) {
            const lines = lyricsContainer.children;
            const activeLine = lines[activeIndex];
            
            if (activeLine && !activeLine.classList.contains('active')) {
                // 清除舊的 active
                const currentActive = lyricsContainer.querySelector('.lyric-line.active');
                if (currentActive) currentActive.classList.remove('active');
                
                // 設定新的 active
                activeLine.classList.add('active');
                
                // 執行捲動：對準歌詞容器中心
                const containerHeight = lyricsContainer.offsetHeight;
                const lineOffset = activeLine.offsetTop;
                const lineHeight = activeLine.offsetHeight;
                
                lyricsContainer.scrollTo({
                    top: lineOffset - (containerHeight / 2) + (lineHeight / 2),
                    behavior: 'smooth'
                });
            }
        }
    });

    function formatTime(s) {
        if (isNaN(s)) return '00:00';
        const m = Math.floor(s / 60);
        const sec = Math.floor(s % 60);
        return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    }

    loadLyrics();
}

init();
