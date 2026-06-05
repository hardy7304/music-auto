import React, { lazy } from 'react';
import { motion } from 'framer-motion';
import type { Artist } from '../data/music';
interface ArtistCardProps {
  artist: Artist;
  onSelect?: (artistId: string) => void;
}
export function ArtistCard({ artist, onSelect }: ArtistCardProps) {
  return (
    <motion.button
      whileHover={{
        y: -4
      }}
      onClick={() => onSelect?.(artist.id)}
      className="group flex w-44 shrink-0 cursor-pointer flex-col items-center rounded-xl bg-neutral-900 p-3 text-center transition-colors hover:bg-neutral-800">
      
      <img
        src={artist.image}
        alt={artist.name}
        className="mb-3 aspect-square w-full rounded-full object-cover"
        loading="lazy" />
      
      <h3 className="truncate text-sm font-semibold text-white">
        {artist.name}
      </h3>
      <p className="mt-0.5 text-xs text-neutral-400">{artist.genre}</p>
      <p className="mt-0.5 text-xs text-neutral-500">
        {artist.followers} followers
      </p>
    </motion.button>);

}