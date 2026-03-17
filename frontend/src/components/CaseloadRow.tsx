"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { counselorSuggestions } from "@/app/actions";

type Item = { id: number; name: string; city: string | null; status: string; headline: string | null; has_cv: boolean;
  applications: number; idle_days: number; anapec_registered: boolean; reasons: string[] | null };
type L = { status: Record<string, string>; idle: string; apps: string; noCv: string; suggest: string; suggestions: string; none: string; registeredAnapec: string };
type Sugg = { offer: { id: number; title: string; city: string | null; source_name: string }; score: number; matched: string[] }[];

const TONE: Record<string, string> = {
  active: "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300",
  to_remind: "bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300",
  dormant: "bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300",
  ghost: "bg-chip text-muted", duplicate: "bg-chip text-muted",
};

export function CaseloadRow({ item, lang, t }: { item: Item; lang: string; t: L }) {
  const [sugg, setSugg] = useState<Sugg | null>(null);
  const [pending, start] = useTransition();
  return (
    <li className="rounded-2xl border border-line bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-ink">{item.name}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${TONE[item.status] ?? ""}`}>{t.status[item.status] ?? item.status}</span>
        {item.anapec_registered && <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-ink">{t.registeredAnapec}</span>}
        <span className="ms-auto text-xs text-muted">{t.idle} · {t.apps}{item.has_cv ? "" : ` · ${t.noCv}`}</span>
      </div>
      <p className="mt-1 text-sm text-muted">{[item.headline, item.city].filter(Boolean).join(" · ")}</p>
      {item.reasons && <p className="mt-1 text-xs text-muted">{item.reasons.join(", ")}</p>}
      {item.has_cv && !sugg && (
        <button disabled={pending} onClick={() => start(async () => setSugg(await counselorSuggestions(item.id, lang)))}
          className="mt-3 rounded-lg border border-brand-600 px-3 py-1.5 text-xs font-semibold text-accent-ink hover:bg-accent-soft disabled:opacity-60">
          {pending ? "…" : t.suggest}
        </button>
      )}
      {sugg && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{t.suggestions}</p>
          {sugg.length === 0 ? <p className="mt-1 text-sm text-muted">{t.none}</p> : (
            <ul className="mt-2 space-y-1.5">
              {sugg.map((m) => (
                <li key={m.offer.id} className="flex items-center gap-3 text-sm">
                  <span className="grid h-8 w-10 shrink-0 place-items-center rounded-lg bg-brand-600 text-xs font-bold text-white">{m.score}</span>
                  <Link href={`/${lang}/offres/${m.offer.id}`} className="min-w-0 truncate text-ink hover:text-accent-ink">{m.offer.title}</Link>
                  <span className="shrink-0 text-xs text-muted">{[m.offer.city, m.offer.source_name].filter(Boolean).join(" · ")}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  );
}
