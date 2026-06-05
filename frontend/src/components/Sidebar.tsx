import React from 'react';
import { motion } from 'framer-motion';
import { Home, Search, Library, Plus, Heart, AudioLines, Cpu } from 'lucide-react';
import { userPlaylists } from '../data/music';
interface SidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
}
const navItems = [
{
  id: 'home',
  label: 'Home',
  icon: Home
},
{
  id: 'search',
  label: 'Search',
  icon: Search
},
{
  id: 'library',
  label: 'Your Library',
  icon: Library
},
{
  id: 'automation',
  label: 'Automation',
  icon: Cpu
}];

export function Sidebar({ activeView, onNavigate }: SidebarProps) {
  return (
    <nav
      aria-label="Primary"
      className="hidden md:flex w-64 shrink-0 flex-col gap-2 bg-neutral-950 p-3 text-neutral-300">
      
      <div className="flex items-center gap-2 px-3 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-500">
          <AudioLines className="h-5 w-5 text-white" aria-hidden="true" />
        </div>
        <span className="text-xl font-semibold tracking-tight text-white">
          Sonora
        </span>
      </div>

      <ul className="space-y-1 rounded-xl bg-neutral-900/60 p-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = activeView === item.id;
          return (
            <li key={item.id}>
              <button
                onClick={() => onNavigate(item.id)}
                aria-current={active ? 'page' : undefined}
                className={`flex w-full items-center gap-4 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${active ? 'bg-neutral-800 text-white' : 'text-neutral-400 hover:text-white'}`}>
                
                <Icon className="h-5 w-5" aria-hidden="true" />
                {item.label}
              </button>
            </li>);

        })}
      </ul>

      <div className="mt-2 flex min-h-0 flex-1 flex-col rounded-xl bg-neutral-900/60 p-2">
        <div className="flex items-center justify-between px-2 py-2">
          <h2 className="text-sm font-semibold text-neutral-300">
            Your Playlists
          </h2>
          <button
            aria-label="Create playlist"
            className="rounded-full p-1.5 text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-white">
            
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto">
          {userPlaylists.map((name, i) =>
          <li key={name}>
              <motion.button
              whileHover={{
                x: 2
              }}
              onClick={() => onNavigate('library')}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-white">
              
                {i === 0 ?
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-violet-500/20">
                    <Heart
                  className="h-4 w-4 text-violet-400"
                  aria-hidden="true" />
                
                  </span> :

              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-neutral-800 text-xs font-medium text-neutral-500">
                    {name.charAt(0)}
                  </span>
              }
                <span className="truncate">{name}</span>
              </motion.button>
            </li>
          )}
        </ul>
      </div>
    </nav>);

}