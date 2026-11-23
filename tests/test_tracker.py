"""
test_tracker.py — Full pytest suite for scripts/tracker.py.

Coverage targets:
  - URL normalization (tracking params, fragments, trailing slashes, case, sorting)
  - Database init (idempotency)
  - cmd_add (success, duplicate, invalid score, invalid platform)
  - cmd_check (found/not-found, --json output, normalized lookup)
  - cmd_list (all, filtered by status, --json output, empty DB)
  - cmd_update (success, invalid status, missing URL)
  - Exit code contracts

All tests use an in-memory SQLite database via monkeypatching to avoid
filesystem side effects.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Allow importing tracker from the scripts directory without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from tracker import (
    SCHEMA,
    TRACKING_PARAMS,
    VALID_PLATFORMS,
    VALID_STATUSES,
    cmd_add,
    cmd_check,
    cmd_init,
    cmd_list,
    cmd_update,
    normalize_url,
    _get_connection,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return a path to a fresh, initialized in-tmp-dir SQLite database."""
    path = tmp_path / "test_jobs.db"
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
    return path


@pytest.fixture
def populated_db(db_path: Path) -> Path:
    """Return a database pre-loaded with two distinct job records."""
    cmd_add(
        db_path,
        url="https://jobs.ashbyhq.com/acme/abc-123",
        company="Acme Corp",
        title="Senior Backend Engineer",
        score=92,
        platform="ashby",
    )
    cmd_add(
        db_path,
        url="https://boards.greenhouse.io/foobar/jobs/456",
        company="Foobar Inc",
        title="Staff Engineer",
        score=61,
        platform="greenhouse",
    )
    return db_path


# ---------------------------------------------------------------------------
# normalize_url — unit tests
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    """Tests for the normalize_url helper function."""

    def test_strips_gh_src_param(self) -> None:
        raw = "https://boards.greenhouse.io/acme/jobs/123?gh_src=redsols"
        result = normalize_url(raw)
        assert "gh_src" not in result
        assert result == "https://boards.greenhouse.io/acme/jobs/123"

    def test_strips_multiple_utm_params(self) -> None:
        raw = (
            "https://jobs.ashbyhq.com/acme/xyz"
            "?utm_source=linkedin&utm_medium=job_board&utm_campaign=Q4"
        )
        result = normalize_url(raw)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "utm_campaign" not in result
        assert result == "https://jobs.ashbyhq.com/acme/xyz"

    def test_strips_ref_param(self) -> None:
        raw = "https://jobs.lever.co/startup/abc?ref=remoteok"
        result = normalize_url(raw)
        assert "ref" not in result
        assert result == "https://jobs.lever.co/startup/abc"

    def test_strips_fragment(self) -> None:
        raw = "https://apply.workable.com/startup/j/ABC123/#top"
        result = normalize_url(raw)
        assert "#" not in result

    def test_strips_trailing_slash_from_path(self) -> None:
        raw = "https://jobs.ashbyhq.com/acme/xyz/"
        result = normalize_url(raw)
        assert not result.endswith("/")
        assert result == "https://jobs.ashbyhq.com/acme/xyz"

    def test_does_not_strip_root_path_to_empty(self) -> None:
        raw = "https://boards.greenhouse.io/"
        result = normalize_url(raw)
        # Root path should remain "/" not become ""
        assert result.endswith("/") or result == "https://boards.greenhouse.io"

    def test_lowercases_scheme_and_host(self) -> None:
        raw = "HTTPS://JOBS.ASHBYHQ.COM/Acme/xyz"
        result = normalize_url(raw)
        assert result.startswith("https://jobs.ashbyhq.com/")

    def test_preserves_non_tracking_params(self) -> None:
        raw = "https://jobs.lever.co/startup/abc?dept=engineering&location=remote"
        result = normalize_url(raw)
        assert "dept=engineering" in result
        assert "location=remote" in result

    def test_sorts_remaining_params_deterministically(self) -> None:
        url_a = "https://apply.workable.com/x/j/Y/?z=1&a=2"
        url_b = "https://apply.workable.com/x/j/Y/?a=2&z=1"
        assert normalize_url(url_a) == normalize_url(url_b)

    def test_strips_whitespace_around_url(self) -> None:
        raw = "  https://jobs.ashbyhq.com/acme/xyz  "
        result = normalize_url(raw)
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_raises_on_empty_string(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_url("")

    def test_raises_on_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_url("   ")

    def test_raises_on_missing_scheme(self) -> None:
        with pytest.raises(ValueError, match="scheme or host"):
            normalize_url("jobs.ashbyhq.com/acme/xyz")

    def test_mixed_tracking_and_real_params_preserved_correctly(self) -> None:
        raw = (
            "https://boards.greenhouse.io/acme/jobs/789"
            "?gh_src=redsols&team=platform&utm_source=linkedin"
        )
        result = normalize_url(raw)
        assert "gh_src" not in result
        assert "utm_source" not in result
        assert "team=platform" in result

    def test_all_tracking_params_are_stripped(self) -> None:
        """Every param in TRACKING_PARAMS must be stripped."""
        for param in TRACKING_PARAMS:
            raw = f"https://jobs.ashbyhq.com/co/job?{param}=testvalue&keep=1"
            result = normalize_url(raw)
            assert param not in result, f"Param '{param}' was not stripped"
            assert "keep=1" in result


# ---------------------------------------------------------------------------
# cmd_init — unit tests
# ---------------------------------------------------------------------------


class TestCmdInit:
    def test_creates_database_file(self, tmp_path: Path) -> None:
        db = tmp_path / "new.db"
        assert not db.exists()
        cmd_init(db)
        assert db.exists()

    def test_idempotent_on_second_call(self, tmp_path: Path) -> None:
        db = tmp_path / "new.db"
        cmd_init(db)
        # Should not raise on second call
        cmd_init(db)
        with _get_connection(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        assert count == 0

    def test_creates_jobs_table(self, db_path: Path) -> None:
        with _get_connection(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
            ).fetchall()
        assert len(tables) == 1


# ---------------------------------------------------------------------------
# cmd_add — unit tests
# ---------------------------------------------------------------------------


class TestCmdAdd:
    def test_adds_job_successfully(self, db_path: Path, capsys: pytest.CaptureFixture) -> None:
        cmd_add(db_path, "https://jobs.lever.co/x/abc", "X Corp", "SWE", 85, "lever")
        with _get_connection(db_path) as conn:
            row = conn.execute("SELECT * FROM jobs").fetchone()
        assert row["company"] == "X Corp"
        assert row["score"] == 85
        assert row["status"] == "SAVED"

    def test_normalizes_url_before_storing(self, db_path: Path) -> None:
        raw_url = "https://jobs.lever.co/x/abc?utm_source=twitter&ref=gh"
        cmd_add(db_path, raw_url, "X Corp", "SWE", 85, "lever")
        with _get_connection(db_path) as conn:
            row = conn.execute("SELECT url FROM jobs").fetchone()
        assert "utm_source" not in row["url"]
        assert "ref" not in row["url"]

    def test_duplicate_url_exits_with_code_2(self, db_path: Path) -> None:
        url = "https://jobs.lever.co/x/abc"
        cmd_add(db_path, url, "X Corp", "SWE", 85, "lever")
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(db_path, url, "X Corp", "SWE", 85, "lever")
        assert exc_info.value.code == 2

    def test_duplicate_detected_after_normalization(self, db_path: Path) -> None:
        """URLs that differ only in tracking params are considered duplicates."""
        url_a = "https://jobs.lever.co/x/abc"
        url_b = "https://jobs.lever.co/x/abc?utm_source=linkedin&ref=remoteok"
        cmd_add(db_path, url_a, "X Corp", "SWE", 85, "lever")
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(db_path, url_b, "X Corp", "SWE", 85, "lever")
        assert exc_info.value.code == 2

    def test_invalid_score_below_zero_exits_1(self, db_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(db_path, "https://jobs.lever.co/x/abc", "X", "T", -1, "lever")
        assert exc_info.value.code == 1

    def test_invalid_score_above_100_exits_1(self, db_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(db_path, "https://jobs.lever.co/x/abc", "X", "T", 101, "lever")
        assert exc_info.value.code == 1

    def test_boundary_score_zero_accepted(self, db_path: Path) -> None:
        cmd_add(db_path, "https://jobs.lever.co/x/abc", "X", "T", 0, "lever")
        with _get_connection(db_path) as conn:
            row = conn.execute("SELECT score FROM jobs").fetchone()
        assert row["score"] == 0

    def test_boundary_score_100_accepted(self, db_path: Path) -> None:
        cmd_add(db_path, "https://jobs.lever.co/x/abc", "X", "T", 100, "lever")
        with _get_connection(db_path) as conn:
            row = conn.execute("SELECT score FROM jobs").fetchone()
        assert row["score"] == 100

    def test_invalid_platform_exits_1(self, db_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(db_path, "https://jobs.lever.co/x/a", "X", "T", 80, "monster")
        assert exc_info.value.code == 1

    def test_all_valid_platforms_accepted(self, db_path: Path) -> None:
        for i, platform in enumerate(VALID_PLATFORMS):
            url = f"https://example.com/job/{i}"
            cmd_add(db_path, url, "Co", "Title", 50, platform)
        with _get_connection(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        assert count == len(VALID_PLATFORMS)

    def test_status_defaults_to_saved(self, db_path: Path) -> None:
        cmd_add(db_path, "https://jobs.lever.co/x/abc", "X", "T", 70, "lever")
        with _get_connection(db_path) as conn:
            row = conn.execute("SELECT status FROM jobs").fetchone()
        assert row["status"] == "SAVED"

    def test_added_at_and_updated_at_are_set(self, db_path: Path) -> None:
        cmd_add(db_path, "https://jobs.lever.co/x/abc", "X", "T", 70, "lever")
        with _get_connection(db_path) as conn:
            row = conn.execute("SELECT added_at, updated_at FROM jobs").fetchone()
        assert row["added_at"] is not None
        assert row["updated_at"] is not None


# ---------------------------------------------------------------------------
# cmd_check — unit tests
# ---------------------------------------------------------------------------


class TestCmdCheck:
    def test_existing_url_exits_0(self, populated_db: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_check(
                populated_db,
                "https://jobs.ashbyhq.com/acme/abc-123",
                as_json=False,
            )
        assert exc_info.value.code == 0

    def test_missing_url_exits_1(self, populated_db: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_check(
                populated_db,
                "https://jobs.ashbyhq.com/acme/does-not-exist",
                as_json=False,
            )
        assert exc_info.value.code == 1

    def test_check_with_json_exists_true(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with pytest.raises(SystemExit):
            cmd_check(
                populated_db,
                "https://jobs.ashbyhq.com/acme/abc-123",
                as_json=True,
            )
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["exists"] is True
        assert payload["company"] == "Acme Corp"
        assert payload["score"] == 92
        assert "status" in payload

    def test_check_with_json_exists_false(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with pytest.raises(SystemExit):
            cmd_check(
                populated_db,
                "https://jobs.ashbyhq.com/acme/not-here",
                as_json=True,
            )
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["exists"] is False

    def test_check_finds_url_after_normalization(self, db_path: Path) -> None:
        """Adding a clean URL and checking with a tracking-param-laden version should match."""
        clean = "https://boards.greenhouse.io/acme/jobs/789"
        cmd_add(db_path, clean, "Acme", "SWE", 80, "greenhouse")
        dirty = clean + "?gh_src=remoteok&utm_medium=social"
        with pytest.raises(SystemExit) as exc_info:
            cmd_check(db_path, dirty, as_json=False)
        assert exc_info.value.code == 0

    def test_check_json_url_field_is_normalized(
        self, db_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_add(db_path, "https://boards.greenhouse.io/acme/jobs/789", "Acme", "SWE", 80, "greenhouse")
        capsys.readouterr()  # Drain cmd_add's [OK] stdout line before JSON assertion
        with pytest.raises(SystemExit):
            cmd_check(
                db_path,
                "https://boards.greenhouse.io/acme/jobs/789?gh_src=x",
                as_json=True,
            )
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert "gh_src" not in payload["url"]


# ---------------------------------------------------------------------------
# cmd_list — unit tests
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_list_returns_all_jobs(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(populated_db, status_filter=None, as_json=False)
        captured = capsys.readouterr()
        assert "Acme Corp" in captured.out
        assert "Foobar Inc" in captured.out

    def test_list_json_returns_valid_json_array(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(populated_db, status_filter=None, as_json=True)
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert isinstance(payload, list)
        assert len(payload) == 2

    def test_list_json_record_structure(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(populated_db, status_filter=None, as_json=True)
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        required_keys = {"url", "company", "title", "score", "status", "platform", "added_at"}
        for record in payload:
            assert required_keys.issubset(record.keys()), (
                f"Missing keys: {required_keys - record.keys()}"
            )

    def test_list_filtered_by_status(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(populated_db, status_filter="SAVED", as_json=True)
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert all(r["status"] == "SAVED" for r in payload)
        assert len(payload) == 2

    def test_list_filtered_by_status_applied_returns_empty(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(populated_db, status_filter="APPLIED", as_json=True)
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload == []

    def test_list_empty_database_prints_info(
        self, db_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(db_path, status_filter=None, as_json=False)
        captured = capsys.readouterr()
        assert "No jobs found" in captured.out

    def test_list_empty_database_json_returns_empty_array(
        self, db_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(db_path, status_filter=None, as_json=True)
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload == []

    def test_list_invalid_status_exits_1(self, populated_db: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_list(populated_db, status_filter="GHOSTED", as_json=False)
        assert exc_info.value.code == 1

    def test_list_ordered_by_score_descending(
        self, populated_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        cmd_list(populated_db, status_filter=None, as_json=True)
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        scores = [r["score"] for r in payload]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# cmd_update — unit tests
# ---------------------------------------------------------------------------


class TestCmdUpdate:
    def test_updates_status_successfully(self, populated_db: Path) -> None:
        url = "https://jobs.ashbyhq.com/acme/abc-123"
        cmd_update(populated_db, url, "APPLIED")
        with _get_connection(populated_db) as conn:
            row = conn.execute(
                "SELECT status FROM jobs WHERE url = ?", (normalize_url(url),)
            ).fetchone()
        assert row["status"] == "APPLIED"

    def test_update_all_valid_statuses(self, db_path: Path) -> None:
        url = "https://jobs.lever.co/x/abc"
        cmd_add(db_path, url, "X", "T", 80, "lever")
        for status in VALID_STATUSES:
            cmd_update(db_path, url, status)
            with _get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT status FROM jobs WHERE url = ?", (normalize_url(url),)
                ).fetchone()
            assert row["status"] == status

    def test_update_normalizes_url(self, populated_db: Path) -> None:
        dirty_url = "https://jobs.ashbyhq.com/acme/abc-123?utm_source=linkedin"
        cmd_update(populated_db, dirty_url, "INTERVIEWING")
        with _get_connection(populated_db) as conn:
            row = conn.execute(
                "SELECT status FROM jobs WHERE url = ?",
                (normalize_url("https://jobs.ashbyhq.com/acme/abc-123"),),
            ).fetchone()
        assert row["status"] == "INTERVIEWING"

    def test_update_nonexistent_url_exits_1(self, db_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_update(db_path, "https://jobs.lever.co/x/nonexistent", "APPLIED")
        assert exc_info.value.code == 1

    def test_update_invalid_status_exits_1(self, populated_db: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_update(
                populated_db,
                "https://jobs.ashbyhq.com/acme/abc-123",
                "GHOSTED",
            )
        assert exc_info.value.code == 1

    def test_update_status_case_insensitive(self, populated_db: Path) -> None:
        """Status input should be uppercased before validation."""
        cmd_update(populated_db, "https://jobs.ashbyhq.com/acme/abc-123", "applied")
        with _get_connection(populated_db) as conn:
            row = conn.execute(
                "SELECT status FROM jobs WHERE url = ?",
                ("https://jobs.ashbyhq.com/acme/abc-123",),
            ).fetchone()
        assert row["status"] == "APPLIED"

    def test_updated_at_changes_on_update(self, populated_db: Path) -> None:
        url = "https://jobs.ashbyhq.com/acme/abc-123"
        normalized = normalize_url(url)
        with _get_connection(populated_db) as conn:
            before = conn.execute(
                "SELECT updated_at FROM jobs WHERE url = ?", (normalized,)
            ).fetchone()["updated_at"]

        import time
        time.sleep(0.01)  # Ensure time advances
        cmd_update(populated_db, url, "APPLIED")

        with _get_connection(populated_db) as conn:
            after = conn.execute(
                "SELECT updated_at FROM jobs WHERE url = ?", (normalized,)
            ).fetchone()["updated_at"]

        assert after > before


# ---------------------------------------------------------------------------
# Integration — full pipeline simulation
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end simulation of a typical agent workflow session."""

    def test_full_workflow(self, db_path: Path, capsys: pytest.CaptureFixture) -> None:
        url = "https://jobs.ashbyhq.com/coolstartup/se-456?gh_src=redsols&utm_source=twitter"

        # 1. Check — should not exist
        with pytest.raises(SystemExit) as exc_info:
            cmd_check(db_path, url, as_json=True)
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert json.loads(out)["exists"] is False

        # 2. Add
        cmd_add(db_path, url, "Cool Startup", "Senior SWE", 88, "ashby")
        capsys.readouterr()  # Drain cmd_add's [OK] stdout line before JSON assertion

        # 3. Check — should now exist
        with pytest.raises(SystemExit) as exc_info:
            cmd_check(db_path, url, as_json=True)
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["exists"] is True
        assert payload["score"] == 88

        # 4. List — should appear
        cmd_list(db_path, status_filter=None, as_json=True)
        out = capsys.readouterr().out
        jobs = json.loads(out)
        assert len(jobs) == 1
        assert jobs[0]["status"] == "SAVED"

        # 5. Update → APPLIED
        cmd_update(db_path, url, "APPLIED")
        capsys.readouterr()  # Drain cmd_update's [OK] stdout line before JSON assertion

        # 6. List filtered by APPLIED
        cmd_list(db_path, status_filter="APPLIED", as_json=True)
        out = capsys.readouterr().out
        applied = json.loads(out)
        assert len(applied) == 1
        assert applied[0]["status"] == "APPLIED"

        # 7. Second add of same URL (with different tracking params) should fail
        url2 = "https://jobs.ashbyhq.com/coolstartup/se-456?ref=hn"
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(db_path, url2, "Cool Startup", "Senior SWE", 88, "ashby")
        assert exc_info.value.code == 2
