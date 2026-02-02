import Link from "next/link";

import { LangSwitcher } from "@/components/LangSwitcher";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Dict, Locale } from "@/i18n/dictionaries";

export function Header({ lang, t }: { lang: Locale; t: Dict }) {
  const links = [
    { href: `/${lang}/offres`, label: t.nav.offers },
    { href: `/${lang}/espace`, label: t.nav.space },
    { href: `/${lang}/conseiller`, label: t.nav.counselor },
    { href: `/${lang}/observatoire`, label: t.nav.observatory },
  ];
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-card/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
        <Link href={`/${lang}`} className="flex items-center gap-2 font-bold text-accent-ink">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-lg text-white">خ</span>
          <span className="text-lg tracking-tight">{t.brand}</span>
        </Link>
        <nav className="hidden flex-1 items-center gap-1 md:flex">
          {links.map((l) => (
            <Link key={l.href} href={l.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-muted hover:bg-accent-soft hover:text-accent-ink">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="ms-auto flex items-center gap-2 md:ms-0">
          <ThemeToggle label={lang === "ar" ? "الوضع الداكن" : lang === "en" ? "Dark mode" : "Mode sombre"} />
          <LangSwitcher lang={lang} />
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-line px-2 py-1.5 md:hidden">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-muted hover:bg-accent-soft">
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
