import Link from "next/link";
import { notFound } from "next/navigation";

import { OfferCard } from "@/components/OfferCard";
import { ReviewCard, Stars } from "@/components/ReviewCard";
import { ReviewsMarquee } from "@/components/ReviewsMarquee";
import { datedReviews, reviewStats } from "@/data/reviews";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { searchOffers } from "@/lib/api";

export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const latest = await searchOffers({ size: "6", lang });
  const stats = [{ n: latest.total.toLocaleString(lang === "ar" ? "ar-MA" : "fr-FR"), l: t.home.stats.offers }];
  // Avis : deux bandeaux qui défilent en sens opposés, les plus récents en tête
  const loc = lang === "ar" ? "ar-MA" : lang === "en" ? "en-GB" : "fr-FR";
  const rs = reviewStats();
  const byDate = datedReviews();
  const card = ({ r, date }: (typeof byDate)[number]) => ({
    key: r.id, node: <ReviewCard r={r} date={date} profileLabel={t.reviews.profiles[r.profile]} starsLabel={t.reviews.stars(r.rating)}
      dateLabel={date.toLocaleDateString(loc, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })} />,
  });
  const avg = rs.avg.toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

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

      <section className="pb-14" aria-labelledby="avis-titre">
        <div className="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-3 px-4">
          <div>
            <h2 id="avis-titre" className="text-2xl font-bold text-ink">{t.reviews.homeTitle}</h2>
            <p className="mt-1 text-sm text-muted">{t.reviews.homeSub}</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="flex items-center gap-2 whitespace-nowrap">
              <Stars n={5} label={t.reviews.stars(5)} />
              <span className="text-sm font-semibold text-ink">{avg} / 5 · {rs.n.toLocaleString(loc)} {t.reviews.countShort}</span>
            </span>
            <Link href={`/${lang}/avis`} className="whitespace-nowrap text-sm font-semibold text-accent-ink hover:underline">
              {t.reviews.seeAll} {lang === "ar" ? "←" : "→"}
            </Link>
          </div>
        </div>
        <div className="mt-6 space-y-4">
          <ReviewsMarquee items={byDate.filter((_, i) => i % 2 === 0).map(card)} seconds={210} />
          <ReviewsMarquee items={byDate.filter((_, i) => i % 2 === 1).map(card)} seconds={240} reverse />
        </div>
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
