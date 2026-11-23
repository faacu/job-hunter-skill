#!/usr/bin/env python3
"""
tracker.py — Local SQLite job application tracker for the job-hunter-skill.

Commands:
    init    Create the SQLite database and schema.
    add     Add a new job record.
    check   Check if a URL already exists in the tracker.
    list    List all tracked jobs, optionally filtered by status.
    update  Update the status of an existing job.

Usage:
    python tracker.py init
    python tracker.py add --url URL --company NAME --title TITLE --score N --platform PLATFORM
    python tracker.py check --url URL [--json]
    python tracker.py list [--status STATUS] [--json]
    python tracker.py update --url URL --status STATUS
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Final
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH: Final[Path] = Path(__file__).parent.parent / "jobs.db"

VALID_STATUSES: Final[frozenset[str]] = frozenset(
    {"SAVED", "APPLIED", "INTERVIEWING", "REJECTED"}
)

VALID_PLATFORMS: Final[frozenset[str]] = frozenset(
    {"greenhouse", "ashby", "lever", "workable", "other"}
)

# Query parameters to strip during URL normalization.
# These are tracking/referral parameters that do not affect job identity.
TRACKING_PARAMS: Final[frozenset[str]] = frozenset(
    {
        "gh_src",
        "gh_jid",
        "ref",
        "referral",
        "source",
        "src",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
    }
)

SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL UNIQUE,
    company     TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    platform    TEXT    NOT NULL DEFAULT 'other',
    score       INTEGER NOT NULL CHECK(score >= 0 AND score <= 100),
    status      TEXT    NOT NULL DEFAULT 'SAVED'
                        CHECK(status IN ('SAVED', 'APPLIED', 'INTERVIEWING', 'REJECTED')),
    added_at    TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# URL Normalization
# ---------------------------------------------------------------------------


def normalize_url(url: str) -> str:
    """
    Normalize a job posting URL for consistent deduplication.

    Steps applied (in order):
      1. Strip leading/trailing whitespace.
      2. Force scheme to lowercase.
      3. Force hostname to lowercase.
      4. Remove URL fragment (#...).
      5. Strip tracking query parameters defined in TRACKING_PARAMS.
      6. Re-sort remaining query parameters for deterministic ordering.
      7. Remove trailing slash from the path component.

    Args:
        url: Raw URL string as scraped from an ATS platform.

    Returns:
        A canonical, normalized URL string suitable for use as a unique key.

    Raises:
        ValueError: If the URL is empty or missing a valid scheme and host.
    """
    url = url.strip()
    if not url:
        raise ValueError("URL must not be empty.")

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL — missing scheme or host: {url!r}")

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"

    # Filter out tracking query parameters; sort the rest for determinism.
    filtered_params = sorted(
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    )
    query = urlencode(filtered_params)

    # Fragment is always dropped — it is client-side only and irrelevant to identity.
    normalized = urlunparse((scheme, netloc, path, parsed.params, query, ""))
    return normalized


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _now_iso() -> str:
    """Return the current UTC datetime as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def cmd_init(db_path: Path) -> None:
    """
    Initialize the SQLite database and create the jobs table if it does not
    already exist. Safe to run multiple times (idempotent).

    Args:
        db_path: Path to the SQLite database file.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
    print(f"[OK] Database initialized at: {db_path}")


def cmd_add(
    db_path: Path,
    url: str,
    company: str,
    title: str,
    score: int,
    platform: str,
) -> None:
    """
    Add a new job posting to the tracker with status SAVED.

    The URL is normalized before storage to prevent duplicates caused by
    tracking parameters or trailing slashes.

    Args:
        db_path:  Path to the SQLite database file.
        url:      Raw job posting URL.
        company:  Company name.
        title:    Job title.
        score:    Match score (0–100).
        platform: ATS platform identifier.

    Raises:
        SystemExit: On validation failure or if the URL already exists.
    """
    if not 0 <= score <= 100:
        print(f"[ERROR] Score must be between 0 and 100, got: {score}", file=sys.stderr)
        sys.exit(1)

    platform = platform.lower()
    if platform not in VALID_PLATFORMS:
        print(
            f"[ERROR] Invalid platform '{platform}'. "
            f"Valid options: {sorted(VALID_PLATFORMS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        canonical_url = normalize_url(url)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    now = _now_iso()
    try:
        with _get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO jobs (url, company, title, platform, score, status, added_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'SAVED', ?, ?)
                """,
                (canonical_url, company.strip(), title.strip(), platform, score, now, now),
            )
        print(f"[OK] Added: {title} at {company} (score={score}, url={canonical_url})")
    except sqlite3.IntegrityError:
        print(f"[SKIP] URL already tracked: {canonical_url}", file=sys.stderr)
        sys.exit(2)


def cmd_check(db_path: Path, url: str, as_json: bool) -> None:
    """
    Check whether a URL is already present in the tracker.

    Exits with code 0 when the URL exists, code 1 when it does not.
    When --json is specified, prints a machine-readable JSON object to stdout.

    Args:
        db_path:  Path to the SQLite database file.
        url:      Raw URL to look up.
        as_json:  If True, output JSON instead of human-readable text.
    """
    try:
        canonical_url = normalize_url(url)
    except ValueError as exc:
        if as_json:
            print(json.dumps({"error": str(exc), "exists": False}))
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    with _get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, company, title, score, status, added_at FROM jobs WHERE url = ?",
            (canonical_url,),
        ).fetchone()

    if row:
        if as_json:
            print(
                json.dumps(
                    {
                        "exists": True,
                        "url": canonical_url,
                        "company": row["company"],
                        "title": row["title"],
                        "score": row["score"],
                        "status": row["status"],
                        "added_at": row["added_at"],
                    }
                )
            )
        else:
            print(
                f"[EXISTS] {row['title']} at {row['company']} "
                f"(status={row['status']}, score={row['score']})"
            )
        sys.exit(0)
    else:
        if as_json:
            print(json.dumps({"exists": False, "url": canonical_url}))
        else:
            print(f"[NEW] URL not tracked: {canonical_url}")
        sys.exit(1)


def cmd_list(db_path: Path, status_filter: str | None, as_json: bool) -> None:
    """
    List all tracked jobs, optionally filtered by application status.

    Args:
        db_path:       Path to the SQLite database file.
        status_filter: Optional status string to filter results.
        as_json:       If True, output a JSON array instead of a table.
    """
    if status_filter:
        status_filter = status_filter.upper()
        if status_filter not in VALID_STATUSES:
            print(
                f"[ERROR] Invalid status '{status_filter}'. "
                f"Valid options: {sorted(VALID_STATUSES)}",
                file=sys.stderr,
            )
            sys.exit(1)

    with _get_connection(db_path) as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC, added_at DESC",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY score DESC, added_at DESC"
            ).fetchall()

    records = [dict(row) for row in rows]

    if as_json:
        print(json.dumps(records, indent=2))
        return

    if not records:
        print("[INFO] No jobs found.")
        return

    # Human-readable table
    header = f"{'#':<4} {'Score':<6} {'Status':<14} {'Company':<24} {'Title':<36} {'Platform':<12}"
    separator = "-" * len(header)
    print(header)
    print(separator)
    for i, job in enumerate(records, start=1):
        print(
            f"{i:<4} {job['score']:<6} {job['status']:<14} "
            f"{job['company'][:22]:<24} {job['title'][:34]:<36} "
            f"{job['platform']:<12}"
        )
    print(separator)
    print(f"Total: {len(records)} job(s)")


def cmd_update(db_path: Path, url: str, status: str) -> None:
    """
    Update the application status of an existing job record.

    Args:
        db_path: Path to the SQLite database file.
        url:     Raw URL of the job to update.
        status:  New status string (must be in VALID_STATUSES).

    Raises:
        SystemExit: If the URL is not found or status is invalid.
    """
    status = status.upper()
    if status not in VALID_STATUSES:
        print(
            f"[ERROR] Invalid status '{status}'. Valid options: {sorted(VALID_STATUSES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        canonical_url = normalize_url(url)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    with _get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE url = ?",
            (status, _now_iso(), canonical_url),
        )
        if cursor.rowcount == 0:
            print(f"[ERROR] No job found with URL: {canonical_url}", file=sys.stderr)
            sys.exit(1)

    print(f"[OK] Updated status to {status} for: {canonical_url}")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="tracker.py",
        description="Local SQLite job application tracker for job-hunter-skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        metavar="PATH",
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- init ---
    subparsers.add_parser("init", help="Initialize the database and schema.")

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Add a new job record.")
    add_parser.add_argument("--url", required=True, help="Job posting URL.")
    add_parser.add_argument("--company", required=True, help="Company name.")
    add_parser.add_argument("--title", required=True, help="Job title.")
    add_parser.add_argument(
        "--score", required=True, type=int, help="Match score (0–100)."
    )
    add_parser.add_argument(
        "--platform",
        required=True,
        choices=sorted(VALID_PLATFORMS),
        help="ATS platform.",
    )

    # --- check ---
    check_parser = subparsers.add_parser(
        "check", help="Check if a URL is already tracked."
    )
    check_parser.add_argument("--url", required=True, help="Job posting URL to check.")
    check_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output machine-readable JSON.",
    )

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List tracked jobs.")
    list_parser.add_argument(
        "--status",
        choices=sorted(VALID_STATUSES),
        default=None,
        help="Filter by application status.",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output machine-readable JSON array.",
    )

    # --- update ---
    update_parser = subparsers.add_parser(
        "update", help="Update the status of a tracked job."
    )
    update_parser.add_argument("--url", required=True, help="Job posting URL.")
    update_parser.add_argument(
        "--status",
        required=True,
        choices=sorted(VALID_STATUSES),
        help="New application status.",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and dispatch to the appropriate command handler."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    db_path: Path = args.db

    match args.command:
        case "init":
            cmd_init(db_path)
        case "add":
            cmd_add(
                db_path,
                url=args.url,
                company=args.company,
                title=args.title,
                score=args.score,
                platform=args.platform,
            )
        case "check":
            cmd_check(db_path, url=args.url, as_json=args.as_json)
        case "list":
            cmd_list(db_path, status_filter=args.status, as_json=args.as_json)
        case "update":
            cmd_update(db_path, url=args.url, status=args.status)
        case _:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
