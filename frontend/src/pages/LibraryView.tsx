import React, { useState } from 'react';
import { TrackListItem } from '../components/TrackListItem';
import { usePlayer } from '../context/PlayerContext';
import { STANDARD_GENRES } from '../constants/genres';

export function LibraryView() {
  const { downloadedTracks } = usePlayer();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('');

  const filteredTracks = downloadedTracks.filter(track => {
    const matchSearch = track.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        track.artist.toLowerCase().includes(searchTerm.toLowerCase());
    const matchGenre = !selectedGenre || track.genre === selectedGenre || (selectedGenre === 'Uncategorized' && (!track.genre || track.genre === 'Uncategorized'));
    return matchSearch && matchGenre;
  });

  const availableGenres = Array.from(new Set(downloadedTracks.map(t => t.genre || 'Uncategorized')));

  // Calculate counts for each genre
  const genreCounts = downloadedTracks.reduce((acc, track) => {
    const genre = track.genre || 'Uncategorized';
    acc[genre] = (acc[genre] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div>
      <div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <h1 className="text-2xl font-bold text-white">專屬曲庫 ({downloadedTracks.length})</h1>
        <div className="flex w-full sm:max-w-md">
          <input
            type="text"
            placeholder="搜尋曲庫中的歌名或作者..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg bg-neutral-800 px-4 py-2 text-sm text-white placeholder-neutral-500 outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      </div>

      {/* Pill buttons for genres */}
      <div className="mb-6 flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        <button
          onClick={() => setSelectedGenre('')}
          className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${selectedGenre === '' ? 'bg-white text-black' : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700 hover:text-white'}`}
        >
          所有曲風 <span className="ml-1 opacity-60">({downloadedTracks.length})</span>
        </button>
        
        {Object.entries(genreCounts)
          .sort((a, b) => b[1] - a[1])
          .map(([genre, count]) => (
          <button
            key={genre}
            onClick={() => setSelectedGenre(genre)}
            className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${selectedGenre === genre ? 'bg-violet-500 text-white' : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700 hover:text-white'}`}
          >
            {genre} <span className="ml-1 opacity-60">({count})</span>
          </button>
        ))}
      </div>
      
      <datalist id="standard-genres">
        {STANDARD_GENRES.map(g => <option key={g} value={g} />)}
        {availableGenres.filter(g => !STANDARD_GENRES.includes(g)).map(g => <option key={g} value={g} />)}
      </datalist>
      
      {filteredTracks.length > 0 ? (
        <div className="flex flex-col gap-1">
          {filteredTracks.map((t) => (
            <TrackListItem key={t.id} track={t} />
          ))}
        </div>
      ) : (
        <p className="py-12 text-center text-sm text-neutral-500">
          {downloadedTracks.length === 0 ? "目前還沒有下載任何歌曲喔！" : "找不到相符的歌曲。"}
        </p>
      )}
    </div>
  );
}