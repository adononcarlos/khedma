"""Publie le projet sur le Space Hugging Face : python deploy/push_space.py

Assemble un dossier minimal (Dockerfile, backend, frontend, export de la base, README du Space), le téléverse,
et règle les variables et secrets du Space. Utilisé en local et par l'action GitHub (.github/workflows/deploy.yml).
Variables d'environnement : HF_TOKEN (obligatoire) ; secrets transmis au Space s'ils sont définis :
GCP_SERVICE_ACCOUNT_JSON, FIRECRAWL_API_KEY, JWT_SECRET.
"""
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
SPACE = os.environ.get("HF_SPACE", "Carlosaish/khedma")
README = """---
title: Khedma
emoji: 💼
colorFrom: purple
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Offres d'emploi du Maroc, matching IA et CV dans la langue de l'offre
---

Khedma regroupe les offres d'emploi marocaines (ANAPEC, ReKrute, Indeed, MarocEmploi, Dreamjob), les classe selon le
profil du candidat et génère un CV et une lettre dans la langue de chaque offre.
"""
IGNORE = shutil.ignore_patterns("node_modules", ".next", "__pycache__", "*.pyc", ".env*", "tests", "*.dump", "artefacts")


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds and not os.environ.get("GCP_SERVICE_ACCOUNT_JSON") and (ROOT / creds).exists():
        os.environ["GCP_SERVICE_ACCOUNT_JSON"] = (ROOT / creds).read_text()


def main() -> None:
    load_env()
    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(SPACE, repo_type="space", space_sdk="docker", exist_ok=True)

    variables = {"LLM_PROVIDER": "gemini", "LLM_MODEL": os.environ.get("LLM_MODEL", "gemini-3.8-flash"),
                 "GCP_LOCATION": os.environ.get("GCP_LOCATION", "eu")}
    for k, v in variables.items():
        api.add_space_variable(SPACE, k, v)
    for k in ("GCP_SERVICE_ACCOUNT_JSON", "FIRECRAWL_API_KEY", "JWT_SECRET"):
        if os.environ.get(k):
            api.add_space_secret(SPACE, k, os.environ[k])

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        shutil.copy(ROOT / "deploy/Dockerfile", out / "Dockerfile")
        shutil.copytree(ROOT / "backend", out / "backend", ignore=IGNORE)
        shutil.copytree(ROOT / "frontend", out / "frontend", ignore=IGNORE)
        (out / "deploy").mkdir()
        for f in ("start.sh", "khedma.dump"):
            shutil.copy(ROOT / "deploy" / f, out / "deploy" / f)
        (out / "README.md").write_text(README, encoding="utf-8")
        api.upload_folder(folder_path=str(out), repo_id=SPACE, repo_type="space", delete_patterns=["**"],
                          commit_message=os.environ.get("DEPLOY_MESSAGE", "Mise à jour du site"))
    print(f"Publié : https://huggingface.co/spaces/{SPACE}  ->  https://{SPACE.replace('/', '-').lower()}.hf.space")


if __name__ == "__main__":
    main()
