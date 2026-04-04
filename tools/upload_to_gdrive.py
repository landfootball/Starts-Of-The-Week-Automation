"""
Uploads PNG files to Google Drive root (or a specified folder).

Handles both:
  - Local dev: reads credentials.json + token.json from project root
  - Streamlit Cloud: reads credentials from st.secrets["GOOGLE_CREDENTIALS_JSON"]
    and token from st.secrets["GOOGLE_TOKEN_JSON"]

Usage:
    from tools.upload_to_gdrive import upload_file, upload_all_outputs
    url = upload_file(Path("output/seahawks_def_card_2025-09-10.png"))
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

# Google API imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CREDENTIALS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"
OUTPUT_DIR = ROOT / "output"


def _get_credentials() -> Credentials:
    """
    Load Google credentials. Tries Streamlit secrets first, falls back to local files.
    """
    creds = None

    # ── Streamlit Cloud path ───────────────────────────────────────────────────
    try:
        import streamlit as st
        if "GOOGLE_TOKEN_JSON" in st.secrets:
            token_data = json.loads(st.secrets["GOOGLE_TOKEN_JSON"])
            creds_data = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    except Exception:
        pass

    # ── Local dev path ─────────────────────────────────────────────────────────
    if not creds and TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token locally if possible
        if TOKEN_PATH.parent.exists():
            TOKEN_PATH.write_text(creds.to_json())

    # First-time auth (local only)
    if not creds or not creds.valid:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                "Google credentials not found. "
                "See SETUP.md for instructions to download credentials.json "
                "from Google Cloud Console."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_PATH}")

    return creds


def _get_drive_service():
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds)


def upload_file(
    file_path: Path,
    folder_id: str | None = None,
    overwrite: bool = True,
) -> str:
    """
    Upload a single file to Google Drive.

    Args:
        file_path: Path to the local file to upload
        folder_id: Google Drive folder ID. None = root of My Drive.
        overwrite: If True, delete existing file with same name before uploading.

    Returns:
        Shareable Google Drive URL for the uploaded file.
    """
    service = _get_drive_service()
    file_name = file_path.name

    # Check for existing file with same name (for overwrite)
    if overwrite:
        query = f"name='{file_name}' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        existing = service.files().list(q=query, fields="files(id)").execute()
        for f in existing.get("files", []):
            service.files().delete(fileId=f["id"]).execute()

    # File metadata
    metadata = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]

    # Upload
    media = MediaFileUpload(str(file_path), mimetype="image/png", resumable=False)
    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    file_id = uploaded["id"]

    # Make publicly viewable (so the link works for anyone with it)
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    link = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
    return link


def upload_all_outputs(folder_id: str | None = None) -> list[dict]:
    """
    Upload all PNG files in the output/ directory to Google Drive.

    Returns:
        List of {"file": filename, "url": drive_url} dicts.
    """
    results = []
    png_files = sorted(OUTPUT_DIR.glob("*.png"))
    if not png_files:
        print("No PNG files found in output/")
        return results

    for png in png_files:
        print(f"  Uploading {png.name} ...", end=" ", flush=True)
        try:
            url = upload_file(png, folder_id=folder_id)
            print(f"OK → {url}")
            results.append({"file": png.name, "url": url})
        except Exception as e:
            print(f"FAILED ({e})")
            results.append({"file": png.name, "url": None, "error": str(e)})

    return results


if __name__ == "__main__":
    print("=== Google Drive Uploader ===")
    results = upload_all_outputs()
    print(f"\nUploaded {sum(1 for r in results if r.get('url'))} / {len(results)} files")
