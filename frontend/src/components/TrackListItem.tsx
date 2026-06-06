import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause } from 'lucide-react';
import type { Track } from '../data/music';
import { usePlayer } from '../context/PlayerContext';

export function TrackListItem({ track }: {track: Track;}) {
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
      whileHover={{ backgroundColor: "rgba(38, 38, 38, 1)" }}
      className="group flex cursor-pointer items-center gap-4 rounded-xl px-4 py-2.5 transition-colors hover:bg-neutral-800"
      onClick={() => playTrack(track)}
    >
      {/* Cover with Play/Pause Overlay */}
      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-md">
        <img
          src={track.cover || '/default-cover.png'}
          alt={`${track.title} cover`}
          className="h-full w-full object-cover"
          loading="lazy"
        />
        <div className={`absolute inset-0 flex items-center justify-center bg-black/40 transition-opacity ${isCurrent ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
           {showPause ? (
             <Pause className="h-5 w-5 fill-white text-white" aria-hidden="true" />
           ) : (
             <Play className="h-5 w-5 fill-white text-white pl-0.5" aria-hidden="true" />
           )}
        </div>
      </div>

      {/* Title and Artist */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <span className={`truncate text-sm font-semibold ${isCurrent ? 'text-violet-400' : 'text-white'}`}>
          {track.title}
        </span>
        <span className="truncate text-xs text-neutral-400">{track.artist}</span>
      </div>

      {/* Genre Tag */}
      <div className="w-32 shrink-0 sm:w-48 text-right sm:text-left pr-2 sm:pr-0">
        {editingGenre ? (
          <input
            autoFocus
            list="standard-genres"
            value={genreInput}
            onChange={(e) => setGenreInput(e.target.value)}
            onBlur={handleGenreSubmit}
            onKeyDown={(e) => { if (e.key === 'Enter') handleGenreSubmit(); }}
            onClick={(e) => e.stopPropagation()}
            className="w-full rounded bg-neutral-700 px-2 py-1 text-xs text-white outline-none focus:ring-1 focus:ring-violet-500"
          />
        ) : (
          <span
            onClick={(e) => {
              e.stopPropagation();
              setGenreInput(track.genre || 'Uncategorized');
              setEditingGenre(true);
            }}
            className="inline-block truncate rounded-full border border-neutral-700 bg-neutral-800/50 px-3 py-1 text-xs text-neutral-300 transition-colors hover:border-neutral-500 hover:text-white"
            title="點擊修改曲風"
          >
            {track.genre || 'Uncategorized'}
          </span>
        )}
      </div>

      {/* Duration */}
      <div className="hidden w-16 shrink-0 text-right text-sm text-neutral-400 sm:block">
        {track.duration || '--:--'}
      </div>
    </motion.div>
  );
}
