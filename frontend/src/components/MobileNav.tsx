import React from 'react';
import { Home, Search, Library } from 'lucide-react';
interface MobileNavProps {
  activeView: string;
  onNavigate: (view: string) => void;
}
const items = [
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
  label: 'Library',
  icon: Library
}];

export function MobileNav({ activeView, onNavigate }: MobileNavProps) {
  return (
    <nav
      aria-label="Mobile primary"
      className="flex items-center justify-around border-t border-neutral-800 bg-neutral-950 py-2 md:hidden">
      
      {items.map((item) => {
        const Icon = item.icon;
        const active = activeView === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            aria-current={active ? 'page' : undefined}
            className={`flex flex-col items-center gap-1 px-4 py-1 text-xs ${active ? 'text-violet-400' : 'text-neutral-400'}`}>
            
            <Icon className="h-5 w-5" aria-hidden="true" />
            {item.label}
          </button>);

      })}
    </nav>);

}