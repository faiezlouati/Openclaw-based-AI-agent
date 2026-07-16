#!/usr/bin/env python3
"""Capture Tuneps browser session credentials after a manual Chrome login.

Usage:
  1. Log in to https://www.tuneps.tn in Chrome using the Tuneps key/account.
  2. Run: python3 scripts/capture_tuneps_credentials.py
  3. Credentials are saved to ~/.tuneps_data/credentials.json

The saved credentials are used only when the user explicitly asks to download RFP
documents for a tender ID.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import time
from pathlib import Path
from typing import Any

import browser_cookie3
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_ROOT = Path(os.environ.get("TUNEPS_DATA_ROOT", "~/.tuneps_data")).expanduser()
CREDENTIALS_FILE = Path(
    os.environ.get("TUNEPS_CREDENTIALS_FILE", DATA_ROOT / "credentials.json")
).expanduser()
BASE = "https://www.tuneps.tn/api2"
DEFAULT_TEST_BID_NO = os.environ.get("TUNEPS_TEST_BID_NO", "20260600248")


def get_cookie() -> str | None:
    """Read Tuneps session cookie from Chrome after manual login."""
    cookies = browser_cookie3.chrome(domain_name=".tuneps.tn")
    for cookie in cookies:
        if cookie.name == "cookiesession1":
            return cookie.value
    return None


def get_jwt(session_cookie: str, test_bid_no: str) -> str | None:
    """Make a small Tuneps API call and extract auth token if returned."""
    headers = {
        "Cookie": f"cookiesession1={session_cookie}",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
    }
    response = requests.get(
        f"{BASE}/ged//vAttachFile/getByBidNo",
        params={"bidNo": test_bid_no},
        headers=headers,
        timeout=30,
        verify=False,
    )
    response.raise_for_status()

    jwt = response.headers.get("Authorization") or response.headers.get("X-Auth-Token")
    if jwt and jwt.startswith("Bearer "):
        jwt = jwt.replace("Bearer ", "", 1).strip()
    return jwt.strip() if jwt else None


def save_credentials(jwt: str, cookie: str) -> dict[str, Any]:
    """Save credentials with a conservative 24-hour expiry timestamp."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    credentials = {
        "jwt": jwt,
        "cookie": cookie,
        "captured": time.strftime("%Y-%m-%d %H:%M:%S"),
        "expires": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 86400)),
    }
    with CREDENTIALS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(credentials, handle, indent=2)
        handle.write("\n")

    # Owner read/write only where supported.
    try:
        CREDENTIALS_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    return credentials


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture Tuneps credentials from Chrome after manual login."
    )
    parser.add_argument(
        "--test-bid-no",
        default=DEFAULT_TEST_BID_NO,
        help="Tender ID used for the small token-check API call.",
    )
    args = parser.parse_args()

    print("Make sure you are logged in on tuneps.tn in Chrome before continuing.")
    print("This script only captures credentials; it does not download documents.")
    print()

    cookie = get_cookie()
    if not cookie:
        print("No Tuneps session cookie found. Please log in to tuneps.tn in Chrome first.")
        return 1
    print(f"Cookie found: {cookie[:10]}...")

    try:
        jwt = get_jwt(cookie, args.test_bid_no)
    except Exception as exc:  # noqa: BLE001 - CLI should show actionable error
        print(f"JWT was not found automatically because the test request failed: {exc}")
        jwt = None

    if not jwt:
        print("JWT not found automatically.")
        jwt = input("Paste your Bearer token here: ").strip()
        if jwt.startswith("Bearer "):
            jwt = jwt.replace("Bearer ", "", 1).strip()

    if not jwt:
        print("Could not capture JWT. Exiting.")
        return 1
    print(f"JWT found: {jwt[:30]}...")

    creds = save_credentials(jwt, cookie)
    print()
    print(f"Credentials saved to {CREDENTIALS_FILE}")
    print(f"Valid until: {creds['expires']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
