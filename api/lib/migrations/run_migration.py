"""Migration runner for Mnemora Aurora database.

Reads numbered SQL migration files from this directory, checks the
``_migrations`` table for already-applied migrations, and executes
new ones in sorted order.

Usage:
    cd api
    python3 -m lib.migrations.run_migration
    python3 -m lib.migrations.run_migration --dry-run

The runner uses a direct connection (not the pool) because migrations
require superuser-like access for DDL statements such as CREATE EXTENSION.
Each migration file is expected to manage its own transaction boundaries
(BEGIN/COMMIT) so the runner connects with autocommit=True.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Directory containing this file and the .sql migration files.
_MIGRATIONS_DIR = Path(__file__).parent


def _get_migration_files() -> list[Path]:
    """Discover SQL migration files sorted by filename prefix.

    Returns:
        Sorted list of Path objects for each ``*.sql`` file in the
        migrations directory, ordered lexicographically (e.g. 001, 002, ...).
    """
    files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    return files


def _get_applied_migrations(conn: Any) -> set[str]:
    """Fetch the set of already-applied migration filenames.

    If the ``_migrations`` table does not exist yet (first run), returns
    an empty set rather than raising an error.

    Args:
        conn: An active psycopg connection with autocommit=True.

    Returns:
        Set of migration filenames that have already been applied.
    """
    with conn.cursor() as cur:
        # Check whether the _migrations table exists before querying it.
        cur.execute(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables "
            "  WHERE table_schema = 'public' AND table_name = '_migrations'"
            ")"
        )
        row = cur.fetchone()
        if row is None or not row.get("exists", False):
            return set()

        cur.execute("SELECT filename FROM _migrations ORDER BY id")
        return {r["filename"] for r in cur.fetchall()}


def _apply_migration(conn: Any, filepath: Path) -> None:
    """Execute a single migration file and record it in ``_migrations``.

    The SQL file is expected to contain its own BEGIN/COMMIT block.  After
    execution, the filename is inserted into the ``_migrations`` tracking
    table so it will not be re-applied.

    Args:
        conn: An active psycopg connection with autocommit=True.
        filepath: Path to the ``.sql`` migration file.

    Raises:
        psycopg.Error: On any SQL execution failure.
    """
    sql = filepath.read_text(encoding="utf-8")
    filename = filepath.name

    logger.info("Applying migration: %s", filename)
    with conn.cursor() as cur:
        cur.execute(sql)

    # Record the migration — this runs outside the migration's own
    # transaction because the connection is in autocommit mode.
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO _migrations (filename) VALUES (%s)",
            (filename,),
        )
    logger.info("Migration applied successfully: %s", filename)


def run(*, dry_run: bool = False) -> int:
    """Execute all pending migrations.

    Args:
        dry_run: If True, list pending migrations without executing them.

    Returns:
        Number of migrations applied (or that would be applied in dry-run).
    """
    # Import here so the module can be imported in environments where
    # psycopg or boto3 are not installed (e.g., for static analysis).
    # get_direct_connection handles Secrets Manager + psycopg connect.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from lib.aurora import get_direct_connection  # noqa: PLC0415

    migration_files = _get_migration_files()
    if not migration_files:
        logger.info("No migration files found in %s", _MIGRATIONS_DIR)
        return 0

    logger.info(
        "Found %d migration file(s): %s",
        len(migration_files),
        ", ".join(f.name for f in migration_files),
    )

    conn = get_direct_connection()
    try:
        applied = _get_applied_migrations(conn)
        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            logger.info("All migrations are up to date. Nothing to apply.")
            return 0

        logger.info(
            "%d pending migration(s): %s",
            len(pending),
            ", ".join(f.name for f in pending),
        )

        if dry_run:
            logger.info("Dry run — no migrations were applied.")
            return len(pending)

        for filepath in pending:
            _apply_migration(conn, filepath)

        logger.info("Migration run complete. Applied %d migration(s).", len(pending))
        return len(pending)
    finally:
        conn.close()
        logger.info("Database connection closed.")


def main() -> None:
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run Mnemora Aurora database migrations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending migrations without executing them.",
    )
    args = parser.parse_args()

    applied_count = run(dry_run=args.dry_run)

    if args.dry_run:
        logger.info("Would apply %d migration(s).", applied_count)
    else:
        logger.info("Applied %d migration(s) total.", applied_count)


if __name__ == "__main__":
    main()
