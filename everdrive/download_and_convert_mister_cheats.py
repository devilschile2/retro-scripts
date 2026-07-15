#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_URL = "https://github.com/MiSTer-devel/Cheats_MiSTer.git"


SYSTEM_FOLDER_HINTS = {
    "md": [
        "Genesis",
        "MegaDrive",
        "Mega Drive",
        "Mega_Drive",
        "MegaDrive_Genesis",
        "Sega Genesis",
    ],
    "sms": [
        "SMS",
        "MasterSystem",
        "Master System",
        "Sega Master System",
    ],
    "gg": [
        "GameGear",
        "Game Gear",
        "GG",
    ],
}


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_git_available() -> None:
    if shutil.which("git") is None:
        raise SystemExit("git is not installed. Install git first.")


def clone_or_update_repo(repo_dir: Path) -> None:
    ensure_git_available()

    if repo_dir.exists() and (repo_dir / ".git").exists():
        run(["git", "pull", "--ff-only"], cwd=repo_dir)
        return

    if repo_dir.exists() and any(repo_dir.iterdir()):
        raise SystemExit(f"Directory exists but is not an empty git repo: {repo_dir}")

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--depth", "1", REPO_URL, str(repo_dir)])


def find_cheats_root(repo_dir: Path) -> Path:
    candidates = [
        repo_dir / "Cheats",
        repo_dir / "cheats",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    return repo_dir


def find_system_dirs(cheats_root: Path, system: str) -> list[Path]:
    hints = SYSTEM_FOLDER_HINTS[system]
    found: list[Path] = []

    for path in cheats_root.rglob("*"):
        if not path.is_dir():
            continue

        name_normalized = path.name.lower().replace("_", " ").replace("-", " ")

        for hint in hints:
            hint_normalized = hint.lower().replace("_", " ").replace("-", " ")
            if hint_normalized == name_normalized:
                found.append(path)
                break

    # If no folder found, try broader substring matching.
    if not found:
        for path in cheats_root.rglob("*"):
            if not path.is_dir():
                continue

            name_normalized = path.name.lower().replace("_", " ").replace("-", " ")

            if system == "md" and ("genesis" in name_normalized or "mega" in name_normalized):
                found.append(path)
            elif system == "sms" and ("master" in name_normalized or name_normalized == "sms"):
                found.append(path)
            elif system == "gg" and ("game gear" in name_normalized or name_normalized == "gg"):
                found.append(path)

    # Only keep dirs that actually contain .cht files.
    found = [p for p in found if list(p.rglob("*.cht"))]

    # De-duplicate.
    return sorted(set(found))


def call_converter(converter: Path, input_dir: Path, output_dir: Path, system: str, mode: str) -> None:
    cmd = [
        sys.executable,
        str(converter),
        str(input_dir),
        "-o",
        str(output_dir),
        "--system",
        system,
        "--mode",
        mode,
    ]

    run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download MiSTer cheats and convert Genesis/SMS/GG cheats to EverDrive txt format."
    )

    parser.add_argument(
        "--work-dir",
        default="./mister-cheats-work",
        help="Working directory where the GitHub repo will be cloned.",
    )

    parser.add_argument(
        "--output-dir",
        default="./everdrive-cheats",
        help="Output folder for converted cheats.",
    )

    parser.add_argument(
        "--converter",
        default="./convert_mister_cheats.py",
        help="Path to convert_mister_cheats.py.",
    )

    parser.add_argument(
        "--systems",
        nargs="+",
        choices=["md", "sms", "gg"],
        default=["md", "sms"],
        help="Systems to convert. Default: md sms",
    )

    parser.add_argument(
        "--mode",
        choices=["ar", "gg", "both"],
        default="both",
        help="Output mode. Default: both.",
    )

    args = parser.parse_args()

    work_dir = Path(args.work_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    converter = Path(args.converter).expanduser().resolve()
    repo_dir = work_dir / "Cheats_MiSTer"

    if not converter.exists():
        raise SystemExit(f"Converter script not found: {converter}")

    print("== Downloading/updating MiSTer cheats ==")
    clone_or_update_repo(repo_dir)

    cheats_root = find_cheats_root(repo_dir)
    print(f"Cheats root: {cheats_root}")

    for system in args.systems:
        print()
        print(f"== Finding {system} cheat folders ==")
        system_dirs = find_system_dirs(cheats_root, system)

        if not system_dirs:
            print(f"No cheat folder found for system: {system}")
            print("You can inspect the repo manually:")
            print(f"  {cheats_root}")
            continue

        for input_dir in system_dirs:
            print(f"Found: {input_dir}")

            if args.mode == "both":
                ar_output = output_dir / system / "ActionReplay" / input_dir.name
                gg_output = output_dir / system / "GameGenie" / input_dir.name
                both_output = output_dir / system / "Mixed" / input_dir.name

                print("Converting Action Replay...")
                call_converter(converter, input_dir, ar_output, system, "ar")

                print("Converting Game Genie...")
                call_converter(converter, input_dir, gg_output, system, "gg")

                print("Converting Mixed...")
                call_converter(converter, input_dir, both_output, system, "both")
            else:
                target = output_dir / system / args.mode / input_dir.name
                call_converter(converter, input_dir, target, system, args.mode)

    print()
    print("Done.")
    print(f"Output folder: {output_dir}")


if __name__ == "__main__":
    main()