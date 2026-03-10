import type { Metadata } from "next";
import { Inter, Noto_Sans_Arabic } from "next/font/google";
import { notFound } from "next/navigation";
import Script from "next/script";

import { Header } from "@/components/Header";
import { dirOf, getDictionary, hasLocale, locales } from "@/i18n/dictionaries";
import "../globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const arabic = Noto_Sans_Arabic({ variable: "--font-arabic", subsets: ["arabic"] });

export const metadata: Metadata = {
  title: "Khedma | Toutes les offres d'emploi du Maroc",
  description: "Agrégation des offres d'emploi marocaines et matching IA des profils.",
};

const THEME_SCRIPT = `try{var t=localStorage.getItem("theme");if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))document.documentElement.classList.add("dark")}catch(e){}`;

export function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  return (
    <html lang={lang} dir={dirOf(lang)} suppressHydrationWarning
      className={`${inter.variable} ${arabic.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        {/* Applique le thème avant l'affichage (évite le flash clair en mode sombre) */}
        <Script id="theme" strategy="beforeInteractive">{THEME_SCRIPT}</Script>
        <Header lang={lang} t={t} />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
