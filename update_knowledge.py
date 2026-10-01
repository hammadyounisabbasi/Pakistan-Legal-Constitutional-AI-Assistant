"""Incremental update entry point; unchanged document hashes are skipped."""
import asyncio

from ingest import main

if __name__ == "__main__":
    asyncio.run(main())

