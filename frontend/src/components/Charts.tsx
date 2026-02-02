"use client";

// Graphiques de l'Observatoire : série unique (pas de légende, le titre nomme la mesure),
// barres <= 24 px à extrémité arrondie, valeur en bout de barre, infobulle au survol ET au focus clavier,
// et tableau des données repliable pour l'accessibilité.
import { useState } from "react";

type Row = { label: string; value: number; hint?: string };

const fmt = (n: number, locale: string) => n.toLocaleString(locale);

export function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-5 shadow-sm">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-ink">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}

function DataTable({ rows, head, locale }: { rows: Row[]; head: [string, string]; locale: string }) {
  return (
    <details className="mt-3 text-xs">
      <summary className="cursor-pointer text-muted hover:text-ink">{locale.startsWith("ar") ? "عرض البيانات" : locale.startsWith("en") ? "View data" : "Voir les données"}</summary>
      <table className="mt-2 w-full">
        <thead><tr className="text-muted"><th className="py-1 text-start font-medium">{head[0]}</th><th className="py-1 text-end font-medium">{head[1]}</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.label} className="border-t border-line"><td className="py-1 text-ink-soft">{r.label}</td><td className="py-1 text-end tabular-nums text-ink">{fmt(r.value, locale)}</td></tr>)}</tbody>
      </table>
    </details>
  );
}

export function BarList({ title, rows, locale, head }: { title: string; rows: Row[]; locale: string; head: [string, string] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  const [hover, setHover] = useState<number | null>(null);
  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
      <h3 className="font-semibold text-ink">{title}</h3>
      <ul className="mt-4 space-y-2.5">
        {rows.map((r, i) => (
          <li key={r.label} className="relative grid grid-cols-[minmax(0,11rem)_1fr] items-center gap-3 text-sm"
            tabIndex={0} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(i)} onBlur={() => setHover(null)} aria-label={`${r.label} : ${fmt(r.value, locale)}`}>
            <span className="truncate text-ink-soft" title={r.label}>{r.label}</span>
            <span className="flex items-center gap-2">
              <span className="h-5 rounded-e-[4px] bg-viz transition-opacity"
                style={{ width: `${Math.max(2, (r.value / max) * 100)}%`, opacity: hover === null || hover === i ? 1 : 0.55 }} />
              <span className="shrink-0 text-xs tabular-nums text-muted">{fmt(r.value, locale)}</span>
            </span>
            {hover === i && r.hint && (
              <span className="pointer-events-none absolute -top-8 end-0 z-10 rounded-lg border border-line bg-card px-2.5 py-1 text-xs shadow-md">
                <b className="text-ink">{fmt(r.value, locale)}</b> <span className="text-muted">{r.hint}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
      <DataTable rows={rows} head={head} locale={locale} />
    </section>
  );
}

export function Columns({ title, rows, locale, head, height = 140 }:
  { title: string; rows: Row[]; locale: string; head: [string, string]; height?: number }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  const [hover, setHover] = useState<number | null>(null);
  const last = rows.length - 1;
  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
      <h3 className="font-semibold text-ink">{title}</h3>
      <div className="relative mt-6 flex items-end gap-[2px] border-b border-grid" style={{ height }}>
        {rows.map((r, i) => (
          <div key={r.label} className="group relative flex h-full flex-1 items-end justify-center" tabIndex={0}
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
            aria-label={`${r.label} : ${fmt(r.value, locale)}`}>
            <div className="w-full max-w-6 rounded-t-[4px] bg-viz transition-opacity"
              style={{ height: `${(r.value / max) * 100}%`, minHeight: r.value ? 2 : 0, opacity: hover === null || hover === i ? 1 : 0.55 }} />
            {(i === last || hover === i) && (
              <span className={`pointer-events-none absolute -top-6 whitespace-nowrap text-xs tabular-nums ${hover === i ? "rounded-md border border-line bg-card px-1.5 py-0.5 font-semibold text-ink shadow-sm" : "text-muted"}`}>
                {fmt(r.value, locale)}{hover === i ? <span className="ms-1 font-normal text-muted">{r.label}</span> : null}
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-muted"><span>{rows[0]?.label}</span><span>{rows[last]?.label}</span></div>
      <DataTable rows={rows} head={head} locale={locale} />
    </section>
  );
}
