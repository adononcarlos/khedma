"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { generateDocuments, markApplied, type GeneratedDocs } from "@/app/actions";

type L = {
  generate: string; generateHint: string; apply: string; login: string; noCv: string; loading: string;
  done: string; cached: string; downloadCv: string; downloadLetter: string; copyLetter: string; copied: string;
  steps: string; applied: string; appliedDone: string;
};

export function GeneratePanel({ offerId, offerUrl, lang, loggedIn, t }:
  { offerId: number; offerUrl: string; lang: string; loggedIn: boolean; t: L }) {
  const [docs, setDocs] = useState<GeneratedDocs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [applied, setApplied] = useState(false);
  const [pending, start] = useTransition();

  const run = () => start(async () => {
    setError(null);
    const r = await generateDocuments(offerId);
    if (r.error) setError(r.error); else setDocs(r.data!);
  });

  return (
    <div className="rounded-2xl border border-brand-200 bg-accent-soft p-5">
      {!docs ? (
        <>
          <button onClick={run} disabled={pending || !loggedIn}
            className="w-full rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
            {pending ? t.loading : `✨ ${t.generate}`}
          </button>
          <p className="mt-2 text-xs text-muted">{t.generateHint}</p>
          {!loggedIn && <Link href={`/${lang}/connexion`} className="mt-2 block text-sm font-semibold text-accent-ink hover:underline">{t.login} →</Link>}
          {error === "no_cv" && <Link href={`/${lang}/espace`} className="mt-2 block text-sm font-semibold text-red-700 dark:text-red-300 hover:underline">{t.noCv} →</Link>}
          {error && error !== "no_cv" && error !== "auth" && <p className="mt-2 text-sm text-red-700 dark:text-red-300">{error}</p>}
        </>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">✓ {t.done} · {docs.language.toUpperCase()}
            {docs.cached && <span className="ms-1 font-normal text-muted">({t.cached})</span>}</p>
          <a href={`/api/documents/${docs.cv.id}`} className="block rounded-xl bg-brand-600 px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-brand-700">⬇ {t.downloadCv}</a>
          <a href={`/api/documents/${docs.letter.id}`} className="block rounded-xl bg-brand-600 px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-brand-700">⬇ {t.downloadLetter}</a>
          <button onClick={() => { navigator.clipboard.writeText(docs.letter_text); setCopied(true); }}
            className="block w-full rounded-xl border border-brand-300 bg-card px-4 py-2.5 text-sm font-semibold text-accent-ink hover:bg-accent-soft">
            {copied ? t.copied : t.copyLetter}
          </button>
          <p className="pt-1 text-xs text-muted">{t.steps}</p>
        </div>
      )}
      <a href={offerUrl} target="_blank" rel="noopener noreferrer"
        className="mt-3 block w-full rounded-xl border border-brand-600 bg-card px-4 py-3 text-center font-semibold text-accent-ink hover:bg-accent-soft">
        {t.apply} ↗
      </a>
      {docs && (
        <button onClick={() => start(async () => { await markApplied(offerId); setApplied(true); })} disabled={applied}
          className="mt-2 w-full rounded-xl px-4 py-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50 dark:bg-emerald-950/50 disabled:opacity-70">
          {applied ? `✓ ${t.appliedDone}` : t.applied}
        </button>
      )}
    </div>
  );
}
