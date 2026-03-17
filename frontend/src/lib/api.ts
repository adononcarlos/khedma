// Accès à l'API FastAPI, côté serveur (Server Components).
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8010";

export type OfferCard = {
  id: number;
  source: string;
  source_name: string;
  title: string;
  company: string | null;
  city: string | null;
  region: string | null;
  sector: string | null;
  contract_type: string | null;
  positions: number | null;
  language: "fr" | "ar" | "en";
  posted_at: string | null;
  salary: string | null;
  job_function: string | null;
  sector_group: string | null;
  experience_level: string | null;
  original_title: string | null;
};

export type OfferDetail = OfferCard & {
  url: string;
  description: string | null;
  education: string | null;
  experience: string | null;
  occupation: string | null;
  languages: Record<string, string> | null;
  start_date: string | null;
  contract_raw: string | null;
  eligibility: { program: string; code: string; tone: string; text: string }[];
  translated: boolean;
};

export type OfferPage = { total: number; page: number; size: number; items: OfferCard[] };
type Facet = { value: string; count: number; name?: string };
export type Facets = {
  regions: Facet[]; contracts: Facet[]; sectors: Facet[]; sources: Facet[]; all_regions: string[];
  functions: Facet[]; sector_groups: Facet[]; experiences: Facet[];
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`API ${path} : ${r.status}`);
  return r.json();
}

export const searchOffers = (params: Record<string, string | undefined>) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
  return get<OfferPage>(`/api/offers?${qs}`);
};
export const getFacets = () => get<Facets>("/api/offers/facets");
export const getOffer = (id: string, lang: string) => get<OfferDetail>(`/api/offers/${id}?lang=${lang}`);
