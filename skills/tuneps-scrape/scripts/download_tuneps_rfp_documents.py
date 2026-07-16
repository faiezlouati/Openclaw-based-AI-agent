#!/usr/bin/env python3
"""Download Tuneps RFP documents for explicitly requested tender IDs.

Usage:
  python3 scripts/download_tuneps_rfp_documents.py 20260600248
  python3 scripts/download_tuneps_rfp_documents.py 20260600248 20260600262

Prerequisite:
  Run scripts/capture_tuneps_credentials.py after logging in to Tuneps in Chrome.

Safety rule:
  This script has no default tender list. It downloads only the tender IDs provided
  by the user/requester.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_ROOT = Path(os.environ.get("TUNEPS_DATA_ROOT", "~/.tuneps_data")).expanduser()
CREDENTIALS_FILE = Path(
    os.environ.get("TUNEPS_CREDENTIALS_FILE", DATA_ROOT / "credentials.json")
).expanduser()
DOCUMENTS_DIR = Path(os.environ.get("TUNEPS_DOCUMENTS_DIR", DATA_ROOT / "documents")).expanduser()
BASE = "https://www.tuneps.tn/api2"
BID_NO_RE = re.compile(r"^[0-9A-Za-z_-]{6,40}$")


def load_credentials() -> dict[str, str]:
    """Load credentials and fail early if they are missing/expired."""
    if not CREDENTIALS_FILE.exists():
        print(f"Credentials file not found: {CREDENTIALS_FILE}")
        print("Run capture_tuneps_credentials.py first after logging in to Tuneps.")
        sys.exit(1)

    with CREDENTIALS_FILE.open(encoding="utf-8") as handle:
        creds = json.load(handle)

    for key in ("jwt", "cookie", "expires"):
        if not creds.get(key):
            print(f"Credentials file is missing required field: {key}")
            sys.exit(1)

    expires = time.strptime(creds["expires"], "%Y-%m-%d %H:%M:%S")
    if time.localtime() > expires:
        print("Token expired. Run capture_tuneps_credentials.py again.")
        sys.exit(1)

    print(f"Credentials loaded. Valid until {creds['expires']}")
    return creds


def get_headers(creds: dict[str, str]) -> dict[str, str]:
    """Build Tuneps request headers using stored credentials."""
    return {
        "Authorization": f"Bearer {creds['jwt']}",
        "Cookie": f"cookiesession1={creds['cookie']}",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }


def get_file_list(bid_no: str, headers: dict[str, str]) -> list[dict]:
    """Fetch the list of documents attached to a given tender number."""
    response = requests.get(
        f"{BASE}/ged//vAttachFile/getByBidNo",
        params={"bidNo": bid_no},
        headers=headers,
        timeout=60,
        verify=False,
    )
    if response.status_code == 401:
        print("Token expired or unauthorized. Run capture_tuneps_credentials.py again.")
        sys.exit(1)
    if response.status_code != 200:
        print(f"Error {response.status_code} for tender {bid_no}")
        return []

    data = response.json()
    payload = data.get("payload", [])
    return payload if isinstance(payload, list) else []


def safe_filename(name: str) -> str:
    """Avoid path traversal while preserving normal file names."""
    cleaned = os.path.basename(name).strip()
    return cleaned or "document.bin"


def download_file(file_info: dict, tender_dir: Path, headers: dict[str, str]) -> Path | None:
    """Download a single Tuneps attachment."""
    filename = safe_filename(str(file_info.get("fileNm", "document.bin")))
    noderef = file_info.get("bidAttNodeRef")
    if not noderef:
        print(f"  Skipped {filename} - missing bidAttNodeRef")
        return None

    url = f"{BASE}/ged/document/downloadFile?noderef={quote(str(noderef))}&fileName={quote(filename)}"
    response = requests.get(url, headers=headers, timeout=120, verify=False)

    if response.status_code == 401:
        print("Token expired or unauthorized. Run capture_tuneps_credentials.py again.")
        sys.exit(1)

    if response.status_code == 200:
        output_path = tender_dir / filename
        output_path.write_bytes(response.content)
        size_kb = len(response.content) // 1024
        print(f"  {filename} downloaded ({size_kb} KB)")
        return output_path

    print(f"  Failed to download {filename} - status {response.status_code}")
    return None


def download_tender_documents(bid_no: str, creds: dict[str, str]) -> None:
    """Download all documents for a given tender number."""
    if not BID_NO_RE.match(bid_no):
        print(f"Invalid tender ID skipped: {bid_no}")
        return

    headers = get_headers(creds)
    print(f"\nProcessing tender: {bid_no}")

    tender_dir = DOCUMENTS_DIR / bid_no
    tender_dir.mkdir(parents=True, exist_ok=True)

    files = get_file_list(bid_no, headers)
    if not files:
        print(f"No files found for tender {bid_no}")
        return

    print(f"{len(files)} file(s) found")
    for file_info in files:
        download_file(file_info, tender_dir, headers)

    print(f"Done - files saved to {tender_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download Tuneps RFP documents for explicit tender IDs only."
    )
    parser.add_argument("bid_no", nargs="+", help="Tender ID(s), e.g. 20260600248")
    args = parser.parse_args()

    print("TUNEPS - RFP document downloader")
    print("Downloads only the tender ID(s) provided on the command line.")
    print()

    creds = load_credentials()
    for bid_no in args.bid_no:
        download_tender_documents(bid_no.strip(), creds)

    print()
    print("All requested downloads completed.")
    print(f"Files saved to: {DOCUMENTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
