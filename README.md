# Khedma

Plateforme de recherche d'emploi pour le Maroc : agrégation des offres (ANAPEC, Indeed, ReKrute, MarocEmploi, Dreamjob), matching IA profil/offre, CV et lettre générés dans la langue de l'offre, espace conseiller et observatoire du marché.

Démo : les offres sont réelles (lien vers l'annonce d'origine) ; les comptes, candidatures et placements sont des données de démonstration (`users.is_demo`).

## Architecture

```
Sources ──> connecteurs (httpx / Firecrawl) ──> normalisation (région, contrat, métier, secteur, expérience)
        ──> dédoublonnage ──> compétences (dictionnaire) ──> embeddings multilingues LOCAUX
        ──> PostgreSQL + pgvector (HNSW)
                     │
            FastAPI  ├── matching 2 étages (rappel vectoriel + score explicable), 0 token
                     ├── CV / lettre : mise en page ATS déterministe + rédaction Gemini (au clic, en cache)
                     ├── traduction à la demande (cache par offre et langue)
                     └── espace conseiller, observatoire, détection des profils fantômes
                     │
            Next.js 16 (FR / AR en RTL / EN, mode sombre)
```

**Économie de tokens** : le LLM n'intervient que pour rédiger (accroche, lettre) et traduire, à la demande, avec un brief compact et un cache en base. Matching, tri, mise en page, traduction des champs normalisés : zéro token.

## Lancer en local

```bash
docker compose up -d db                              # Postgres 17 + pgvector sur 127.0.0.1:5433
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
.venv/bin/playwright install chromium                # rendu PDF des CV
cp .env.example .env                                 # puis compléter

cd backend
../.venv/bin/python -m scripts.ingest anapec --pages 80          # sources : anapec, rekrute, marocemploi, dreamjob, indeed
../.venv/bin/python -m scripts.embed_offers
../.venv/bin/python -m scripts.seed_demo                          # comptes de démonstration
../.venv/bin/uvicorn app.main:app --port 8010 --reload

cd ../frontend && npm install && npx next dev -p 3010
```

Comptes de démo (mot de passe `demo12345`) : `yassine.demo@example.com` (candidat), `conseiller6@demo.khedma.ma` (conseiller Casablanca-Settat), `admin@demo.khedma.ma` (observatoire).

## IA (Gemini sur Vertex AI)

1. Placer le JSON du compte de service dans `secrets/gcp-service-account.json` (dossier ignoré par git).
2. Dans `.env` : `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-3.8-flash`, `GCP_LOCATION=eu`, `GOOGLE_APPLICATION_CREDENTIALS=secrets/gcp-service-account.json`.
3. Rôle requis pour le compte de service : `Vertex AI User`.

Sans identifiants, la plateforme bascule automatiquement en mode simulé (gabarits FR/EN/AR).

## Sources et conformité

Respect du `robots.txt`, rythme limité, attribution et lien vers l'offre d'origine. LinkedIn et MarocAnnonces sont exclus (interdits par leur `robots.txt`). Indeed passe par Firecrawl ; ses conditions d'utilisation restreignent le scraping : usage limité à cette démo.
