import { notFound } from "next/navigation";

import { BarList, Columns, StatTile } from "@/components/Charts";
import { Restricted } from "@/components/Restricted";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { authFetch, getMe } from "@/lib/session";

type F = { value: string; count: number };
type Obs = {
  hcp: { period: string; unemployment: number; youth_15_24: number; urban: number; rural: number; source: string };
  offers: { total: number; by_source: F[]; by_function: F[]; by_region: F[]; by_sector: F[];
    top_skills: { label: string; count: number }[]; daily: { date: string; count: number }[] };
  users: { registered: number; status: Record<string, number>; verified_active: number; employed: number;
    ghost_reasons: Record<string, number>; timeline: { month: string; signups: number; cumulative: number; hires: number }[] };
  tension: { function: string; offers: number; seekers: number; ratio: number }[];
};

const SOURCE_NAMES: Record<string, string> = { anapec: "ANAPEC", indeed: "Indeed", rekrute: "ReKrute", dreamjob: "Dreamjob", marocemploi: "MarocEmploi" };

export default async function ObservatoryPage({ params }: PageProps<"/[lang]/observatoire">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const s = t.staff;
  const me = await getMe();
  if (!me || !["admin", "counselor"].includes(me.user.role))
    return <Restricted lang={lang} text={s.restricted} demo={s.demoAccounts} loginLabel={t.auth.login} loggedIn={Boolean(me)} />;
  const d: Obs = await authFetch("/api/admin/observatory").then((r) => r.json());
  const loc = lang === "ar" ? "ar-MA" : lang === "en" ? "en-GB" : "fr-FR";
  const monthLabel = (m: string) => new Date(`${m}-01`).toLocaleDateString(loc, { month: "short", year: "2-digit" });
  const ghosts = (d.users.status.ghost ?? 0) + (d.users.status.duplicate ?? 0);
  const pct = (n: number) => `${((100 * n) / Math.max(1, d.users.registered)).toFixed(1).replace(".", lang === "en" ? "." : ",")} %`;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold text-ink">{s.obsTitle}</h1>
      <p className="mt-1 text-sm text-muted">{s.obsSub}</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label={s.offers} value={d.offers.total.toLocaleString(loc)} />
        <StatTile label={s.registered} value={d.users.registered.toLocaleString(loc)} sub={`${s.verifiedActive} : ${d.users.verified_active.toLocaleString(loc)}`} />
        <StatTile label={s.ghosts} value={ghosts.toLocaleString(loc)} sub={pct(ghosts)} />
        <StatTile label={s.employed} value={d.users.employed.toLocaleString(loc)} sub={pct(d.users.employed)} />
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <a href={d.hcp.source} target="_blank" rel="noopener noreferrer" className="block"><StatTile label={s.unemployment(d.hcp.period)} value={`${d.hcp.unemployment} %`} sub={`${d.hcp.urban} % urbain · ${d.hcp.rural} % rural ↗`} /></a>
        <StatTile label={s.youth} value={`${d.hcp.youth_15_24} %`} sub={`HCP, ${d.hcp.period}`} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <BarList title={s.byFunction} locale={loc} head={[t.facets.function, s.count]}
          rows={d.offers.by_function.filter((f) => f.value !== "other").slice(0, 12).map((f) => ({ label: t.functions[f.value] ?? f.value, value: f.count }))} />
        <BarList title={s.byRegion} locale={loc} head={[t.offers.region, s.count]}
          rows={d.offers.by_region.map((f) => ({ label: t.regions[f.value] ?? f.value, value: f.count }))} />
        <BarList title={s.topSkills} locale={loc} head={[t.space.skills, s.count]}
          rows={d.offers.top_skills.map((k) => ({ label: k.label, value: k.count }))} />
        <BarList title={s.bySector} locale={loc} head={[t.facets.sector, s.count]}
          rows={d.offers.by_sector.filter((f) => f.value !== "other").map((f) => ({ label: t.sectors[f.value] ?? f.value, value: f.count }))} />
        <Columns title={s.signups} locale={loc} head={[s.month, s.count]}
          rows={d.users.timeline.map((m) => ({ label: monthLabel(m.month), value: m.signups }))} />
        <Columns title={s.hires} locale={loc} head={[s.month, s.count]}
          rows={d.users.timeline.map((m) => ({ label: monthLabel(m.month), value: m.hires }))} />
        <Columns title={s.daily} locale={loc} head={[s.day, s.count]}
          rows={d.offers.daily.map((x) => ({ label: new Date(x.date).toLocaleDateString(loc, { day: "numeric", month: "short" }), value: x.count }))} />
        <BarList title={s.bySource} locale={loc} head={[s.source, s.count]}
          rows={d.offers.by_source.map((f) => ({ label: SOURCE_NAMES[f.value] ?? f.value, value: f.count }))} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[2fr_1fr]">
        <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
          <h3 className="font-semibold text-ink">{s.tension}</h3>
          <p className="mt-1 text-xs text-muted">{s.tensionSub}</p>
          <table className="mt-4 w-full text-sm">
            <thead><tr className="text-xs text-muted"><th className="py-1.5 text-start font-medium">{t.facets.function}</th>
              <th className="py-1.5 text-end font-medium">{s.offersCol}</th><th className="py-1.5 text-end font-medium">{s.seekersCol}</th>
              <th className="py-1.5 text-end font-medium">{s.ratioCol}</th></tr></thead>
            <tbody>
              {d.tension.filter((r) => r.seekers > 0).slice(0, 12).map((r) => (
                <tr key={r.function} className="border-t border-line">
                  <td className="py-1.5 text-ink-soft">{t.functions[r.function] ?? r.function}</td>
                  <td className="py-1.5 text-end tabular-nums text-ink">{r.offers}</td>
                  <td className="py-1.5 text-end tabular-nums text-ink">{r.seekers}</td>
                  <td className="py-1.5 text-end font-semibold tabular-nums text-ink">{r.ratio.toLocaleString(loc)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="rounded-2xl border border-line bg-card p-5 shadow-sm">
          <h3 className="font-semibold text-ink">{s.ghostTitle}</h3>
          <ul className="mt-4 space-y-2 text-sm">
            {Object.entries(d.users.ghost_reasons).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-3 border-t border-line pt-2 first:border-0 first:pt-0">
                <span className="text-ink-soft">{k}</span><span className="tabular-nums font-semibold text-ink">{v}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
