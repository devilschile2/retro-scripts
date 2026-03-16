#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import yaml  # pip install pyyaml
except ImportError:
    yaml = None


def load_config(path: Path) -> dict:
    suffix = path.suffix.lower()

    with path.open("r", encoding="utf-8") as f:
        if suffix == ".json":
            return json.load(f)
        if suffix in {".yml", ".yaml"}:
            if yaml is None:
                raise RuntimeError(
                    "PyYAML is not installed. Install it with: pip install pyyaml"
                )
            return yaml.safe_load(f)

    raise ValueError(f"Unsupported config format: {path}")


def download_file(url: str, dest: Path) -> None:
    req = Request(
        url,
        headers={
            "User-Agent": "romvault-dat-updater/1.0"
        },
    )

    with urlopen(req, timeout=60) as response, dest.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output_dir)


def update_source(source: dict) -> None:
    name = source["name"]
    url = source["url"]
    output_dir = Path(source["output_dir"])

    logging.info("Updating source '%s' from %s", name, url)

    with tempfile.TemporaryDirectory(prefix=f"datup_{name}_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_path = tmpdir_path / f"{name}.zip"

        download_file(url, zip_path)
        extract_zip(zip_path, output_dir)

    logging.info("Finished '%s' -> %s", name, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and extract DAT files for RomVault.")
    parser.add_argument(
        "config",
        type=Path,
        help="Path to JSON or YAML config file.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        config = load_config(args.config)
        sources = config.get("sources", [])

        if not sources:
            logging.error("No sources found in config.")
            return 1

        for source in sources:
            try:
                update_source(source)
            except Exception as exc:
                logging.exception("Failed updating '%s': %s", source.get("name", "unknown"), exc)

        return 0

    except Exception as exc:
        logging.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
