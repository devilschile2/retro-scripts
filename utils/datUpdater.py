#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


DEFAULT_GLOBALS = {
    "state_dir": "./state",
    "temp_dir": "./tmp",
    "log_level": "INFO",
    "timeout": 60,
    "user_agent": "romvault-dat-updater/2.0",
    "cleanup_before_extract": False,
}


@dataclass
class Source:
    name: str
    url: str
    output_dir: Path
    enabled: bool = True
    cleanup_before_extract: Optional[bool] = None


class ConfigError(Exception):
    pass


def load_config(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as f:
        if suffix == ".json":
            data = json.load(f)
        elif suffix in {".yml", ".yaml"}:
            if yaml is None:
                raise ConfigError("PyYAML is required for YAML config files. Install with: pip install pyyaml")
            data = yaml.safe_load(f)
        else:
            raise ConfigError(f"Unsupported config format: {path}")
    if not isinstance(data, dict):
        raise ConfigError("Top-level config must be an object/dictionary.")
    return data


def parse_sources(config: Dict[str, Any]) -> tuple[Dict[str, Any], list[Source]]:
    global_cfg = {**DEFAULT_GLOBALS, **(config.get("global") or {})}
    raw_sources = config.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ConfigError("Config must contain a non-empty 'sources' list.")

    sources: list[Source] = []
    seen_names: set[str] = set()

    for entry in raw_sources:
        if not isinstance(entry, dict):
            raise ConfigError("Each source entry must be an object/dictionary.")

        try:
            name = str(entry["name"]).strip()
            url = str(entry["url"]).strip()
            output_dir = Path(str(entry["output_dir"]))
        except KeyError as exc:
            raise ConfigError(f"Missing required key in source entry: {exc}") from exc

        if not name:
            raise ConfigError("Source name cannot be empty.")
        if name in seen_names:
            raise ConfigError(f"Duplicate source name: {name}")
        seen_names.add(name)

        enabled = bool(entry.get("enabled", True))
        cleanup_before_extract = entry.get("cleanup_before_extract", None)
        if cleanup_before_extract is not None:
            cleanup_before_extract = bool(cleanup_before_extract)

        sources.append(
            Source(
                name=name,
                url=url,
                output_dir=output_dir,
                enabled=enabled,
                cleanup_before_extract=cleanup_before_extract,
            )
        )

    return global_cfg, sources


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def state_file_for(state_dir: Path, source_name: str) -> Path:
    return state_dir / f"{source_name}.json"


def load_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        with state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        logging.warning("Could not read state file %s; ignoring it.", state_path)
    return {}


def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    ensure_dir(state_path.parent)
    tmp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    tmp_path.replace(state_path)


def make_request(url: str, user_agent: str, etag: Optional[str], last_modified: Optional[str]) -> Request:
    headers = {"User-Agent": user_agent}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return Request(url, headers=headers)


def download_if_changed(
    url: str,
    dest: Path,
    timeout: int,
    user_agent: str,
    prior_state: Dict[str, Any],
) -> tuple[bool, Dict[str, Any]]:
    etag = prior_state.get("etag")
    last_modified = prior_state.get("last_modified")

    req = make_request(url, user_agent, etag, last_modified)

    try:
        with urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status == 304:
                return False, prior_state

            headers = response.headers
            new_state = dict(prior_state)
            new_state["etag"] = headers.get("ETag")
            new_state["last_modified"] = headers.get("Last-Modified")
            new_state["content_length"] = headers.get("Content-Length")

            with dest.open("wb") as out_file:
                shutil.copyfileobj(response, out_file)

            return True, new_state

    except HTTPError as exc:
        if exc.code == 304:
            return False, prior_state
        raise
    except URLError:
        raise


def cleanup_output_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    for child in output_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def extract_zip(zip_path: Path, output_dir: Path) -> list[str]:
    ensure_dir(output_dir)
    extracted: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            zf.extract(member, output_dir)
            extracted.append(member.filename)
    return extracted


def run_command(command: str) -> int:
    logging.info("Running post-update command: %s", command)
    completed = subprocess.run(command, shell=True, check=False)
    return completed.returncode


def iter_selected_sources(
    sources: Iterable[Source], only: Optional[set[str]]
) -> Iterable[Source]:
    for source in sources:
        if only is not None and source.name not in only:
            continue
        yield source


def update_source(
    source: Source,
    global_cfg: Dict[str, Any],
    state_dir: Path,
    temp_dir: Path,
    force: bool = False,
) -> bool:
    cleanup_default = bool(global_cfg["cleanup_before_extract"])
    cleanup_this_source = (
        source.cleanup_before_extract
        if source.cleanup_before_extract is not None
        else cleanup_default
    )

    state_path = state_file_for(state_dir, source.name)
    prior_state = load_state(state_path)
    zip_path = temp_dir / f"{source.name}.zip"

    logging.info("Checking source '%s'", source.name)
    logging.debug("URL: %s", source.url)

    if force:
        logging.info("Force mode enabled for '%s': downloading regardless of previous state.", source.name)
        prior_state = {}

    downloaded, new_state = download_if_changed(
        url=source.url,
        dest=zip_path,
        timeout=int(global_cfg["timeout"]),
        user_agent=str(global_cfg["user_agent"]),
        prior_state=prior_state,
    )

    if not downloaded:
        logging.info("No change for '%s'; skipping extraction.", source.name)
        return False

    ensure_dir(source.output_dir)
    if cleanup_this_source:
        logging.info("Cleaning output directory for '%s': %s", source.name, source.output_dir)
        cleanup_output_dir(source.output_dir)

    extracted = extract_zip(zip_path, source.output_dir)
    logging.info(
        "Updated '%s': extracted %d file(s) into %s",
        source.name,
        len(extracted),
        source.output_dir,
    )

    save_state(state_path, new_state)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and update No-Intro or similar DAT zips for RomVault."
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to YAML or JSON config file.",
    )
    parser.add_argument(
        "--only",
        help="Comma-separated source names to update, e.g. --only snes,nes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download and extract even if the remote file appears unchanged.",
    )
    parser.add_argument(
        "--post-update-cmd",
        help="Shell command to run if at least one source was updated.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional log file path.",
    )
    return parser.parse_args()


def setup_logging(level_name: str, log_file: Optional[Path]) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        ensure_dir(log_file.parent)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def main() -> int:
    args = parse_args()

    try:
        config = load_config(args.config)
        global_cfg, sources = parse_sources(config)
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    setup_logging(str(global_cfg["log_level"]), args.log_file)

    state_dir = Path(str(global_cfg["state_dir"]))
    temp_dir_base = Path(str(global_cfg["temp_dir"]))
    ensure_dir(state_dir)
    ensure_dir(temp_dir_base)

    only: Optional[set[str]] = None
    if args.only:
        only = {item.strip() for item in args.only.split(",") if item.strip()}
        if not only:
            logging.error("The --only argument was provided but no valid source names were found.")
            return 1

    selected_sources = list(iter_selected_sources(sources, only))
    if not selected_sources:
        logging.error("No sources selected.")
        return 1

    updated_any = False
    failed_any = False

    with tempfile.TemporaryDirectory(prefix="datup_", dir=temp_dir_base) as tmpdir:
        temp_dir = Path(tmpdir)

        for source in selected_sources:
            if not source.enabled:
                logging.info("Skipping disabled source '%s'.", source.name)
                continue

            try:
                changed = update_source(
                    source=source,
                    global_cfg=global_cfg,
                    state_dir=state_dir,
                    temp_dir=temp_dir,
                    force=args.force,
                )
                updated_any = updated_any or changed
            except Exception as exc:
                failed_any = True
                logging.exception("Failed updating '%s': %s", source.name, exc)

    if updated_any and args.post_update_cmd:
        rc = run_command(args.post_update_cmd)
        if rc != 0:
            logging.error("Post-update command exited with code %d.", rc)
            failed_any = True

    if failed_any:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
