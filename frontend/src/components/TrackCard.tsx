import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause } from 'lucide-react';
import type { Track } from '../data/music';
import { usePlayer } from '../context/PlayerContext';
export function TrackCard({ track }: {track: Track;}) {
  const { currentTrack, isPlaying, playTrack, updateTrackGenre } = usePlayer();
  const isCurrent = currentTrack?.id === track.id;
  const showPause = isCurrent && isPlaying;

  const [editingGenre, setEditingGenre] = useState(false);
  const [genreInput, setGenreInput] = useState(track.genre || 'Uncategorized');

  const handleGenreSubmit = () => {
    if (genreInput !== track.genre && updateTrackGenre) {
      updateTrackGenre(track.id, genreInput);
    }
    setEditingGenre(false);
  };
  return (
    <motion.div
      whileHover={{
        y: -4
      }}
      className="group relative w-44 shrink-0 cursor-pointer rounded-xl bg-neutral-900 p-3 transition-colors hover:bg-neutral-800"
      onClick={() => playTrack(track)}>
      
      <div className="relative mb-3 overflow-hidden rounded-lg">
        <img
          src={track.cover}
          alt={`${track.album} cover`}
          className="aspect-square w-full object-cover"
          loading="lazy" />
        
        <motion.button
          initial={false}
          animate={{
            opacity: showPause ? 1 : 0,
            y: showPause ? 0 : 8
          }}
          whileHover={{
            scale: 1.06
          }}
          aria-label={
          showPause ? `Pause ${track.title}` : `Play ${track.title}`
          }
          onClick={(e) => {
            e.stopPropagation();
            playTrack(track);
          }}
          className="absolute bottom-2 right-2 flex h-11 w-11 items-center justify-center rounded-full bg-violet-500 text-white shadow-lg shadow-black/40 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
          style={{
            opacity: showPause ? 1 : undefined
          }}>
          
          {showPause ?
          <Pause className="h-5 w-5 fill-current" aria-hidden="true" /> :

          <Play className="h-5 w-5 fill-current" aria-hidden="true" />
          }
        </motion.button>
      </div>
      <h3
        className={`truncate text-sm font-semibold ${isCurrent ? 'text-violet-400' : 'text-white'}`}>
        
        {track.title}
      </h3>
      <p className="mt-0.5 truncate text-xs text-neutral-400">{track.artist}</p>
      
      <div className="mt-1 h-5">
        {editingGenre ? (
          <input
            autoFocus
            list="standard-genres"
            value={genreInput}
            onChange={(e) => setGenreInput(e.target.value)}
            onBlur={handleGenreSubmit}
            onKeyDown={(e) => { if (e.key === 'Enter') handleGenreSubmit(); }}
            onClick={(e) => e.stopPropagation()}
            className="w-full rounded bg-neutral-800 px-1 text-xs text-white outline-none focus:ring-1 focus:ring-violet-500"
          />
        ) : (
          <span
            onClick={(e) => {
              e.stopPropagation();
              setGenreInput(track.genre || 'Uncategorized');
              setEditingGenre(true);
            }}
            className="inline-block w-full truncate rounded border border-neutral-700 bg-neutral-800/50 px-1 text-xs text-neutral-400 transition-colors hover:border-neutral-500 hover:text-white"
            title="點擊修改曲風"
          >
            {track.genre || 'Uncategorized'}
          </span>
        )}
      </div>
    </motion.div>);

}