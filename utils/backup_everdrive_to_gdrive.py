#!/usr/bin/env python3
import argparse
import datetime as dt
import mimetypes
import os
import shutil
import tarfile
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload



# Google Cloud Console
# → Enable Google Drive API
# → Credentials
# → Create OAuth client ID
# → Desktop app
# → Download JSON
# → save as: credentials.json


# Put credentials.json next to the script



SCOPES = ["https://www.googleapis.com/auth/drive.file"]


DEFAULT_BACKUP_CANDIDATES = [
    "MEGA/SAVE",
    "MEGA/STATE",
    "MEGA/SNAP",
    "MEGA/CHEATS",
    "MEGA/CFG",
    "MEGA",
    "SAVE",
    "STATE",
    "SNAP",
    "CHEATS",
]


def build_drive_service(credentials_file: Path, token_file: Path):
    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file),
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


def find_or_create_drive_folder(service, folder_name, parent_id=None):
    escaped_name = folder_name.replace("'", "\\'")
    query_parts = [
        "mimeType = 'application/vnd.google-apps.folder'",
        f"name = '{escaped_name}'",
        "trashed = false",
    ]

    if parent_id:
        query_parts.append(f"'{parent_id}' in parents")

    query = " and ".join(query_parts)

    result = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=10,
    ).execute()

    files = result.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(
        body=metadata,
        fields="id",
    ).execute()

    return folder["id"]


def upload_file(service, local_file: Path, drive_folder_id: str):
    mime_type, _ = mimetypes.guess_type(str(local_file))
    if not mime_type:
        mime_type = "application/gzip"

    metadata = {
        "name": local_file.name,
        "parents": [drive_folder_id],
    }

    media = MediaFileUpload(
        str(local_file),
        mimetype=mime_type,
        resumable=True,
    )

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name, size, webViewLink",
    ).execute()

    return uploaded


def collect_existing_paths(sd_root: Path, relative_paths):
    existing = []

    for rel in relative_paths:
        path = sd_root / rel
        if path.exists():
            existing.append(path)

    return existing


def create_backup_archive(sd_root: Path, output_dir: Path, include_paths, prefix: str):
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_path = output_dir / f"{prefix}_{timestamp}.tar.gz"

    existing_paths = collect_existing_paths(sd_root, include_paths)

    if not existing_paths:
        raise RuntimeError(
            "No save/state folders found. "
            "Check the SD root path or pass --include with the correct folders."
        )

    with tarfile.open(archive_path, "w:gz") as tar:
        for path in existing_paths:
            arcname = path.relative_to(sd_root)
            print(f"Adding: {arcname}")
            tar.add(path, arcname=str(arcname))

    return archive_path, existing_paths


def prune_local_backups(output_dir: Path, prefix: str, keep: int):
    if keep <= 0:
        return

    backups = sorted(
        output_dir.glob(f"{prefix}_*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[keep:]:
        print(f"Removing old local backup: {old_backup}")
        old_backup.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Backup Mega EverDrive saves/states to Google Drive."
    )

    parser.add_argument(
        "--sd-root",
        required=True,
        help="Mounted root path of the EverDrive SD card, e.g. /run/media/user/MEGAED",
    )

    parser.add_argument(
        "--output-dir",
        default=str(Path.home() / "backups" / "mega-everdrive"),
        help="Local folder where .tar.gz backups are created.",
    )

    parser.add_argument(
        "--drive-folder",
        default="Mega EverDrive Backups",
        help="Google Drive folder name to upload backups into.",
    )

    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Google OAuth client credentials JSON.",
    )

    parser.add_argument(
        "--token",
        default="token.json",
        help="OAuth token file created after first login.",
    )

    parser.add_argument(
        "--prefix",
        default="mega-everdrive-backup",
        help="Backup filename prefix.",
    )

    parser.add_argument(
        "--keep-local",
        type=int,
        default=10,
        help="Number of local .tar.gz backups to keep.",
    )

    parser.add_argument(
        "--include",
        action="append",
        help=(
            "Relative path inside SD root to include. "
            "Can be used multiple times. "
            "If omitted, common EverDrive folders are tried."
        ),
    )

    args = parser.parse_args()

    sd_root = Path(args.sd_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    credentials_file = Path(args.credentials).expanduser().resolve()
    token_file = Path(args.token).expanduser().resolve()

    if not sd_root.exists():
        raise SystemExit(f"SD root does not exist: {sd_root}")

    if not credentials_file.exists():
        raise SystemExit(f"Missing Google credentials file: {credentials_file}")

    include_paths = args.include if args.include else DEFAULT_BACKUP_CANDIDATES

    print("== Creating backup archive ==")
    archive_path, included = create_backup_archive(
        sd_root=sd_root,
        output_dir=output_dir,
        include_paths=include_paths,
        prefix=args.prefix,
    )

    print()
    print(f"Created backup: {archive_path}")
    print(f"Included paths: {len(included)}")

    print()
    print("== Connecting to Google Drive ==")
    service = build_drive_service(credentials_file, token_file)

    print(f"== Ensuring Drive folder exists: {args.drive_folder} ==")
    folder_id = find_or_create_drive_folder(service, args.drive_folder)

    print("== Uploading backup ==")
    uploaded = upload_file(service, archive_path, folder_id)

    print()
    print("Uploaded:")
    print(f"  name: {uploaded.get('name')}")
    print(f"  id:   {uploaded.get('id')}")
    print(f"  link: {uploaded.get('webViewLink')}")

    print()
    print("== Pruning local backups ==")
    prune_local_backups(output_dir, args.prefix, args.keep_local)

    print("Done.")


if __name__ == "__main__":
    main()