"""Lance l'ingestion d'une source : python -m scripts.ingest anapec --pages 3 | indeed --pages 2 --details"""
import argparse
import asyncio
import logging

from app.db import init_db
from app.sourcing.connectors.anapec import AnapecConnector
from app.sourcing.connectors.dreamjob import DreamjobConnector
from app.sourcing.connectors.indeed import IndeedConnector
from app.sourcing.connectors.marocemploi import MarocEmploiConnector
from app.sourcing.connectors.rekrute import RekruteConnector
from app.sourcing.pipeline import ingest, refetch_details

CONNECTORS = {"anapec": AnapecConnector, "indeed": IndeedConnector, "rekrute": RekruteConnector,
              "marocemploi": MarocEmploiConnector, "dreamjob": DreamjobConnector}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("source", choices=CONNECTORS)
    p.add_argument("--pages", type=int, default=3)
    p.add_argument("--details", action="store_true", help="fiches détail (Indeed : 1 crédit Firecrawl / offre)")
    p.add_argument("--it", action="store_true", help="Indeed : recherches métiers IT/data/IA")
    p.add_argument("--junior", action="store_true", help="Indeed : jeunes diplômés, tous secteurs")
    p.add_argument("--only-missing-details", action="store_true", help="reprendre les fiches détail en échec")
    args = p.parse_args()
    init_db()
    connector = IndeedConnector(with_details=args.details, it_searches=args.it, junior=args.junior) if args.source == "indeed" else CONNECTORS[args.source]()
    job = refetch_details(connector) if args.only_missing_details else ingest(connector, max_pages=args.pages)
    print(asyncio.run(job))
