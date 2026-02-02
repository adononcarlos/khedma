"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { locales, type Locale } from "@/i18n/dictionaries";

const labels: Record<Locale, string> = { fr: "FR", ar: "ع", en: "EN" };

export function LangSwitcher({ lang }: { lang: Locale }) {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  return (
    <div className="flex rounded-lg border border-line bg-card p-0.5 text-sm">
      {locales.map((l) => (
        <Link key={l} href={`${pathname.replace(/^\/(fr|ar|en)/, `/${l}`)}${search ? `?${search}` : ""}`}
          className={`rounded-md px-2.5 py-1 font-medium ${l === lang ? "bg-brand-600 text-white" : "text-muted hover:bg-accent-soft"}`}>
          {labels[l]}
        </Link>
      ))}
    </div>
  );
}
