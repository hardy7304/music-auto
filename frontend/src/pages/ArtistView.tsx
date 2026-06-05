import React from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, Play, Pause } from 'lucide-react';
import { getArtistById, getArtistTracks, formatTime } from '../data/music';
import { usePlayer } from '../context/PlayerContext';
interface ArtistViewProps {
  artistId: string;
  onBack: () => void;
}
export function ArtistView({ artistId, onBack }: ArtistViewProps) {
  const artist = getArtistById(artistId);
  const { currentTrack, isPlaying, playTrack } = usePlayer();
  if (!artist) {
    return (
      <div className="text-neutral-400">
        <button
          onClick={onBack}
          className="mb-4 text-sm text-violet-400 hover:underline">
          
          ← Back
        </button>
        <p>Artist not found.</p>
      </div>);

  }
  const tracks = getArtistTracks(artist.name);
  const firstTrack = tracks[0];
  const isArtistPlaying =
  isPlaying && firstTrack && currentTrack?.id === firstTrack.id;
  return (
    <div>
      <button
        onClick={onBack}
        aria-label="Go back"
        className="mb-6 inline-flex items-center gap-1 rounded-full bg-black/40 px-3 py-1.5 text-sm text-neutral-300 transition-colors hover:text-white">
        
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Back
      </button>

      {/* Artist header */}
      <header className="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-end sm:text-left">
        <img
          src={artist.image}
          alt={artist.name}
          className="h-40 w-40 shrink-0 rounded-full object-cover shadow-2xl shadow-black/50 sm:h-52 sm:w-52" />
        
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-violet-300">
            Artist · {artist.genre}
          </p>
          <h1 className="mt-2 text-4xl font-bold text-white sm:text-6xl">
            {artist.name}
          </h1>
          <p className="mt-3 text-sm text-neutral-400">
            {artist.followers} monthly listeners
          </p>
        </div>
      </header>

      {/* Actions */}
      {firstTrack &&
      <div className="mt-6 flex items-center gap-4">
          <motion.button
          whileTap={{
            scale: 0.96
          }}
          onClick={() => playTrack(firstTrack, tracks)}
          aria-label={isArtistPlaying ? 'Pause' : `Play ${artist.name}`}
          className="flex h-14 w-14 items-center justify-center rounded-full bg-violet-500 text-white transition-colors hover:bg-violet-400">
          
            {isArtistPlaying ?
          <Pause className="h-6 w-6 fill-current" aria-hidden="true" /> :

          <Play className="h-6 w-6 fill-current" aria-hidden="true" />
          }
          </motion.button>
        </div>
      }

      {/* Bio */}
      {artist.bio &&
      <section className="mt-8 max-w-2xl">
          <h2 className="mb-2 text-lg font-bold text-white">About</h2>
          <p className="text-sm leading-relaxed text-neutral-400">
            {artist.bio}
          </p>
        </section>
      }

      {/* Tracks */}
      <section className="mt-10">
        <h2 className="mb-3 text-lg font-bold text-white">
          {tracks.length ? 'Popular' : 'No tracks available'}
        </h2>
        <ul className="space-y-1">
          {tracks.map((track, i) => {
            const isCurrent = currentTrack?.id === track.id;
            const showPause = isCurrent && isPlaying;
            return (
              <li key={track.id}>
                <button
                  onClick={() => playTrack(track, tracks)}
                  className="group flex w-full items-center gap-4 rounded-lg px-3 py-2 text-left transition-colors hover:bg-neutral-800">
                  
                  <span className="relative flex w-5 shrink-0 justify-center text-sm text-neutral-500">
                    <span className="group-hover:opacity-0">{i + 1}</span>
                    <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100">
                      {showPause ?
                      <Pause
                        className="h-4 w-4 text-white"
                        aria-hidden="true" /> :


                      <Play
                        className="h-4 w-4 text-white"
                        aria-hidden="true" />

                      }
                    </span>
                  </span>
                  <img
                    src={track.cover}
                    alt=""
                    aria-hidden="true"
                    className="h-10 w-10 shrink-0 rounded object-cover" />
                  
                  <span className="min-w-0 flex-1">
                    <span
                      className={`block truncate text-sm font-medium ${isCurrent ? 'text-violet-400' : 'text-white'}`}>
                      
                      {track.title}
                    </span>
                    <span className="block truncate text-xs text-neutral-400">
                      {track.album}
                    </span>
                  </span>
                  <span className="shrink-0 text-xs tabular-nums text-neutral-500">
                    {formatTime(track.duration)}
                  </span>
                </button>
              </li>);

          })}
        </ul>
      </section>
    </div>);

}