import type { Metadata } from "next";
import { Inter, Noto_Sans_Arabic } from "next/font/google";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";

import { Header } from "@/components/Header";
import { dirOf, getDictionary, hasLocale, locales } from "@/i18n/dictionaries";
import "../globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const arabic = Noto_Sans_Arabic({ variable: "--font-arabic", subsets: ["arabic"] });

export const metadata: Metadata = {
  title: "Khedma | Toutes les offres d'emploi du Maroc",
  description: "Agrégation des offres d'emploi marocaines et matching IA des profils.",
};

export function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  // Thème choisi par l'utilisateur (cookie) ; sans choix, le CSS suit la préférence du système
  const theme = (await cookies()).get("theme")?.value;
  const themeClass = theme === "dark" ? "dark" : theme === "light" ? "light" : "";
  return (
    <html lang={lang} dir={dirOf(lang)} suppressHydrationWarning
      className={`${inter.variable} ${arabic.variable} h-full antialiased ${themeClass}`}>
      <body className="min-h-full flex flex-col">
        <Header lang={lang} t={t} />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
