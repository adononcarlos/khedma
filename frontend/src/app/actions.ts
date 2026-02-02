"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { API_URL, authFetch, getToken, TOKEN_COOKIE } from "@/lib/session";

export type FormState = { error?: string } | undefined;

async function setSession(token: string) {
  (await cookies()).set(TOKEN_COOKIE, token, {
    httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 60 * 60 * 24 * 7,
  });
}

async function detail(r: Response) {
  const body = await r.json().catch(() => ({}));
  const d = body.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? d.map((x: { msg: string }) => x.msg).join(", ") : "Erreur";
}

export async function login(_: FormState, form: FormData): Promise<FormState> {
  const r = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
  });
  if (!r.ok) return { error: await detail(r) };
  await setSession((await r.json()).token);
  redirect(`/${form.get("lang") ?? "fr"}/espace`);
}

export async function register(_: FormState, form: FormData): Promise<FormState> {
  const r = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({
      email: form.get("email"), password: form.get("password"), full_name: form.get("full_name"),
      phone: form.get("phone") || null, city: form.get("city") || null,
      preferred_language: form.get("lang") ?? "fr", anapec_registered: form.get("anapec") === "on",
    }),
  });
  if (!r.ok) return { error: await detail(r) };
  await setSession((await r.json()).token);
  redirect(`/${form.get("lang") ?? "fr"}/espace`);
}

export async function logout(form: FormData) {
  (await cookies()).delete(TOKEN_COOKIE);
  redirect(`/${form.get("lang") ?? "fr"}`);
}

export async function uploadCv(_: FormState, form: FormData): Promise<FormState> {
  if (!(await getToken())) return { error: "Session expirée" };
  const file = form.get("cv");
  if (!(file instanceof File) || file.size === 0) return { error: "Choisissez un fichier" };
  const body = new FormData();
  body.append("file", file, file.name);
  const r = await authFetch("/api/me/cv", { method: "POST", body });
  if (!r.ok) return { error: await detail(r) };
  redirect(`/${form.get("lang") ?? "fr"}/espace?cv=ok`);
}

export type GeneratedDocs = {
  cv: { id: number }; letter: { id: number }; language: string; cached: boolean; offer_url: string; letter_text: string;
};

export async function generateDocuments(offerId: number): Promise<{ data?: GeneratedDocs; error?: string }> {
  if (!(await getToken())) return { error: "auth" };
  const r = await authFetch(`/api/me/offers/${offerId}/documents`, { method: "POST" });
  if (r.status === 409) return { error: "no_cv" };
  if (!r.ok) return { error: await detail(r) };
  return { data: await r.json() };
}

export async function markApplied(offerId: number) {
  await authFetch(`/api/me/offers/${offerId}/applied`, { method: "POST" });
}

export async function counselorSuggestions(userId: number) {
  const r = await authFetch(`/api/counselor/seekers/${userId}/suggestions`);
  return r.ok ? (await r.json()).items : [];
}
