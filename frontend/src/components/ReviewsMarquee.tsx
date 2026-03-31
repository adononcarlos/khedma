import type { ReactNode } from "react";

// Bandeau d'avis qui défile en continu (CSS seul, voir globals.css) : pause au survol,
// défilement désactivé si l'utilisateur limite les animations. La liste est dupliquée
// pour une boucle sans à-coup ; la copie est masquée aux lecteurs d'écran.
export function ReviewsMarquee({ items, reverse = false, seconds = 120 }:
  { items: { key: number; node: ReactNode }[]; reverse?: boolean; seconds?: number }) {
  const copy = (hidden: boolean) => items.map((it) => (
    <div key={`${hidden ? "b" : "a"}-${it.key}`} aria-hidden={hidden || undefined} className="w-[19rem] shrink-0 pr-4 sm:w-[22rem]">
      {it.node}
    </div>
  ));
  return (
    <div dir="ltr" className="marquee overflow-hidden py-1">
      <div className={`marquee-track flex w-max items-stretch${reverse ? " marquee-reverse" : ""}`}
        style={{ animationDuration: `${seconds}s` }}>
        {copy(false)}
        {copy(true)}
      </div>
    </div>
  );
}
