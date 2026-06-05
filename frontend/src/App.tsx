import React, { useState } from 'react';
import { PlayerProvider } from './context/PlayerContext';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { PlayerBar } from './components/PlayerBar';
import { MobileNav } from './components/MobileNav';
import { LyricsView } from './components/LyricsView';
import { HomeView } from './pages/HomeView';
import { SearchView } from './pages/SearchView';
import { LibraryView } from './pages/LibraryView';
import { ArtistView } from './pages/ArtistView';
import { AutomationView } from './pages/AutomationView';
import { useScreenInit } from './useScreenInit.js';
export function App() {
  const screenInit = useScreenInit() as {
    activeView?: string;
    selectedArtist?: string;
  };
  const [activeView, setActiveView] = useState(screenInit?.activeView ?? 'home');
  const [query, setQuery] = useState('');
  const [selectedArtist, setSelectedArtist] = useState<string | null>(
    screenInit?.selectedArtist ?? null
  );
  const handleNavigate = (view: string) => setActiveView(view);
  const handleSelectArtist = (artistId: string) => {
    setSelectedArtist(artistId);
    setActiveView('artist');
  };
  return (
    <PlayerProvider>
      <div className="dark flex h-screen w-full flex-col overflow-hidden bg-black font-sans text-white">
        <div className="flex min-h-0 flex-1 gap-2 p-2">
          <Sidebar activeView={activeView} onNavigate={handleNavigate} />
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl bg-neutral-900">
            <TopBar
              query={query}
              onQueryChange={(q) => {
                setQuery(q);
                if (q && activeView !== 'search') setActiveView('search');
              }}
              onSearchFocus={() => setActiveView('search')} />
            
            <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-6">
              {activeView === 'home' &&
              <HomeView onSelectArtist={handleSelectArtist} />
              }
              {activeView === 'search' && <SearchView query={query} />}
              {activeView === 'library' && <LibraryView />}
              {activeView === 'automation' && <AutomationView />}
              {activeView === 'artist' && selectedArtist &&
              <ArtistView
                artistId={selectedArtist}
                onBack={() => setActiveView('home')} />

              }
            </main>
          </div>
        </div>
        <PlayerBar />
        <MobileNav activeView={activeView} onNavigate={handleNavigate} />
        <LyricsView />
      </div>
    </PlayerProvider>);

}