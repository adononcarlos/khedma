import "server-only";

import { cookies } from "next/headers";

export const API_URL = process.env.API_URL ?? "http://127.0.0.1:8010";
export const TOKEN_COOKIE = "khedma_token";

export async function getToken() {
  return (await cookies()).get(TOKEN_COOKIE)?.value;
}

/** Appel authentifié à l'API (Server Components, Server Actions, Route Handlers). */
export async function authFetch(path: string, init: RequestInit = {}) {
  const token = await getToken();
  return fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { ...(init.headers ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
}

export type Me = {
  user: { id: number; email: string; full_name: string; role: string; city: string | null; region: string | null;
    phone: string | null; preferred_language: "fr" | "ar" | "en"; anapec_registered: boolean; status: string };
  profile: null | {
    version: number; headline: string | null; summary: string | null; skills: { id: string; label: string }[];
    extra_skills: string[] | null; experiences: { title: string; company: string | null; start: string | null; end: string | null; bullets: string[] }[] | null;
    education: { degree: string; school: string | null; year: string | null }[] | null;
    languages: { name: string; level: string | null }[] | null; education_level: string | null;
    years_experience: number | null; cv_filename: string | null; cv_language: string | null;
  };
  eligibility: { program: string; status: string; text: string }[];
};

export async function getMe(): Promise<Me | null> {
  if (!(await getToken())) return null;
  const r = await authFetch("/api/me");
  return r.ok ? r.json() : null;
}
