import React from 'react';
import { TrackCard } from '../components/TrackCard';
import { newReleases, trending } from '../data/music';
const genres = [
{
  name: 'Dream Pop',
  color: 'bg-violet-600'
},
{
  name: 'Electronic',
  color: 'bg-sky-600'
},
{
  name: 'Indie Rock',
  color: 'bg-rose-600'
},
{
  name: 'Folk',
  color: 'bg-amber-600'
},
{
  name: 'R&B',
  color: 'bg-emerald-600'
},
{
  name: 'Ambient',
  color: 'bg-indigo-600'
}];

export function SearchView({ query }: {query: string;}) {
  const all = [...newReleases, ...trending];
  const results = query ?
  all.filter(
    (t) =>
    t.title.toLowerCase().includes(query.toLowerCase()) ||
    t.artist.toLowerCase().includes(query.toLowerCase())
  ) :
  [];
  if (query) {
    return (
      <div>
        <h1 className="mb-6 text-2xl font-bold text-white">
          Results for “{query}”
        </h1>
        {results.length ?
        <div className="flex flex-wrap gap-4">
            {results.map((t) =>
          <TrackCard key={t.id} track={t} />
          )}
          </div> :

        <p className="text-neutral-400">No tracks match your search.</p>
        }
      </div>);

  }
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-white">Browse all</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {genres.map((g) =>
        <div
          key={g.name}
          className={`relative aspect-[4/3] overflow-hidden rounded-xl ${g.color} p-4`}>
          
            <h2 className="text-lg font-bold text-white">{g.name}</h2>
          </div>
        )}
      </div>
    </div>);

}