import { notFound, redirect } from "next/navigation";

import { AuthForms } from "@/components/AuthForms";
import { getDictionary, hasLocale } from "@/i18n/dictionaries";
import { getMe } from "@/lib/session";

export default async function LoginPage({ params }: PageProps<"/[lang]/connexion">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  if (await getMe()) redirect(`/${lang}/espace`);
  return <div className="px-4 py-14"><AuthForms lang={lang} t={getDictionary(lang).auth} /></div>;
}
