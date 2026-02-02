import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { logout } from "@/app/actions";
import { CvUpload } from "@/components/CvUpload";
import { OfferCard as Card, Tag } from "@/components/OfferCard";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import type { OfferCard } from "@/lib/api";
import { authFetch, getMe } from "@/lib/session";

type MatchItem = { offer: OfferCard; score: number; matched: string[]; missing: string[] };
type Gap = { skill: string; label: string; share: number; provider: string; url: string };

const STATUS_TONE: Record<string, string> = {
  eligible: "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 ring-emerald-200",
  possible: "bg-accent-soft text-accent-ink ring-brand-200",
  action: "bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 ring-amber-200",
};

export default async function SpacePage({ params, searchParams }: PageProps<"/[lang]/espace">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const me = await getMe();
  if (!me) redirect(`/${lang}/connexion`);
  const t = getDictionary(lang);
  const s = t.space;
  const justUploaded = (await searchParams).cv === "ok";
  const p = me.profile;
  const matches: { items: MatchItem[]; skill_gaps: Gap[] } | null =
    p ? await authFetch("/api/me/matches?limit=12").then((r) => (r.ok ? r.json() : null)) : null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{s.hello(me.user.full_name.split(" ")[0])}</h1>
        <form action={logout}><input type="hidden" name="lang" value={lang} />
          <button className="text-sm font-medium text-muted hover:text-ink">{t.auth.logout}</button></form>
      </div>
      {justUploaded && <p className="mt-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">✓ {s.uploaded}</p>}

      <div className="mt-6 grid gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="min-w-0 space-y-6">
          <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            <h2 className="font-bold">{p ? s.profile : s.uploadTitle}</h2>
            {p && (
              <div className="mt-3 space-y-3 text-sm">
                <p className="font-medium text-ink" dir="auto">{p.headline}</p>
                {p.years_experience ? <p className="text-muted">{s.years(p.years_experience)}</p> : null}
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted">{s.skills}</p>
                  <div className="flex flex-wrap gap-1.5">{p.skills.map((k) => <Tag key={k.id} tone="brand">{k.label}</Tag>)}</div>
                </div>
                <p className="text-xs text-muted">📄 {p.cv_filename}</p>
              </div>
            )}
            <div className="mt-4 border-t border-line pt-4">
              <CvUpload lang={lang} label={p ? s.replace : s.upload} hint={s.uploadHint} />
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            <h2 className="font-bold">{s.eligibility}</h2>
            <ul className="mt-3 space-y-2">
              {me.eligibility.map((e) => (
                <li key={e.program} className="text-sm">
                  <span className={`me-2 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${STATUS_TONE[e.status] ?? ""}`}>{e.program}</span>
                  <span className="text-ink-soft">{e.text}</span>
                </li>
              ))}
            </ul>
          </section>

          {matches && matches.skill_gaps.length > 0 && (
            <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
              <h2 className="font-bold">{s.gaps}</h2>
              <ul className="mt-3 space-y-3">
                {matches.skill_gaps.map((g) => (
                  <li key={g.skill} className="text-sm">
                    <p className="text-ink">{s.gapLine(g.label, g.share)}</p>
                    <a href={g.url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-accent-ink hover:underline">
                      {s.train} : {g.provider} ↗</a>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>

        <section className="min-w-0">
          <h2 className="text-lg font-bold">{s.matches}</h2>
          {!matches || matches.items.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-line bg-card p-10 text-center text-muted">{s.noMatches}</p>
          ) : (
            <div className="mt-4 space-y-3">
              {matches.items.map((m) => (
                <div key={m.offer.id} className="grid grid-cols-[64px_1fr] items-start gap-3">
                  <div className="grid h-16 place-items-center rounded-2xl bg-brand-600 text-white shadow-sm">
                    <span className="text-xl font-bold">{m.score}</span>
                  </div>
                  <div className="min-w-0 space-y-1.5">
                    <Card o={m.offer} lang={lang} t={t} />
                    <p className="px-1 text-xs text-muted">
                      {m.matched.length > 0 && <><b className="text-emerald-700 dark:text-emerald-300">{s.why} :</b> {m.matched.join(", ")}</>}
                      {m.missing.length > 0 && <> · <b className="text-amber-700 dark:text-amber-300">{s.missing} :</b> {m.missing.join(", ")}</>}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
          <Link href={`/${lang}/offres`} className="mt-6 inline-block text-sm font-semibold text-accent-ink hover:underline">{t.home.seeAll} →</Link>
        </section>
      </div>
    </div>
  );
}
