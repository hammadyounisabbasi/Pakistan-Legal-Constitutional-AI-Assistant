import argparse
import asyncio
import json
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.services.catalog import Catalog
from backend.app.vectorstore.factory import get_vector_store


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest configured official Pakistani legal sources")
    parser.add_argument("--sources", type=Path, default=Path("backend/app/ingestion/sources.json"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    configure_logging()
    settings = get_settings()
    report = await IngestionPipeline(settings, Catalog(settings.database_path), get_vector_store()).run(args.sources, args.force)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

