import React from 'react';
import { Hero } from '../components/Hero';
import { Carousel } from '../components/Carousel';
import { TrackCard } from '../components/TrackCard';
import { ArtistCard } from '../components/ArtistCard';
import { PlaylistCard } from '../components/PlaylistCard';
import { usePlayer } from '../context/PlayerContext';
import {
  newReleases,
  trending,
  featuredArtists,
  madeForYou } from
  '../data/music';

interface HomeViewProps {
  onSelectArtist?: (artistId: string) => void;
}

export function HomeView({ onSelectArtist }: HomeViewProps) {
  const { downloadedTracks } = usePlayer();

  // If we have downloaded tracks, use them as releases and trending. Otherwise fall back to mock data.
  const displayReleases = downloadedTracks.length > 0 ? downloadedTracks.slice(0, 10) : newReleases;
  const displayTrending = downloadedTracks.length > 10 ? downloadedTracks.slice(10, 20) : (downloadedTracks.length > 0 ? downloadedTracks : trending);

  return (
    <div>
      <Hero />
      <Carousel title={downloadedTracks.length > 0 ? "最新下載的歌曲 (Recent Downloads)" : "New Releases"}>
        {displayReleases.map((t) =>
        <TrackCard key={t.id} track={t} />
        )}
      </Carousel>
      <Carousel title="Made For You">
        {madeForYou.map((p) =>
        <PlaylistCard key={p.id} playlist={p} />
        )}
      </Carousel>
      <Carousel title="Featured Artists">
        {featuredArtists.map((a) =>
        <ArtistCard key={a.id} artist={a} onSelect={onSelectArtist} />
        )}
      </Carousel>
      <Carousel title="Trending Now">
        {displayTrending.map((t) =>
        <TrackCard key={t.id} track={t} />
        )}
      </Carousel>
    </div>);
}