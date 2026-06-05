import React from 'react';
import { motion } from 'framer-motion';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Shuffle,
  Repeat,
  Volume2,
  Volume1,
  VolumeX,
  Heart,
  Mic2 } from
'lucide-react';
import { usePlayer } from '../context/PlayerContext';
import { formatTime } from '../data/music';
export function PlayerBar() {
  const {
    currentTrack,
    isPlaying,
    progress,
    duration,
    volume,
    shuffle,
    repeat,
    showLyrics,
    togglePlay,
    nextTrack,
    prevTrack,
    setProgress,
    setVolume,
    toggleShuffle,
    toggleRepeat,
    toggleLyrics
  } = usePlayer();
  const VolumeIcon = volume === 0 ? VolumeX : volume < 50 ? Volume1 : Volume2;
  return (
    <footer
      aria-label="Player"
      className="z-20 flex items-center gap-3 border-t border-neutral-800 bg-neutral-950 px-3 py-3 md:gap-4 md:px-4">
      
      {/* Now playing */}
      <div className="flex min-w-0 flex-1 items-center gap-3 md:w-72 md:flex-none">
        {currentTrack ?
        <>
            <img
            src={currentTrack.cover}
            alt=""
            aria-hidden="true"
            className="h-12 w-12 shrink-0 rounded-md object-cover md:h-14 md:w-14" />
          
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">
                {currentTrack.title}
              </p>
              <p className="truncate text-xs text-neutral-400">
                {currentTrack.artist}
              </p>
            </div>
            <button
            aria-label="Save to your library"
            className="ml-1 hidden shrink-0 text-neutral-400 transition-colors hover:text-violet-400 sm:block">
            
              <Heart className="h-4 w-4" aria-hidden="true" />
            </button>
          </> :

        <div className="flex items-center gap-3">
            <div className="h-12 w-12 shrink-0 rounded-md bg-neutral-800 md:h-14 md:w-14" />
            <p className="text-sm text-neutral-500">Select a track to play</p>
          </div>
        }
      </div>

      {/* Center controls */}
      <div className="flex flex-[1.5] flex-col items-center gap-1.5">
        <div className="flex items-center gap-4">
          <button
            aria-label="Shuffle"
            aria-pressed={shuffle}
            onClick={toggleShuffle}
            className={`hidden transition-colors sm:block ${shuffle ? 'text-violet-400' : 'text-neutral-400 hover:text-white'}`}>
            
            <Shuffle className="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            aria-label="Previous track"
            onClick={prevTrack}
            disabled={!currentTrack}
            className="text-neutral-300 transition-colors hover:text-white disabled:opacity-40">
            
            <SkipBack className="h-5 w-5 fill-current" aria-hidden="true" />
          </button>
          <motion.button
            whileTap={{
              scale: 0.92
            }}
            aria-label={isPlaying ? 'Pause' : 'Play'}
            onClick={togglePlay}
            disabled={!currentTrack}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-neutral-950 transition-transform hover:scale-105 disabled:opacity-40">
            
            {isPlaying ?
            <Pause className="h-4 w-4 fill-current" aria-hidden="true" /> :

            <Play className="h-4 w-4 fill-current" aria-hidden="true" />
            }
          </motion.button>
          <button
            aria-label="Next track"
            onClick={nextTrack}
            disabled={!currentTrack}
            className="text-neutral-300 transition-colors hover:text-white disabled:opacity-40">
            
            <SkipForward className="h-5 w-5 fill-current" aria-hidden="true" />
          </button>
          <button
            aria-label="Repeat"
            aria-pressed={repeat}
            onClick={toggleRepeat}
            className={`hidden transition-colors sm:block ${repeat ? 'text-violet-400' : 'text-neutral-400 hover:text-white'}`}>
            
            <Repeat className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="hidden w-full max-w-xl items-center gap-2 sm:flex">
          <span className="w-10 text-right text-xs tabular-nums text-neutral-400">
            {formatTime(progress)}
          </span>
          <label htmlFor="seek" className="sr-only">
            Seek
          </label>
          <input
            id="seek"
            type="range"
            min={0}
            max={duration || 100}
            value={progress}
            onChange={(e) => setProgress(Number(e.target.value))}
            disabled={!currentTrack}
            className="player-range h-1 flex-1"
            style={{
              ['--pct' as string]: `${duration ? progress / duration * 100 : 0}%`
            }}
            aria-label="Seek" />
          
          <span className="w-10 text-xs tabular-nums text-neutral-400">
            {formatTime(duration)}
          </span>
        </div>
      </div>

      {/* Lyrics + Volume */}
      <div className="hidden w-52 items-center justify-end gap-2 md:flex">
        <button
          aria-label="Lyrics"
          aria-pressed={showLyrics}
          onClick={toggleLyrics}
          disabled={!currentTrack}
          className={`shrink-0 transition-colors disabled:opacity-40 ${showLyrics ? 'text-violet-400' : 'text-neutral-400 hover:text-white'}`}>
          
          <Mic2 className="h-4 w-4" aria-hidden="true" />
        </button>
        <VolumeIcon
          className="h-4 w-4 shrink-0 text-neutral-400"
          aria-hidden="true" />
        
        <label htmlFor="volume" className="sr-only">
          Volume
        </label>
        <input
          id="volume"
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="player-range h-1 w-24"
          style={{
            ['--pct' as string]: `${volume}%`
          }}
          aria-label="Volume" />
        
      </div>
    </footer>);

}