import React, { lazy } from 'react';
import { motion } from 'framer-motion';
import { Play } from 'lucide-react';
import type { Playlist } from '../data/music';
export function PlaylistCard({ playlist }: {playlist: Playlist;}) {
  return (
    <motion.div
      whileHover={{
        y: -4
      }}
      className="group relative w-44 shrink-0 cursor-pointer rounded-xl bg-neutral-900 p-3 transition-colors hover:bg-neutral-800">
      
      <div className="relative mb-3 overflow-hidden rounded-lg">
        <img
          src={playlist.cover}
          alt={`${playlist.title} cover`}
          className="aspect-square w-full object-cover"
          loading="lazy" />
        
        <motion.button
          aria-label={`Play ${playlist.title}`}
          whileHover={{
            scale: 1.06
          }}
          className="absolute bottom-2 right-2 flex h-11 w-11 items-center justify-center rounded-full bg-violet-500 text-white opacity-0 shadow-lg shadow-black/40 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          
          <Play className="h-5 w-5 fill-current" aria-hidden="true" />
        </motion.button>
      </div>
      <h3 className="truncate text-sm font-semibold text-white">
        {playlist.title}
      </h3>
      <p className="mt-0.5 line-clamp-2 text-xs text-neutral-400">
        {playlist.description}
      </p>
    </motion.div>);

}