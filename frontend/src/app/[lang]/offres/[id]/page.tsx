import Link from "next/link";
import { notFound } from "next/navigation";

import { GeneratePanel } from "@/components/GeneratePanel";
import { Markdown } from "@/components/Markdown";
import { formatDate, Tag } from "@/components/OfferCard";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { getOffer } from "@/lib/api";
import { authFetch, getToken } from "@/lib/session";

export default async function OfferPage({ params }: PageProps<"/[lang]/offres/[id]">) {
  const { lang, id } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const o = await getOffer(id, lang).catch(() => null);
  if (!o) notFound();
  const loggedIn = Boolean(await getToken());
  const match: { score: number; matched: string[]; missing: string[] } | null = loggedIn
    ? await authFetch(`/api/me/offers/${o.id}/match`).then((r) => (r.ok ? r.json() : null)) : null;

  // Infos clés affichées directement sous le titre (seulement celles qui existent)
  const facts = [
    [t.facets.function, o.job_function && o.job_function !== "other" ? t.functions[o.job_function] : null],
    [t.facets.sector, o.sector_group && o.sector_group !== "other" ? t.sectors[o.sector_group] : o.sector],
    [t.facets.experience, o.experience_level ? t.experiences[o.experience_level] : o.experience?.replace(/[()]/g, "")],
    [t.offer.education, o.education],
    [t.offer.languages, o.languages && Object.keys(o.languages).length
      ? Object.entries(o.languages).map(([k, v]) => `${k} (${v})`).join(", ") : null],
    [t.offer.salary, o.salary],
    [t.offer.start, formatDate(o.start_date, lang)],
  ].filter(([, v]) => v) as [string, string][];

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <Link href={`/${lang}/offres`} className="text-sm font-medium text-accent-ink hover:underline">← {t.offer.back}</Link>
      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_340px]">
        <article className="min-w-0 rounded-2xl border border-line bg-card p-6 shadow-sm md:p-8">
          <h1 className="text-2xl font-bold text-ink md:text-3xl" dir="auto">{o.title}</h1>
          <p className="mt-1 text-muted" dir="auto">
            {[o.company, o.city, o.region && (t.regions[o.region] ?? o.region)].filter(Boolean).join(" · ")}
          </p>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {o.contract_type && <Tag tone="brand">{t.contracts[o.contract_type] ?? o.contract_type}</Tag>}
            {o.positions && <Tag tone="green">{t.offers.positions(o.positions)}</Tag>}
            {o.posted_at && <Tag>{t.offers.postedOn} {formatDate(o.posted_at, lang)}</Tag>}
            <Tag>{t.offers.via} {o.source_name}</Tag>
          </div>
          {facts.length > 0 && (
            <dl className="mt-6 grid gap-x-6 gap-y-3 rounded-xl bg-chip p-4 sm:grid-cols-2">
              {facts.map(([k, v]) => (
                <div key={k} className="min-w-0">
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted">{k}</dt>
                  <dd className="mt-0.5 text-sm text-ink" dir="auto">{v}</dd>
                </div>
              ))}
            </dl>
          )}
          {o.description && (
            <section className="mt-8">
              <h2 className="text-sm font-bold uppercase tracking-wide text-muted">{t.offer.description}</h2>
              {o.translated && <p className="mt-2 text-xs italic text-muted">{t.facets.translated}</p>}
              <div className="mt-3"><Markdown text={o.description} lang={o.translated ? lang : o.language} /></div>
            </section>
          )}
        </article>
        <aside className="min-w-0 space-y-4 lg:sticky lg:top-24 lg:self-start">
          {match && (
            <div className="rounded-2xl border border-line bg-card p-5 shadow-sm">
              <div className="flex items-center gap-3">
                <span className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-600 text-xl font-bold text-white">{match.score}</span>
                <span className="text-sm font-semibold text-ink-soft">{t.gen.score}</span>
              </div>
              {match.matched.length > 0 && <p className="mt-3 text-xs text-muted"><b className="text-emerald-700 dark:text-emerald-300">{t.space.why} :</b> {match.matched.join(", ")}</p>}
              {match.missing.length > 0 && <p className="mt-1 text-xs text-muted"><b className="text-amber-700 dark:text-amber-300">{t.space.missing} :</b> {match.missing.join(", ")}</p>}
            </div>
          )}
          <GeneratePanel offerId={o.id} offerUrl={o.url} lang={lang} loggedIn={loggedIn}
            t={{ generate: t.offer.generate, generateHint: t.offer.generateHint, apply: t.offer.apply, login: t.gen.login,
              noCv: t.gen.noCv, loading: t.gen.loading, done: t.gen.done(t.langNames[o.language]), cached: t.gen.cached,
              downloadCv: t.gen.downloadCv, downloadLetter: t.gen.downloadLetter, copyLetter: t.gen.copyLetter,
              copied: t.gen.copied, steps: t.gen.steps, applied: t.gen.applied, appliedDone: t.gen.appliedDone }} />
          {o.eligibility.length > 0 && (
            <div className="space-y-2 rounded-2xl border border-line bg-card p-5 text-sm shadow-sm">
              {o.eligibility.map((e) => (
                <p key={e.program}><span className="me-2 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-bold text-accent-ink">{e.program}</span>
                  <span className="text-ink-soft">{e.text}</span></p>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
