#!/usr/bin/env python3
import argparse
import os
import re
from pathlib import Path

SYSTEMS = {
    "md": {
        "name": "Mega Drive / Genesis",
        "address_len": 6,
        "ram_start": 0xFF0000,
        "ram_end": 0xFFFFFF,
    },
    "sms": {
        "name": "Master System",
        "address_len": 4,
        "ram_start": 0xC000,
        "ram_end": 0xDFFF,
    },
    "gg": {
        "name": "Game Gear",
        "address_len": 4,
        "ram_start": 0xC000,
        "ram_end": 0xDFFF,
    },
}


def clean_value(value):
    if value is None:
        return ""

    value = value.strip()

    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]

    return value.strip()


def normalize_hex(value):
    value = clean_value(value).upper()

    if value.startswith("0X"):
        value = value[2:]

    return re.sub(r"[^0-9A-F]", "", value)


def parse_cht_file(path):
    cheats = {}
    pattern = re.compile(r"^cheat(\d+)_([A-Za-z0-9_]+)\s*=\s*(.*)$")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            match = pattern.match(line)
            if not match:
                continue

            index = int(match.group(1))
            key = match.group(2).lower()
            value = clean_value(match.group(3))

            cheats.setdefault(index, {})
            cheats[index][key] = value

    return cheats


def is_game_genie(code):
    code = clean_value(code).upper()
    return bool(re.match(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$", code))


def is_action_replay(code, system):
    code = clean_value(code).upper()

    if system == "md":
        return bool(re.match(r"^[0-9A-F]{6}:[0-9A-F]{2,4}$", code))

    if system in ("sms", "gg"):
        return bool(re.match(r"^[0-9A-F]{4}:[0-9A-F]{2,4}$", code))

    return False


def normalize_action_replay(code, system):
    code = clean_value(code).upper().replace(" ", "")

    if not is_action_replay(code, system):
        return None

    address, value = code.split(":", 1)
    value = normalize_hex(value)

    if len(value) <= 2:
        value = value.zfill(2)
    elif len(value) <= 4:
        value = value.zfill(4)
    else:
        return None

    return f"{address}:{value}"


def address_value_to_action_replay(address, value, system):
    cfg = SYSTEMS[system]

    address_hex = normalize_hex(address)
    value_hex = normalize_hex(value)

    if not address_hex or not value_hex:
        return None

    address_len = cfg["address_len"]

    if len(address_hex) > address_len:
        address_hex = address_hex[-address_len:]

    address_hex = address_hex.zfill(address_len)

    try:
        address_int = int(address_hex, 16)
    except ValueError:
        return None

    if not (cfg["ram_start"] <= address_int <= cfg["ram_end"]):
        return None

    if len(value_hex) <= 2:
        value_hex = value_hex.zfill(2)
    elif len(value_hex) <= 4:
        value_hex = value_hex.zfill(4)
    else:
        return None

    return f"{address_hex}:{value_hex}"


def convert_entry_to_action_replay(entry, system):
    desc = (
        entry.get("desc")
        or entry.get("description")
        or entry.get("name")
        or "Unnamed cheat"
    )

    # Prefer explicit address/value conversion.
    address = entry.get("address")
    value = entry.get("value")

    ar_code = address_value_to_action_replay(address, value, system)
    if ar_code:
        return desc, [ar_code], None

    # If the source already has Action Replay codes, keep them.
    raw_code = entry.get("code")
    if raw_code:
        raw_code = clean_value(raw_code).upper()
        split_codes = re.split(r"[+,;]", raw_code)

        ar_codes = []
        game_genie_codes = []

        for code in split_codes:
            code = code.strip().upper()

            normalized_ar = normalize_action_replay(code, system)
            if normalized_ar:
                ar_codes.append(normalized_ar)
            elif is_game_genie(code):
                game_genie_codes.append(code)

        if ar_codes:
            return desc, ar_codes, None

        if game_genie_codes:
            return desc, [], "Source is Game Genie, not converted to Action Replay"

    return desc, [], "No RAM address/value Action Replay conversion found"


def write_output(input_path, output_path, system, include_unconverted=True):
    cheats = parse_cht_file(input_path)

    converted_count = 0
    skipped_count = 0

    with open(output_path, "w", encoding="utf-8", newline="\n") as out:
        out.write(f"# Converted from: {os.path.basename(input_path)}\n")
        out.write(f"# Target: {SYSTEMS[system]['name']}\n")
        out.write("# Format: Action Replay only, ADDRESS:VALUE\n\n")

        for index in sorted(cheats.keys()):
            entry = cheats[index]
            desc, codes, note = convert_entry_to_action_replay(entry, system)

            if codes:
                converted_count += 1
                out.write(f"{desc}\n")
                for code in codes:
                    out.write(f"{code}\n")
                out.write("\n")
            else:
                skipped_count += 1

                if include_unconverted:
                    out.write(f"# {desc}\n")
                    out.write(f"# NOT CONVERTED: {note}\n")

                    for key in ("address", "value", "code"):
                        if key in entry:
                            out.write(f"# {key}={entry.get(key)}\n")

                    out.write("\n")

    return converted_count, skipped_count


def convert_file(input_file, output_dir, suffix, system):
    input_path = Path(input_file)

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / (input_path.stem + suffix)
    else:
        output_path = input_path.with_suffix(suffix)

    converted, skipped = write_output(input_path, output_path, system)

    print(f"Input:     {input_path}")
    print(f"Output:    {output_path}")
    print(f"System:    {system}")
    print(f"Converted: {converted}")
    print(f"Skipped:   {skipped}")


def convert_directory(input_dir, output_dir, suffix, system):
    input_dir = Path(input_dir)
    files = sorted(input_dir.rglob("*.cht"))

    if not files:
        print(f"No .cht files found in {input_dir}")
        return

    for file in files:
        if output_dir:
            rel = file.relative_to(input_dir)
            target_dir = Path(output_dir) / rel.parent
        else:
            target_dir = None

        convert_file(file, target_dir, suffix, system)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Convert RetroArch/MiSTer .cht cheats to Action Replay .txt files."
    )

    parser.add_argument(
        "input",
        help="Input .cht file or directory containing .cht files"
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        help="Output directory. If omitted, .txt files are created next to source files."
    )

    parser.add_argument(
        "--system",
        choices=["md", "sms", "gg"],
        default="md",
        help="Target system: md, sms, or gg. Default: md"
    )

    parser.add_argument(
        "--suffix",
        default=".txt",
        help="Output suffix. Default: .txt"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_dir():
        convert_directory(input_path, args.output_dir, args.suffix, args.system)
    elif input_path.is_file():
        convert_file(input_path, args.output_dir, args.suffix, args.system)
    else:
        raise SystemExit(f"Input does not exist: {input_path}")


if __name__ == "__main__":
    main()