"""Recalcule les champs dérivés (Markdown, fonction, secteur, expérience, compétences) : python -m scripts.backfill"""
from sqlalchemy import select

from app.db import SessionLocal
from app.matching.skills import extract_skills
from app.models import Offer
from app.sourcing.markdown import bulletize, reflow, structure_plain, tidy
from app.sourcing.taxonomy import experience_level, job_function, sector_group

if __name__ == "__main__":
    with SessionLocal() as s:
        n = 0
        for o in s.scalars(select(Offer)):
            if o.source == "anapec" and o.description and not o.description.lstrip().startswith("**"):
                o.description = structure_plain(o.description)
            if o.source == "anapec" and o.description:
                o.description = bulletize(o.description)
            elif o.description:
                o.description = reflow(tidy(o.description))
            o.job_function = job_function(o.title, o.occupation, o.description)
            o.sector_group = sector_group(o.sector, o.title)
            o.experience_level = experience_level(o.experience, o.description)
            o.skills = extract_skills("\n".join(filter(None, [o.title, o.occupation, o.education, o.description])))
            n += 1
        s.commit()
    print("offres recalculées :", n)
