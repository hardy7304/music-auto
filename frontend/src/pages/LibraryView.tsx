import React, { useState } from 'react';
import { TrackCard } from '../components/TrackCard';
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

  return (
    <div>
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <h1 className="text-2xl font-bold text-white">專屬曲庫 ({downloadedTracks.length})</h1>
        <div className="flex w-full gap-2 sm:max-w-md">
          <select
            value={selectedGenre}
            onChange={(e) => setSelectedGenre(e.target.value)}
            className="w-1/3 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500"
          >
            <option value="">所有曲風</option>
            {STANDARD_GENRES.map(g => (
              <option key={g} value={g}>{g}</option>
            ))}
            {availableGenres.filter(g => !STANDARD_GENRES.includes(g)).map(g => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="搜尋曲庫中的歌名或作者..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-2/3 rounded-lg bg-neutral-800 px-4 py-2 text-sm text-white placeholder-neutral-500 outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      </div>
      
      <datalist id="standard-genres">
        {STANDARD_GENRES.map(g => <option key={g} value={g} />)}
        {availableGenres.filter(g => !STANDARD_GENRES.includes(g)).map(g => <option key={g} value={g} />)}
      </datalist>
      
      {filteredTracks.length > 0 ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {filteredTracks.map((t) => (
            <TrackCard key={t.id} track={t} />
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