import { notFound } from "next/navigation";

import { CaseloadRow } from "@/components/CaseloadRow";
import { StatTile } from "@/components/Charts";
import { Restricted } from "@/components/Restricted";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { authFetch, getMe } from "@/lib/session";

type Caseload = {
  counselor: { name: string; region: string | null }; totals: Record<string, number>;
  items: { id: number; name: string; city: string | null; status: string; headline: string | null; has_cv: boolean;
    applications: number; idle_days: number; anapec_registered: boolean; reasons: string[] | null }[];
};

export default async function CounselorPage({ params }: PageProps<"/[lang]/conseiller">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const s = t.staff;
  const me = await getMe();
  if (!me || !["admin", "counselor"].includes(me.user.role))
    return <Restricted lang={lang} text={s.restricted} demo={s.demoAccounts} loginLabel={t.auth.login} loggedIn={Boolean(me)} />;
  const d: Caseload = await authFetch("/api/counselor/caseload").then((r) => r.json());
  const loc = lang === "ar" ? "ar-MA" : lang === "en" ? "en-GB" : "fr-FR";
  const region = d.counselor.region ? (t.regions[d.counselor.region] ?? d.counselor.region) : "Maroc";

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-bold text-ink">{s.caseTitle}</h1>
      <p className="mt-1 text-sm text-muted">{d.counselor.name} · {s.caseSub(region)}</p>
      <div className="mt-6 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {["active", "to_remind", "dormant", "ghost", "duplicate"].map((k) => (
          <StatTile key={k} label={s.status[k]} value={(d.totals[k] ?? 0).toLocaleString(loc)} />
        ))}
      </div>
      <ul className="mt-6 space-y-3">
        {d.items.map((it) => (
          <CaseloadRow key={it.id} item={it} lang={lang} t={{
            status: s.status, idle: s.idle(it.idle_days), apps: s.apps(it.applications), noCv: s.noCv,
            suggest: s.suggest, suggestions: s.suggestions, none: s.none, registeredAnapec: s.registeredAnapec,
          }} />
        ))}
      </ul>
    </div>
  );
}
