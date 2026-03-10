"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import type { Facets } from "@/lib/api";

export type FilterLabels = {
  all: string; reset: string; region: string; contract: string; source: string; searchPlaceholder: string;
  contracts: Record<string, string>; regions: Record<string, string>;
  function: string; sector: string; experience: string; since: string; sinceOptions: Record<string, string>;
  functions: Record<string, string>; sectors: Record<string, string>; experiences: Record<string, string>;
};

export function Filters({ facets, t }: { facets: Facets; t: FilterLabels }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    next.delete("page");
    router.push(`${pathname}?${next}`);
  };

  // Les options arrivent déjà triées depuis le serveur (même ordre au rendu serveur et client)
  const select = (key: string, label: string, options: { value: string; label: string; count: number }[]) => (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">{label}</span>
      <select value={params.get(key) ?? ""} onChange={(e) => set(key, e.target.value)}
        className="w-full rounded-xl border border-line bg-card px-3 py-2 text-sm focus:border-brand-500 focus:outline-none">
        <option value="">{t.all}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label} ({o.count})</option>)}
      </select>
    </label>
  );

  return (
    <div className="space-y-4">
      <form onSubmit={(e) => { e.preventDefault(); set("q", String(new FormData(e.currentTarget).get("q") ?? "")); }}>
        <input name="q" defaultValue={params.get("q") ?? ""} placeholder={t.searchPlaceholder}
          className="w-full rounded-xl border border-line bg-card px-3 py-2 text-sm focus:border-brand-500 focus:outline-none" />
      </form>
      {select("function", t.function, facets.functions.map((f) => ({ value: f.value, label: t.functions[f.value] ?? f.value, count: f.count })))}
      {select("sector_group", t.sector, facets.sector_groups.map((f) => ({ value: f.value, label: t.sectors[f.value] ?? f.value, count: f.count })))}
      {select("experience", t.experience, ["entry", "1-2", "3-5", "5-10", "10+"].map((v) => ({ value: v, label: t.experiences[v], count: facets.experiences.find((f) => f.value === v)?.count ?? 0 })).filter((o) => o.count > 0))}
      <label className="block">
        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">{t.since}</span>
        <select value={params.get("since") ?? ""} onChange={(e) => set("since", e.target.value)}
          className="w-full rounded-xl border border-line bg-card px-3 py-2 text-sm focus:border-brand-500 focus:outline-none">
          <option value="">{t.all}</option>
          {Object.entries(t.sinceOptions).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>
      {select("region", t.region, facets.regions.map((f) => ({ value: f.value, label: t.regions[f.value] ?? f.value, count: f.count })))}
      {select("contract", t.contract, facets.contracts.map((f) => ({ value: f.value, label: t.contracts[f.value] ?? f.value, count: f.count })))}
      {select("source", t.source, facets.sources.map((f) => ({ value: f.value, label: f.name ?? f.value, count: f.count })))}
      {params.toString() && (
        <button onClick={() => router.push(pathname)} className="text-sm font-medium text-accent-ink hover:underline">
          {t.reset}
        </button>
      )}
    </div>
  );
}
