import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";

import { ReviewCard, Stars } from "@/components/ReviewCard";
import { REVIEWS, datedReviews, reviewStats, type ReviewLang, type ReviewProfile } from "@/data/reviews";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";

const PROFILES: ReviewProfile[] = ["seeker", "student", "pro"];
const LANGS: ReviewLang[] = ["fr", "ar", "en"];

export default async function ReviewsPage({ params, searchParams }: PageProps<"/[lang]/avis">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  await connection(); // dates calculées à la requête
  const t = getDictionary(lang);
  const r = t.reviews;
  const sp = await searchParams;
  const one = (k: string) => (typeof sp[k] === "string" ? (sp[k] as string) : undefined);
  const profile = PROFILES.find((p) => p === one("profil"));
  const language = LANGS.find((l) => l === one("langue"));

  const loc = lang === "ar" ? "ar-MA" : lang === "en" ? "en-GB" : "fr-FR";
  const list = datedReviews(REVIEWS.filter((x) => (!profile || x.profile === profile) && (!language || x.lang === language)));
  const st = reviewStats(list.map((e) => e.r));
  const num = (n: number, digits = 0) => n.toLocaleString(loc, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const href = (p?: string, l?: string) => {
    const qs = new URLSearchParams(Object.entries({ profil: p, langue: l }).filter(([, v]) => v) as [string, string][]);
    return `/${lang}/avis${qs.size ? `?${qs}` : ""}`;
  };
  const chip = (active: boolean) => `rounded-full px-3 py-1.5 text-sm font-medium ${active
    ? "bg-brand-600 text-white" : "border border-line bg-card text-ink-soft hover:bg-accent-soft hover:text-accent-ink"}`;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold text-ink">{r.title}</h1>
      <p className="mt-1 text-sm text-muted">{r.sub}</p>

      <div className="mt-6 grid grid-cols-3 gap-3 sm:gap-4 lg:grid-cols-[1fr_1fr_1fr_1.3fr]">
        <div className="rounded-2xl border border-line bg-card p-3 shadow-sm sm:p-5">
          <p className="text-xs text-muted sm:text-sm">{r.average}</p>
          <p className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">{num(st.avg, 1)} <span className="text-base text-muted sm:text-lg">/ 5</span></p>
          <div className="mt-2"><Stars n={Math.round(st.avg)} label={r.stars(Math.round(st.avg))} size="h-3 w-3 sm:h-4 sm:w-4" /></div>
        </div>
        <div className="rounded-2xl border border-line bg-card p-3 shadow-sm sm:p-5">
          <p className="text-xs text-muted sm:text-sm">{r.count}</p>
          <p className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">{num(st.n)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card p-3 shadow-sm sm:p-5">
          <p className="text-xs text-muted sm:text-sm">5 ★</p>
          <p className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">{num(100 * st.fiveStars)} %</p>
          <p className="mt-1 text-xs text-muted">{r.fiveStars}</p>
        </div>
        <div className="col-span-3 rounded-2xl border border-line bg-card p-5 shadow-sm lg:col-span-1">
          <p className="text-sm text-muted">{r.breakdown}</p>
          <ul className="mt-2 space-y-1.5">
            {st.byStars.map((b) => (
              <li key={b.stars} className="flex items-center gap-2 text-xs text-muted">
                <span className="w-7 shrink-0">{b.stars} ★</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-grid">
                  <span className="block h-full rounded-full bg-saffron-500" style={{ width: `${st.n ? (100 * b.count) / st.n : 0}%` }} />
                </span>
                <span className="w-6 shrink-0 text-end">{num(b.count)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-8 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="me-1 text-xs font-semibold uppercase tracking-wide text-muted">{r.profile}</span>
          <Link href={href(undefined, language)} className={chip(!profile)}>{r.profiles.all}</Link>
          {PROFILES.map((p) => <Link key={p} href={href(p, language)} className={chip(profile === p)}>{r.profiles[p]}</Link>)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="me-1 text-xs font-semibold uppercase tracking-wide text-muted">{r.language}</span>
          <Link href={href(profile, undefined)} className={chip(!language)}>{r.allLanguages}</Link>
          {LANGS.map((l) => <Link key={l} href={href(profile, l)} className={chip(language === l)}>{t.langNames[l]}</Link>)}
        </div>
      </div>

      {list.length === 0 ? (
        <p className="mt-10 rounded-2xl border border-dashed border-line bg-card p-10 text-center text-muted">{r.empty}</p>
      ) : (
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {list.map(({ r: x, date }) => (
            <ReviewCard key={x.id} r={x} date={date} profileLabel={r.profiles[x.profile]} starsLabel={r.stars(x.rating)}
              dateLabel={date.toLocaleDateString(loc, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })} />
          ))}
        </div>
      )}
    </div>
  );
}
