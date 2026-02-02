import Link from "next/link";

export function Restricted({ lang, text, demo, loginLabel, loggedIn }:
  { lang: string; text: string; demo: string; loginLabel: string; loggedIn: boolean }) {
  return (
    <div className="mx-auto max-w-lg px-4 py-20 text-center">
      <p className="text-lg font-semibold text-ink">{text}</p>
      <p className="mt-3 rounded-lg bg-accent-soft px-3 py-2 text-xs text-accent-ink">{demo}</p>
      {!loggedIn && <Link href={`/${lang}/connexion`} className="mt-5 inline-block rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white">{loginLabel}</Link>}
    </div>
  );
}
