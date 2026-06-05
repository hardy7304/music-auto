import React, {
  useEffect,
  useState,
  useRef,
  createContext,
  useContext } from
'react';
import type { Track } from '../data/music';
import { allTracks } from '../data/music';
interface PlayerState {
  currentTrack: Track | null;
  isPlaying: boolean;
  progress: number; // seconds (live from audio element)
  duration: number; // seconds (real duration once metadata loads)
  volume: number; // 0-100
  shuffle: boolean;
  repeat: boolean;
  showLyrics: boolean;
  playTrack: (track: Track, queue?: Track[]) => void;
  togglePlay: () => void;
  nextTrack: () => void;
  prevTrack: () => void;
  setProgress: (s: number) => void;
  setVolume: (v: number) => void;
  toggleShuffle: () => void;
  toggleRepeat: () => void;
  toggleLyrics: () => void;
  downloadedTracks: Track[];
  setShuffle: (s: boolean) => void;
  setRepeat: (r: boolean) => void;
  setQueue: (q: Track[]) => void;
  updateTrackGenre: (trackId: string, genre: string) => Promise<boolean>;
}
const PlayerContext = createContext<PlayerState | null>(null);
export function PlayerProvider({ children }: {children: React.ReactNode;}) {
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [downloadedTracks, setDownloadedTracks] = useState<Track[]>([]);
  const [queue, setQueue] = useState<Track[]>(allTracks);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgressState] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(70);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);
  const [showLyrics, setShowLyrics] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Fetch downloaded tracks from FastAPI backend
  useEffect(() => {
    async function fetchSongs() {
      try {
        const res = await fetch('/api/songs?limit=1000');
        if (res.ok) {
          const data = await res.json();
          const mapped: Track[] = data.map((s: any) => ({
            id: s.song_id,
            title: s.title,
            artist: s.author || "Mureka Creator",
            album: "Mureka Library",
            cover: s.cover_url || "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=600&q=80",
            duration: 180,
            audioUrl: s.audio_url,
            fallbackUrl: s.fallback_url,
            genre: s.genre,
            lyrics: s.lyrics ? JSON.parse(s.lyrics) : undefined,
          }));
          setDownloadedTracks(mapped);
          if (mapped.length > 0) {
            setQueue(mapped);
          }
        }
      } catch (err) {
        console.error("Error fetching downloaded songs:", err);
      }
    }
    fetchSongs();
  }, []);

  // Load a new track source when currentTrack changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentTrack) return;
    audio.src = currentTrack.audioUrl ?? '';
    audio.load();
    setProgressState(0);
    setDuration(currentTrack.duration || 0);
    if (isPlaying) {
      audio.play().catch(() => setIsPlaying(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrack?.id]);
  // Play / pause the real audio element
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentTrack) return;
    if (isPlaying) {
      audio.play().catch(() => setIsPlaying(false));
    } else {
      audio.pause();
    }
  }, [isPlaying, currentTrack]);
  // Keep the element volume in sync (0-100 -> 0-1)
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume / 100;
  }, [volume]);
  const playTrack = (track: Track, nextQueue?: Track[]) => {
    if (nextQueue && nextQueue.length) setQueue(nextQueue);
    if (currentTrack?.id === track.id) {
      setIsPlaying((p) => !p);
      return;
    }
    setCurrentTrack(track);
    setProgressState(0);
    setIsPlaying(true);
  };
  const togglePlay = () => {
    if (!currentTrack) return;
    setIsPlaying((p) => !p);
  };
  // Pick the next track in the active queue (random when shuffle is on, wraps around).
  const pickNext = (): Track | null => {
    if (!queue.length) return null;
    if (!currentTrack) return queue[0];
    const idx = queue.findIndex((t) => t.id === currentTrack.id);
    if (shuffle) {
      if (queue.length === 1) return queue[0];
      let r = idx;
      while (r === idx) r = Math.floor(Math.random() * queue.length);
      return queue[r];
    }
    return queue[(idx + 1) % queue.length];
  };
  const pickPrev = (): Track | null => {
    if (!queue.length) return null;
    if (!currentTrack) return queue[0];
    const idx = queue.findIndex((t) => t.id === currentTrack.id);
    return queue[(idx - 1 + queue.length) % queue.length];
  };
  const nextTrack = () => {
    const t = pickNext();
    if (!t) return;
    setCurrentTrack(t);
    setProgressState(0);
    setIsPlaying(true);
  };
  const prevTrack = () => {
    // Restart current track if more than 3s in, otherwise go to previous.
    if (audioRef.current && audioRef.current.currentTime > 3) {
      audioRef.current.currentTime = 0;
      setProgressState(0);
      return;
    }
    const t = pickPrev();
    if (!t) return;
    setCurrentTrack(t);
    setProgressState(0);
    setIsPlaying(true);
  };
  // Seek the real audio element
  const setProgress = (s: number) => {
    if (audioRef.current) audioRef.current.currentTime = s;
    setProgressState(s);
  };
  const setVolume = (v: number) => setVolumeState(v);
  const handleTimeUpdate = () => {
    if (audioRef.current) setProgressState(audioRef.current.currentTime);
  };
  const handleLoadedMetadata = () => {
    if (audioRef.current && !isNaN(audioRef.current.duration)) {
      setDuration(audioRef.current.duration);
    }
  };
  // Radio behaviour: when a track ends, repeat it or auto-advance to the next.
  const handleEnded = () => {
    const audio = audioRef.current;
    if (repeat && audio) {
      audio.currentTime = 0;
      audio.play().catch(() => setIsPlaying(false));
      return;
    }
    nextTrack();
  };
  const handleError = () => {
    const audio = audioRef.current;
    if (audio && currentTrack?.fallbackUrl && audio.src !== new URL(currentTrack.fallbackUrl, window.location.href).href) {
      console.warn("Primary audio URL failed, falling back to NAS...");
      audio.src = currentTrack.fallbackUrl;
      audio.load();
      if (isPlaying) audio.play().catch(() => setIsPlaying(false));
    }
  };

  const updateTrackGenre = async (trackId: string, genre: string) => {
    try {
      const res = await fetch(`/api/songs/${trackId}/genre`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ genre }),
      });
      if (res.ok) {
        setDownloadedTracks(prev => prev.map(t => t.id === trackId ? { ...t, genre } : t));
        if (currentTrack?.id === trackId) {
          setCurrentTrack({ ...currentTrack, genre });
        }
        return true;
      }
      return false;
    } catch (e) {
      console.error("Failed to update genre", e);
      return false;
    }
  };

  return (
    <PlayerContext.Provider
      value={{
        currentTrack,
        isPlaying,
        progress,
        duration,
        volume,
        shuffle,
        repeat,
        showLyrics,
        playTrack,
        togglePlay,
        nextTrack,
        prevTrack,
        setProgress,
        setVolume,
        toggleShuffle: () => setShuffle((s) => !s),
        toggleRepeat: () => setRepeat((r) => !r),
        toggleLyrics: () => setShowLyrics((v) => !v),
        downloadedTracks,
        setShuffle,
        setRepeat,
        setQueue,
        updateTrackGenre
      }}>
      
      {/* Hidden real audio element driving playback */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        onError={handleError}
        preload="metadata" />
      
      {children}
    </PlayerContext.Provider>);

}
export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error('usePlayer must be used within PlayerProvider');
  return ctx;
}