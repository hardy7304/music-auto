export interface LyricLine {
  time: number; // seconds the line starts
  text: string;
}

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  cover: string;
  duration: number; // seconds
  audioUrl?: string; // public/streamable audio URL (e.g. Cloudflare R2). Swap demo URLs for your own.
  lyrics?: LyricLine[]; // time-synced lyrics
}

export interface Artist {
  id: string;
  name: string;
  genre: string;
  image: string;
  followers: string;
  bio?: string;
}

export interface Playlist {
  id: string;
  title: string;
  description: string;
  cover: string;
  trackCount: number;
}

const COVERS = [
'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1487180144351-b8472da7d491?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1499415479124-43c32433a620?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1507838153414-b4b713384a76?auto=format&fit=crop&w=600&q=80'];


const ARTIST_IMAGES = [
'https://images.unsplash.com/photo-1493666438817-866a91353ca9?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1549213783-8284d0336c4f?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1535201344177-6cf6f99b9908?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=600&q=80',
'https://images.unsplash.com/photo-1529068755536-a5ade0dcb4e8?auto=format&fit=crop&w=600&q=80'];


export const newReleases: Track[] = [
{
  id: 't1',
  title: 'Neon Tide',
  artist: 'Aurelia Quinn',
  album: 'Glass Horizons',
  cover: COVERS[0],
  duration: 214,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
},
{
  id: 't2',
  title: 'Midnight Cartography',
  artist: 'The Velvet Static',
  album: 'Northbound',
  cover: COVERS[1],
  duration: 187,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3'
},
{
  id: 't3',
  title: 'Paper Lanterns',
  artist: 'Kairo Sound',
  album: 'Drift',
  cover: COVERS[2],
  duration: 242,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3'
},
{
  id: 't4',
  title: 'Echo Garden',
  artist: 'Mara Lune',
  album: 'Bloomfall',
  cover: COVERS[3],
  duration: 198,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3'
},
{
  id: 't5',
  title: 'Slow Comet',
  artist: 'Halcyon Field',
  album: 'Orbit Theory',
  cover: COVERS[4],
  duration: 233,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3'
},
{
  id: 't6',
  title: 'Saltwater Pulse',
  artist: 'Indigo Harbor',
  album: 'Tide & Time',
  cover: COVERS[5],
  duration: 205,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3'
}];


export const trending: Track[] = [
{
  id: 't7',
  title: 'Crystal Avenue',
  artist: 'Nova Reign',
  album: 'Citylight',
  cover: COVERS[6],
  duration: 221,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3'
},
{
  id: 't8',
  title: 'Heatwave',
  artist: 'Solene',
  album: 'Ember',
  cover: COVERS[7],
  duration: 176,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3'
},
{
  id: 't9',
  title: 'Ghost Frequency',
  artist: 'The Velvet Static',
  album: 'Northbound',
  cover: COVERS[1],
  duration: 259,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3'
},
{
  id: 't10',
  title: 'Lowlight',
  artist: 'Kairo Sound',
  album: 'Drift',
  cover: COVERS[2],
  duration: 190,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3'
},
{
  id: 't11',
  title: 'Goldenrod',
  artist: 'Mara Lune',
  album: 'Bloomfall',
  cover: COVERS[3],
  duration: 212,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3'
},
{
  id: 't12',
  title: 'Afterglow',
  artist: 'Aurelia Quinn',
  album: 'Glass Horizons',
  cover: COVERS[0],
  duration: 228,
  audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3'
}];


export const featuredArtists: Artist[] = [
{
  id: 'a1',
  name: 'Aurelia Quinn',
  genre: 'Dream Pop',
  image: ARTIST_IMAGES[0],
  followers: '1.2M',
  bio: 'Aurelia Quinn crafts widescreen dream pop drenched in reverb and warm analog synths. Her records feel like late-night drives along a glowing coastline.'
},
{
  id: 'a2',
  name: 'The Velvet Static',
  genre: 'Indie Rock',
  image: ARTIST_IMAGES[1],
  followers: '880K',
  bio: 'A four-piece known for their hazy guitars and restless rhythms, The Velvet Static blur the line between garage rock and shoegaze.'
},
{
  id: 'a3',
  name: 'Kairo Sound',
  genre: 'Electronic',
  image: ARTIST_IMAGES[2],
  followers: '2.4M',
  bio: 'Producer and sound designer Kairo Sound builds intricate electronic landscapes — equal parts club energy and ambient introspection.'
},
{
  id: 'a4',
  name: 'Mara Lune',
  genre: 'Folk',
  image: ARTIST_IMAGES[3],
  followers: '640K',
  bio: 'Singer-songwriter Mara Lune pairs fingerpicked guitar with intimate storytelling, capturing the quiet poetry of everyday life.'
},
{
  id: 'a5',
  name: 'Nova Reign',
  genre: 'R&B',
  image: ARTIST_IMAGES[4],
  followers: '3.1M',
  bio: 'Nova Reign delivers silky, modern R&B with sharp lyricism and a flair for cinematic production.'
},
{
  id: 'a6',
  name: 'Halcyon Field',
  genre: 'Ambient',
  image: ARTIST_IMAGES[5],
  followers: '410K',
  bio: 'Halcyon Field composes slow-moving ambient pieces designed for focus, rest, and the spaces in between.'
}];


export const madeForYou: Playlist[] = [
{
  id: 'p1',
  title: 'Daily Mix 01',
  description: 'Aurelia Quinn, Mara Lune and more',
  cover: COVERS[0],
  trackCount: 30
},
{
  id: 'p2',
  title: 'Late Night Drift',
  description: 'Slow electronic for the quiet hours',
  cover: COVERS[4],
  trackCount: 42
},
{
  id: 'p3',
  title: 'Fresh Finds',
  description: 'New tracks picked for your taste',
  cover: COVERS[6],
  trackCount: 25
},
{
  id: 'p4',
  title: 'Focus Flow',
  description: 'Instrumental concentration',
  cover: COVERS[5],
  trackCount: 60
},
{
  id: 'p5',
  title: 'Coastal Pop',
  description: 'Bright, breezy and warm',
  cover: COVERS[2],
  trackCount: 38
}];


export const userPlaylists = [
'Liked Songs',
'Late Night Drift',
'Coastal Pop',
'Focus Flow',
'Road Trip 2026',
'Acoustic Mornings',
'Workout Heat'];


export const featuredHero = {
  track: newReleases[0],
  tagline: 'New Release',
  blurb:
  'Aurelia Quinn returns with a luminous full-length record — twelve tracks of widescreen dream pop.'
};

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// Full catalogue used as the default radio / autoplay queue.
export const allTracks: Track[] = [...newReleases, ...trending];

// Look up an artist by id.
export function getArtistById(id: string): Artist | undefined {
  return featuredArtists.find((a) => a.id === id);
}

// All tracks (across catalogues) performed by the given artist name.
export function getArtistTracks(artistName: string): Track[] {
  return [...newReleases, ...trending].filter((t) => t.artist === artistName);
}

// Demo synced lyrics keyed by track id. Replace with your own real lyrics.
const LYRICS: Record<string, LyricLine[]> = {
  t1: [
  { time: 0, text: 'Neon tide rolling over the bay' },
  { time: 8, text: 'City lights bleeding into the grey' },
  { time: 16, text: 'I follow the glow till it fades away' },
  { time: 24, text: 'Holding your hand on the edge of the day' },
  { time: 34, text: '(Oh) we drift, we drift, we drift' },
  { time: 44, text: 'Into the violet hour' },
  { time: 54, text: 'Where the quiet becomes a song' },
  { time: 66, text: 'And the night is ours alone' },
  { time: 80, text: 'Neon tide, carry me home' },
  { time: 92, text: 'Carry me home, carry me home' }],

  t7: [
  { time: 0, text: 'Down on Crystal Avenue' },
  { time: 9, text: 'Every window knows your name' },
  { time: 18, text: 'I keep walking, chasing you' },
  { time: 27, text: 'Through the rain and the neon flame' },
  { time: 38, text: 'Tell me, are you still awake?' },
  { time: 48, text: 'Counting headlights, one by one' },
  { time: 60, text: 'There is nothing left to fake' },
  { time: 72, text: 'When the morning steals the sun' }]

};

// Returns synced lyrics for a track, generating evenly-spaced placeholder lines if none exist.
export function getLyrics(track: Track): LyricLine[] {
  if (track.lyrics?.length) return track.lyrics;
  if (LYRICS[track.id]) return LYRICS[track.id];
  // Placeholder: evenly distribute generic lines across the duration so the view is never empty.
  const lines = [
  'La la la, carried on the melody',
  'Soft and slow, the rhythm sets us free',
  'Close your eyes and let the music play',
  'We will hum these notes until the break of day',
  'Hold the sound, let it linger in the air',
  'Every beat a promise that we share'];

  const span = Math.max(track.duration, lines.length * 6);
  const step = span / (lines.length + 1);
  return lines.map((text, i) => ({ time: Math.round(step * (i + 1)), text }));
}