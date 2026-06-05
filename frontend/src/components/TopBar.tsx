import React from 'react';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';
interface TopBarProps {
  query: string;
  onQueryChange: (q: string) => void;
  onSearchFocus: () => void;
}
export function TopBar({ query, onQueryChange, onSearchFocus }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-4 bg-neutral-900/80 px-4 py-3 backdrop-blur-md md:px-6">
      <div className="hidden gap-2 sm:flex">
        <button
          aria-label="Go back"
          className="rounded-full bg-black/40 p-1.5 text-neutral-400 transition-colors hover:text-white">
          
          <ChevronLeft className="h-5 w-5" aria-hidden="true" />
        </button>
        <button
          aria-label="Go forward"
          className="rounded-full bg-black/40 p-1.5 text-neutral-400 transition-colors hover:text-white">
          
          <ChevronRight className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <div className="relative flex-1 max-w-md">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500"
          aria-hidden="true" />
        
        <label htmlFor="global-search" className="sr-only">
          Search music
        </label>
        <input
          id="global-search"
          type="search"
          value={query}
          onFocus={onSearchFocus}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="What do you want to listen to?"
          className="w-full rounded-full border border-transparent bg-neutral-800 py-2 pl-10 pr-4 text-sm text-white placeholder:text-neutral-500 transition-colors focus:border-violet-500 focus:bg-neutral-800 focus:outline-none" />
        
      </div>

      <button
        aria-label="Account"
        className="ml-auto flex h-9 w-9 items-center justify-center rounded-full bg-violet-500 text-sm font-semibold text-white">
        
        SR
      </button>
    </header>);

}