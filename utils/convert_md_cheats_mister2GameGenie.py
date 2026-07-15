#!/usr/bin/env python3
import argparse
import os
import re
from pathlib import Path


RAM_START = 0xFF0000
RAM_END = 0xFFFFFF


def clean_value(value):
    """
    Remove quotes and spaces from RetroArch/MiSTer-style values.
    """
    if value is None:
        return ""

    value = value.strip()

    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]

    return value.strip()


def parse_cht_file(path):
    """
    Parse RetroArch-style .cht files.

    Expected lines:
      cheat0_desc = "Infinite Lives"
      cheat0_code = "FF1234:09"
      cheat0_address = "FF1234"
      cheat0_value = "09"
      cheat0_enable = "true"

    Returns a dict:
      {
        0: {
          "desc": "...",
          "address": "...",
          "value": "...",
          "code": "...",
          ...
        }
      }
    """
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


def normalize_hex(value):
    """
    Convert values like:
      0xFF1234
      FF1234
      ff1234
      "FF1234"
    into uppercase hex without 0x.
    """
    value = clean_value(value)
    value = value.upper()

    if value.startswith("0X"):
        value = value[2:]

    value = re.sub(r"[^0-9A-F]", "", value)

    return value


def is_probably_game_genie(code):
    """
    Mega Drive / Genesis Game Genie codes are usually ABCD-EFGH style.
    This is intentionally permissive.
    """
    code = clean_value(code).upper()
    return bool(re.match(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$", code))


def is_probably_action_replay(code):
    """
    Common Action Replay style:
      FF1234:09
      FF1234:0009
      FFFF00:FFFF
    """
    code = clean_value(code).upper()
    return bool(re.match(r"^[0-9A-F]{6}:[0-9A-F]{2,4}$", code))


def address_value_to_ar(address, value):
    """
    Convert address + value into Action Replay style:
      FF1234:09

    Only converts obvious Mega Drive RAM addresses FF0000-FFFFFF by default.
    """
    address_hex = normalize_hex(address)
    value_hex = normalize_hex(value)

    if not address_hex or not value_hex:
        return None

    # Mega Drive 68000 addresses are normally 6 hex digits.
    if len(address_hex) > 6:
        address_hex = address_hex[-6:]

    address_hex = address_hex.zfill(6)

    try:
        address_int = int(address_hex, 16)
    except ValueError:
        return None

    if not (RAM_START <= address_int <= RAM_END):
        return None

    # Keep byte or word values.
    if len(value_hex) <= 2:
        value_hex = value_hex.zfill(2)
    elif len(value_hex) <= 4:
        value_hex = value_hex.zfill(4)
    else:
        # Too large for a simple AR code.
        return None

    return f"{address_hex}:{value_hex}"


def convert_cheat_entry(entry):
    """
    Return:
      (description, code, note)

    code may be Game Genie or Action Replay.
    """
    desc = (
        entry.get("desc")
        or entry.get("description")
        or entry.get("name")
        or "Unnamed cheat"
    )

    # Some packs already contain a complete code.
    raw_code = entry.get("code")

    if raw_code:
        raw_code = clean_value(raw_code).upper()

        # Some RetroArch cheats use + as separator for several codes.
        # Example: "FF1234:09+FF1235:09"
        split_codes = re.split(r"[+,;]", raw_code)
        valid_codes = []

        for code in split_codes:
            code = code.strip().upper()

            if is_probably_game_genie(code) or is_probably_action_replay(code):
                valid_codes.append(code)

        if valid_codes:
            return desc, valid_codes, None

    # Otherwise try address + value.
    address = entry.get("address")
    value = entry.get("value")

    ar_code = address_value_to_ar(address, value)

    if ar_code:
        return desc, [ar_code], None

    return desc, [], "Could not convert automatically"


def write_everdrive_txt(input_path, output_path, include_unconverted=True):
    cheats = parse_cht_file(input_path)

    converted_count = 0
    skipped_count = 0

    with open(output_path, "w", encoding="utf-8", newline="\n") as out:
        out.write(f"# Converted from: {os.path.basename(input_path)}\n")
        out.write("# Format: description line followed by Game Genie or Action Replay code\n\n")

        for index in sorted(cheats.keys()):
            entry = cheats[index]
            desc, codes, note = convert_cheat_entry(entry)

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

                    if "address" in entry:
                        out.write(f"# address={entry.get('address')}\n")
                    if "value" in entry:
                        out.write(f"# value={entry.get('value')}\n")
                    if "code" in entry:
                        out.write(f"# code={entry.get('code')}\n")

                    out.write("\n")

    return converted_count, skipped_count


def convert_file(input_file, output_dir=None, suffix=".txt"):
    input_path = Path(input_file)

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / (input_path.stem + suffix)
    else:
        output_path = input_path.with_suffix(suffix)

    converted, skipped = write_everdrive_txt(input_path, output_path)

    print(f"Input:     {input_path}")
    print(f"Output:    {output_path}")
    print(f"Converted: {converted}")
    print(f"Skipped:   {skipped}")


def convert_directory(input_dir, output_dir=None, suffix=".txt"):
    input_dir = Path(input_dir)

    files = sorted(input_dir.rglob("*.cht"))

    if not files:
        print(f"No .cht files found in {input_dir}")
        return

    for file in files:
        if output_dir:
            # Preserve relative folder structure.
            rel = file.relative_to(input_dir)
            target_dir = Path(output_dir) / rel.parent
        else:
            target_dir = None

        convert_file(file, target_dir, suffix=suffix)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Convert RetroArch/MiSTer Mega Drive .cht cheats to simple EverDrive-style .txt files."
    )

    parser.add_argument(
        "input",
        help="Input .cht file or directory containing .cht files"
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        help="Output directory. If omitted, .txt files are created next to the source files."
    )

    parser.add_argument(
        "--suffix",
        default=".txt",
        help="Output suffix. Default: .txt"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_dir():
        convert_directory(input_path, args.output_dir, args.suffix)
    elif input_path.is_file():
        convert_file(input_path, args.output_dir, args.suffix)
    else:
        raise SystemExit(f"Input does not exist: {input_path}")


if __name__ == "__main__":
    main()