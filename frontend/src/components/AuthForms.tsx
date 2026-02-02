"use client";

import { useActionState, useState } from "react";

import { login, register } from "@/app/actions";

type L = {
  login: string; register: string; email: string; password: string; fullName: string; phone: string; city: string;
  anapec: string; submitLogin: string; submitRegister: string; haveAccount: string; noAccount: string; demo: string;
};

const input = "w-full rounded-xl border border-line bg-card px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none";

export function AuthForms({ lang, t }: { lang: string; t: L }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loginState, loginAction, loginPending] = useActionState(login, undefined);
  const [regState, regAction, regPending] = useActionState(register, undefined);
  const error = mode === "login" ? loginState?.error : regState?.error;

  return (
    <div className="mx-auto max-w-md rounded-2xl border border-line bg-card p-8 shadow-sm">
      <h1 className="text-2xl font-bold">{mode === "login" ? t.login : t.register}</h1>
      <form action={mode === "login" ? loginAction : regAction} className="mt-6 space-y-3">
        <input type="hidden" name="lang" value={lang} />
        {mode === "register" && <input name="full_name" required placeholder={t.fullName} className={input} />}
        <input name="email" type="email" required placeholder={t.email} className={input} />
        <input name="password" type="password" required minLength={8} placeholder={t.password} className={input} />
        {mode === "register" && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <input name="phone" placeholder={t.phone} className={input} />
              <input name="city" placeholder={t.city} className={input} />
            </div>
            <label className="flex items-center gap-2 text-sm text-ink-soft">
              <input type="checkbox" name="anapec" className="h-4 w-4 accent-brand-600" /> {t.anapec}
            </label>
          </>
        )}
        {error && <p className="rounded-lg bg-red-50 dark:bg-red-950/50 px-3 py-2 text-sm text-red-700 dark:text-red-300">{error}</p>}
        <button disabled={loginPending || regPending}
          className="w-full rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
          {mode === "login" ? t.submitLogin : t.submitRegister}
        </button>
      </form>
      <button onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="mt-4 text-sm font-medium text-accent-ink hover:underline">
        {mode === "login" ? `${t.noAccount} ${t.register}` : `${t.haveAccount} ${t.login}`}
      </button>
      <p className="mt-6 rounded-lg bg-accent-soft px-3 py-2 text-xs text-accent-ink">{t.demo}</p>
    </div>
  );
}
