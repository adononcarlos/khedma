import Link from "next/link";

import type { Dict, Locale } from "@/i18n/dictionaries";
import type { OfferCard as Offer } from "@/lib/api";

const SOURCE_STYLE: Record<string, string> = {
  anapec: "bg-fuchsia-50 dark:bg-fuchsia-950/50 text-fuchsia-700 dark:text-fuchsia-300 ring-fuchsia-200",
  indeed: "bg-sky-50 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 ring-sky-200",
};

export function formatDate(d: string | null, lang: Locale) {
  if (!d) return null;
  return new Date(d).toLocaleDateString(lang === "ar" ? "ar-MA" : lang === "en" ? "en-GB" : "fr-FR",
    { day: "numeric", month: "short" });
}

export function Tag({ children, tone = "zinc" }: { children: React.ReactNode; tone?: "zinc" | "brand" | "green" }) {
  const tones = {
    zinc: "bg-chip text-ink-soft",
    brand: "bg-accent-soft text-accent-ink",
    green: "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300",
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

export function OfferCard({ o, lang, t }: { o: Offer; lang: Locale; t: Dict }) {
  return (
    <Link href={`/${lang}/offres/${o.id}`}
      className="group block rounded-2xl border border-line bg-card p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-ink group-hover:text-accent-ink" dir="auto">{o.title}</h3>
          <p className="mt-0.5 truncate text-sm text-muted" dir="auto">
            {[o.company, o.city].filter(Boolean).join(" · ")}
          </p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${SOURCE_STYLE[o.source] ?? "bg-chip text-muted ring-zinc-200"}`}>
          {o.source_name}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        {o.contract_type && <Tag tone={o.contract_type === "IDMAJ" ? "brand" : "zinc"}>{t.contracts[o.contract_type] ?? o.contract_type}</Tag>}
        {o.region && <Tag>{t.regions[o.region] ?? o.region}</Tag>}
        {o.positions && o.positions > 1 && <Tag tone="green">{t.offers.positions(o.positions)}</Tag>}
        {o.language !== "fr" && <Tag>{o.language.toUpperCase()}</Tag>}
        <span className="ms-auto text-xs text-muted">{formatDate(o.posted_at, lang)}</span>
      </div>
    </Link>
  );
}
