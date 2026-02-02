import Link from "next/link";
import { notFound } from "next/navigation";

import { OfferCard } from "@/components/OfferCard";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { searchOffers } from "@/lib/api";

export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const latest = await searchOffers({ size: "6", lang });
  const stats = [{ n: latest.total.toLocaleString(lang === "ar" ? "ar-MA" : "fr-FR"), l: t.home.stats.offers }];

  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-900 via-brand-700 to-brand-600 text-white">
        <div className="pointer-events-none absolute inset-0 opacity-10"
          style={{ backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)", backgroundSize: "22px 22px" }} />
        <div className="relative mx-auto max-w-6xl px-4 py-16 md:py-24">
          <h1 className="max-w-2xl text-4xl font-bold leading-tight tracking-tight md:text-5xl">{t.home.title}</h1>
          <p className="mt-4 max-w-2xl text-lg text-white/80">{t.home.subtitle}</p>
          <form action={`/${lang}/offres`} className="mt-8 flex max-w-2xl gap-2 rounded-2xl bg-card p-2 shadow-xl">
            <input name="q" placeholder={t.home.searchPlaceholder}
              className="min-w-0 flex-1 rounded-xl px-4 py-3 text-ink placeholder:text-muted focus:outline-none" />
            <button className="rounded-xl bg-saffron-500 px-6 py-3 font-semibold text-[#2a1466] hover:bg-saffron-400">
              {t.home.search}
            </button>
          </form>
          <dl className="mt-10 flex flex-wrap gap-8">
            {stats.map((s) => (
              <div key={s.l}>
                <dt className="text-3xl font-bold">{s.n}</dt>
                <dd className="text-sm text-white/70">{s.l}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <h2 className="text-2xl font-bold text-ink">{t.home.how}</h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-3">
          {t.home.steps.map((s, i) => (
            <li key={s.t} className="rounded-2xl border border-line bg-card p-6 shadow-sm">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-accent-soft font-bold text-accent-ink">{i + 1}</span>
              <h3 className="mt-4 font-semibold">{s.t}</h3>
              <p className="mt-1 text-sm text-muted">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16">
        <div className="flex items-end justify-between">
          <h2 className="text-2xl font-bold text-ink">{t.home.latest}</h2>
          <Link href={`/${lang}/offres`} className="text-sm font-semibold text-accent-ink hover:underline">{t.home.seeAll} →</Link>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {latest.items.map((o) => <OfferCard key={o.id} o={o} lang={lang} t={t} />)}
        </div>
      </section>
    </>
  );
}
