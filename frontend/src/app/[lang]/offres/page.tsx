import Link from "next/link";
import { notFound } from "next/navigation";

import { Filters } from "@/components/Filters";
import { OfferCard } from "@/components/OfferCard";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { getFacets, searchOffers } from "@/lib/api";

const SIZE = 20;

export default async function OffersPage({ params, searchParams }: PageProps<"/[lang]/offres">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const sp = await searchParams;
  const one = (k: string) => (typeof sp[k] === "string" ? (sp[k] as string) : undefined);
  const page = Math.max(1, Number(one("page") ?? 1));
  const filters = { q: one("q"), region: one("region"), contract: one("contract"), source: one("source"),
    function: one("function"), sector_group: one("sector_group"), experience: one("experience"), since: one("since") };
  const [res, facets] = await Promise.all([
    searchOffers({ ...filters, lang, page: String(page), size: String(SIZE) }),
    getFacets(),
  ]);
  const pages = Math.ceil(res.total / SIZE);
  const link = (p: number) => {
    const qs = new URLSearchParams(Object.entries({ ...filters, page: String(p) }).filter(([, v]) => v) as [string, string][]);
    return `/${lang}/offres?${qs}`;
  };

  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[260px_1fr]">
      <aside className="min-w-0 md:sticky md:top-24 md:self-start">
        <h2 className="mb-4 text-sm font-bold text-ink">{t.offers.filters}</h2>
        <Filters facets={facets} t={{
          all: t.offers.all, reset: t.offers.reset, region: t.offers.region, contract: t.offers.contract,
          source: t.offers.source, searchPlaceholder: t.home.searchPlaceholder, contracts: t.contracts, regions: t.regions,
          function: t.facets.function, sector: t.facets.sector, experience: t.facets.experience, since: t.facets.since,
          sinceOptions: t.facets.sinceOptions, functions: t.functions, sectors: t.sectors, experiences: t.experiences,
        }} />
      </aside>
      <section className="min-w-0">
        <div className="flex items-baseline justify-between">
          <h1 className="text-2xl font-bold text-ink">{t.offers.title}</h1>
          <span className="text-sm text-muted">{t.offers.results(res.total)}</span>
        </div>
        {res.items.length === 0 ? (
          <p className="mt-10 rounded-2xl border border-dashed border-line bg-card p-10 text-center text-muted">{t.offers.empty}</p>
        ) : (
          <div className="mt-6 grid gap-3 lg:grid-cols-2">
            {res.items.map((o) => <OfferCard key={o.id} o={o} lang={lang} t={t} />)}
          </div>
        )}
        {pages > 1 && (
          <nav className="mt-8 flex items-center justify-center gap-3 text-sm">
            {page > 1 && <Link href={link(page - 1)} className="rounded-lg border border-line bg-card px-3 py-1.5 hover:bg-accent-soft">{t.offers.prev}</Link>}
            <span className="text-muted">{page} / {pages}</span>
            {page < pages && <Link href={link(page + 1)} className="rounded-lg border border-line bg-card px-3 py-1.5 hover:bg-accent-soft">{t.offers.next}</Link>}
          </nav>
        )}
      </section>
    </div>
  );
}
