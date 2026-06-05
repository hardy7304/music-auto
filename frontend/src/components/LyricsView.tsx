import React, { useEffect, useMemo, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { usePlayer } from '../context/PlayerContext';
import { getLyrics } from '../data/music';
export function LyricsView() {
  const { currentTrack, showLyrics, progress, toggleLyrics, setProgress } =
  usePlayer();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const lines = useMemo(
    () => currentTrack ? getLyrics(currentTrack) : [],
    [currentTrack]
  );
  // Index of the currently-active line based on playback progress
  const activeIndex = useMemo(() => {
    let idx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (progress >= lines[i].time) idx = i;else
      break;
    }
    return idx;
  }, [lines, progress]);
  // Auto-scroll the active line into the centre
  useEffect(() => {
    if (!showLyrics || activeIndex < 0 || !containerRef.current) return;
    const el = containerRef.current.querySelector<HTMLElement>(
      `[data-line="${activeIndex}"]`
    );
    el?.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }, [activeIndex, showLyrics]);
  return (
    <AnimatePresence>
      {showLyrics && currentTrack &&
      <motion.div
        initial={{
          opacity: 0,
          y: '100%'
        }}
        animate={{
          opacity: 1,
          y: 0
        }}
        exit={{
          opacity: 0,
          y: '100%'
        }}
        transition={{
          type: 'spring',
          stiffness: 320,
          damping: 34
        }}
        className="fixed inset-0 z-30 flex flex-col bg-neutral-950"
        role="dialog"
        aria-modal="true"
        aria-label="Lyrics">
        
          {/* Blurred cover backdrop */}
          <div className="pointer-events-none absolute inset-0">
            <img
            src={currentTrack.cover}
            alt=""
            aria-hidden="true"
            className="h-full w-full scale-110 object-cover opacity-20 blur-2xl" />
          
            <div className="absolute inset-0 bg-neutral-950/80" />
          </div>

          {/* Header */}
          <header className="relative flex items-center gap-4 px-5 py-4">
            <button
            onClick={toggleLyrics}
            aria-label="Close lyrics"
            className="rounded-full p-2 text-neutral-300 transition-colors hover:bg-white/10 hover:text-white">
            
              <ChevronDown className="h-6 w-6" aria-hidden="true" />
            </button>
            <img
            src={currentTrack.cover}
            alt=""
            aria-hidden="true"
            className="h-12 w-12 rounded-md object-cover" />
          
            <div className="min-w-0">
              <p className="truncate text-base font-semibold text-white">
                {currentTrack.title}
              </p>
              <p className="truncate text-sm text-neutral-400">
                {currentTrack.artist}
              </p>
            </div>
          </header>

          {/* Lyrics */}
          <div
          ref={containerRef}
          className="relative min-h-0 flex-1 overflow-y-auto px-6 pb-32 pt-8 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          
            <ul className="mx-auto max-w-2xl space-y-5">
              {lines.map((line, i) => {
              const active = i === activeIndex;
              const past = i < activeIndex;
              return (
                <li key={i} data-line={i}>
                    <button
                    onClick={() => setProgress(line.time)}
                    className={`block w-full text-left text-2xl font-bold leading-snug transition-all duration-300 sm:text-3xl ${active ? 'text-white' : past ? 'text-neutral-600' : 'text-neutral-500'} hover:text-violet-300`}>
                    
                      {line.text}
                    </button>
                  </li>);

            })}
            </ul>
          </div>
        </motion.div>
      }
    </AnimatePresence>);

}