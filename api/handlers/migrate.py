"""One-shot migration Lambda handler.

Runs inside the VPC so it can reach Aurora in the isolated subnets.
Invoke manually via the AWS CLI::

    aws lambda invoke --function-name mnemora-migrate-dev /dev/stdout

The handler reads SQL files from ``lib/migrations/``, checks the
``_migrations`` tracking table, and applies any pending migrations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "lib" / "migrations"


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run pending Aurora database migrations.

    Args:
        event: Lambda event payload (ignored).
        context: Lambda execution context.

    Returns:
        Dict with statusCode and body describing what was applied.
    """
    import psycopg  # noqa: PLC0415
    from psycopg.rows import dict_row  # noqa: PLC0415

    from lib.aurora import _build_conninfo  # noqa: PLC0415

    logger.info("Migration handler invoked")

    # Direct connection with autocommit — migrations manage their own txns.
    conninfo = _build_conninfo()
    conn = psycopg.connect(conninfo, row_factory=dict_row, autocommit=True)

    try:
        # Discover migration files
        migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        logger.info(
            "Found %d migration file(s): %s",
            len(migration_files),
            ", ".join(f.name for f in migration_files),
        )

        if not migration_files:
            return _response(
                200, {"applied": [], "message": "No migration files found"}
            )

        # Check which migrations have already been applied
        applied = _get_applied(conn)
        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            return _response(
                200, {"applied": [], "message": "All migrations up to date"}
            )

        logger.info(
            "%d pending: %s",
            len(pending),
            ", ".join(f.name for f in pending),
        )

        # Apply each pending migration
        applied_names: list[str] = []
        for filepath in pending:
            sql = filepath.read_text(encoding="utf-8")
            logger.info("Applying: %s (%d bytes)", filepath.name, len(sql))

            with conn.cursor() as cur:
                cur.execute(sql)

            # Record in tracking table
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO _migrations (filename) VALUES (%s)",
                    (filepath.name,),
                )

            applied_names.append(filepath.name)
            logger.info("Applied: %s", filepath.name)

        return _response(
            200,
            {
                "applied": applied_names,
                "message": f"Applied {len(applied_names)} migration(s)",
            },
        )

    except Exception as exc:
        logger.exception("Migration failed")
        return _response(500, {"error": str(exc)})

    finally:
        conn.close()


def _get_applied(conn: Any) -> set[str]:
    """Return set of already-applied migration filenames."""
    with conn.cursor() as cur:
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


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build a simple Lambda response."""
    return {
        "statusCode": status,
        "body": json.dumps(body),
    }
