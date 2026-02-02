"use client";

import { useActionState } from "react";

import { uploadCv } from "@/app/actions";

export function CvUpload({ lang, label, hint }: { lang: string; label: string; hint: string }) {
  const [state, action, pending] = useActionState(uploadCv, undefined);
  return (
    <form action={action} className="space-y-3">
      <input type="hidden" name="lang" value={lang} />
      <input type="file" name="cv" accept=".pdf,.docx,.txt" required
        className="block w-full text-sm file:me-3 file:rounded-lg file:border-0 file:bg-accent-soft file:px-4 file:py-2 file:font-semibold file:text-accent-ink hover:file:bg-brand-200" />
      <p className="text-xs text-muted">{hint}</p>
      {state?.error && <p className="rounded-lg bg-red-50 dark:bg-red-950/50 px-3 py-2 text-sm text-red-700 dark:text-red-300">{state.error}</p>}
      <button disabled={pending} className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
        {pending ? "…" : label}
      </button>
    </form>
  );
}
