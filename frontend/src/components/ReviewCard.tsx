import type { Review } from "@/data/reviews";

export function Stars({ n, label, size = "h-4 w-4" }: { n: number; label: string; size?: string }) {
  return (
    <span role="img" aria-label={label} className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <svg key={i} viewBox="0 0 20 20" aria-hidden className={`${size} ${i <= n ? "fill-saffron-500" : "fill-grid"}`}>
          <path d="M10 1.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8L10 14.9l-5.2 2.7 1-5.8L1.6 7.7l5.8-.8z" />
        </svg>
      ))}
    </span>
  );
}

// Carte d'avis : le texte garde sa langue et son sens d'écriture, quelle que soit la langue de l'interface
export function ReviewCard({ r, date, dateLabel, profileLabel, starsLabel }:
  { r: Review; date: Date; dateLabel: string; profileLabel: string; starsLabel: string }) {
  return (
    <figure dir={r.lang === "ar" ? "rtl" : "ltr"} lang={r.lang}
      className="flex h-full flex-col rounded-2xl border border-line bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <Stars n={r.rating} label={starsLabel} />
        <span className="shrink-0 whitespace-nowrap rounded-full bg-chip px-2 py-0.5 text-[11px] font-medium text-muted">{profileLabel}</span>
      </div>
      <blockquote className="mt-3 flex-1 text-sm leading-relaxed text-ink-soft">{r.text}</blockquote>
      <figcaption className="mt-4 flex items-center gap-3">
        <span aria-hidden className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent-soft text-sm font-bold text-accent-ink">
          {r.name.charAt(0)}
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink">{r.name}</span>
          <span className="line-clamp-2 block text-xs text-muted">{r.role}</span>
          <time dir="auto" dateTime={date.toISOString().slice(0, 10)} className="mt-0.5 block text-xs text-muted/80">{dateLabel}</time>
        </span>
      </figcaption>
    </figure>
  );
}
