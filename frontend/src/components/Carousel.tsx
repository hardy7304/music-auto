import React from 'react';
interface CarouselProps {
  title: string;
  children: React.ReactNode;
}
export function Carousel({ title, children }: CarouselProps) {
  return (
    <section className="mt-8">
      <div className="mb-4 flex items-baseline justify-between px-1">
        <h2 className="text-xl font-bold text-white">{title}</h2>
        <button className="text-xs font-semibold uppercase tracking-wider text-neutral-400 transition-colors hover:text-white">
          Show all
        </button>
      </div>
      <div className="flex gap-4 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {children}
      </div>
    </section>);

}