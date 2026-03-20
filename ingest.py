from __future__ import annotations

import argparse

from sap_navigator.config import get_config
from sap_navigator.rag import ensure_knowledge_dir, ingest_knowledge_base


def main() -> None:
    parser = argparse.ArgumentParser(description="Index SAP TM/TMS knowledge into the local vector store.")
    parser.add_argument("--append", action="store_true", help="Append to the current collection instead of replacing it.")
    args = parser.parse_args()

    config = get_config()
    ensure_knowledge_dir(config.knowledge_dir)
    report, stats = ingest_knowledge_base(config, reset=not args.append)

    print(f"Knowledge directory: {config.knowledge_dir}")
    print(f"Documents loaded: {len(report.loaded_documents)}")
    print(f"Files skipped: {len(report.skipped_files)}")
    print(f"Chunks indexed: {len(report.chunks)}")
    print(f"Collection size: {stats.chunk_count}")

    if report.skipped_files:
        print("\nSkipped files:")
        for skipped in report.skipped_files:
            print(f"- {skipped.path}: {skipped.reason}")


if __name__ == "__main__":
    main()

