import React from 'react';
import { motion } from 'framer-motion';
import { Play, Pause } from 'lucide-react';
import { featuredHero } from '../data/music';
import { usePlayer } from '../context/PlayerContext';
export function Hero() {
  const { track, tagline, blurb } = featuredHero;
  const { currentTrack, isPlaying, playTrack } = usePlayer();
  const isCurrent = currentTrack?.id === track.id;
  const showPause = isCurrent && isPlaying;
  return (
    <section className="relative overflow-hidden rounded-2xl bg-neutral-900">
      <div className="absolute inset-0">
        <img
          src={track.cover}
          alt=""
          aria-hidden="true"
          className="h-full w-full object-cover opacity-30" />
        
        <div className="absolute inset-0 bg-neutral-950/70" />
      </div>
      <div className="relative flex flex-col gap-6 p-6 sm:flex-row sm:items-end sm:p-10">
        <img
          src={track.cover}
          alt={`${track.album} cover`}
          className="h-40 w-40 shrink-0 rounded-xl object-cover shadow-2xl shadow-black/50 sm:h-48 sm:w-48" />
        
        <div className="min-w-0">
          <span className="inline-block rounded-full bg-violet-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-violet-300">
            {tagline}
          </span>
          <h1 className="mt-3 text-3xl font-bold text-white sm:text-5xl">
            {track.album}
          </h1>
          <p className="mt-1 text-lg font-medium text-neutral-300">
            {track.artist}
          </p>
          <p className="mt-3 max-w-xl text-sm text-neutral-400">{blurb}</p>
          <motion.button
            whileTap={{
              scale: 0.96
            }}
            onClick={() => playTrack(track)}
            className="mt-5 inline-flex items-center gap-2 rounded-full bg-violet-500 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-violet-400">
            
            {showPause ?
            <Pause className="h-4 w-4 fill-current" aria-hidden="true" /> :

            <Play className="h-4 w-4 fill-current" aria-hidden="true" />
            }
            {showPause ? 'Pause' : 'Play'}
          </motion.button>
        </div>
      </div>
    </section>);

}