"""Aurora Serverless v2 (pgvector) client wrapper for Mnemora semantic memory.

Provides connection pooling, RLS tenant context injection, and parameterized
query execution against an Aurora PostgreSQL 15.8 cluster with the pgvector
extension.

Connection credentials are fetched from AWS Secrets Manager and cached for
the lifetime of the Lambda container (module-level global).  The connection
pool is also lazily initialised at module level so that warm Lambda
invocations reuse existing connections.

Environment variables:
    AURORA_ENDPOINT   – Cluster writer endpoint (default: dev cluster).
    AURORA_PORT       – PostgreSQL port (default: 5432).
    AURORA_SECRET_ARN – Secrets Manager ARN for DB credentials (required).
    AURORA_DB_NAME    – Database name (default: mnemora).

Usage from a Lambda handler::

    from lib.aurora import get_connection, set_tenant_context

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, content FROM semantic_memory WHERE agent_id = %s",
                (agent_id,),
            )
            rows = cur.fetchall()
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level caches — survive across warm Lambda invocations.
# ---------------------------------------------------------------------------
_secret_cache: dict[str, Any] | None = None
_pool: Any | None = None  # psycopg_pool.ConnectionPool (lazy import)

# ---------------------------------------------------------------------------
# Environment configuration with sensible defaults from the deployed stack.
# ---------------------------------------------------------------------------
_AURORA_ENDPOINT = os.environ.get("AURORA_HOST", os.environ.get("AURORA_ENDPOINT", ""))
_AURORA_PORT = os.environ.get("AURORA_PORT", "5432")
_AURORA_SECRET_ARN = os.environ.get("AURORA_SECRET_ARN", "")
_AURORA_DB_NAME = os.environ.get("AURORA_DB_NAME", "mnemora")


def _get_secret() -> dict[str, Any]:
    """Fetch and cache Aurora credentials from AWS Secrets Manager.

    Credentials are cached at module level so that subsequent calls within
    the same Lambda container skip the Secrets Manager round-trip.

    Returns:
        Dict with at least ``username`` and ``password`` keys.

    Raises:
        RuntimeError: If AURORA_SECRET_ARN is not configured.
        botocore.exceptions.ClientError: On Secrets Manager API failures.
    """
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache

    if not _AURORA_SECRET_ARN:
        raise RuntimeError(
            "AURORA_SECRET_ARN environment variable is not set. "
            "Cannot retrieve database credentials."
        )

    import boto3  # noqa: PLC0415

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=_AURORA_SECRET_ARN)
    _secret_cache = json.loads(response["SecretString"])
    logger.info("Aurora credentials fetched from Secrets Manager")
    return _secret_cache


def _build_conninfo() -> str:
    """Build a libpq connection string from environment and secret.

    Returns:
        A PostgreSQL connection URI string.
    """
    secret = _get_secret()
    username = secret["username"]
    password = secret["password"]
    return (
        f"host={_AURORA_ENDPOINT} "
        f"port={_AURORA_PORT} "
        f"dbname={_AURORA_DB_NAME} "
        f"user={username} "
        f"password={password} "
        f"sslmode=require "
        f"connect_timeout=30"
    )


def _get_pool() -> Any:
    """Lazily initialise and return the module-level connection pool.

    The pool is created on first call and reused for the lifetime of the
    Lambda container.  Pool size is tuned for Lambda: min_size=1 keeps one
    connection warm, max_size=5 accommodates brief concurrency spikes during
    async handler patterns.

    Returns:
        A ``psycopg_pool.ConnectionPool`` instance.
    """
    global _pool
    if _pool is not None:
        return _pool

    from psycopg.rows import dict_row  # noqa: PLC0415
    from psycopg_pool import ConnectionPool  # noqa: PLC0415

    conninfo = _build_conninfo()

    _pool = ConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=5,
        timeout=30.0,
        kwargs={"row_factory": dict_row, "autocommit": False},
    )
    logger.info("Aurora connection pool initialised (min=1, max=5, timeout=5s)")
    return _pool


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    """Context manager that yields a connection from the pool.

    The connection is returned to the pool when the context exits.  On
    normal exit the transaction is committed; on exception it is rolled
    back.

    Yields:
        A ``psycopg.Connection`` configured with ``dict_row`` row factory.

    Raises:
        psycopg.OperationalError: On connection failure.
    """
    pool = _get_pool()
    with pool.connection() as conn:
        yield conn


def set_tenant_context(conn: Any, tenant_id: str) -> None:
    """Set the RLS tenant context on a connection.

    This MUST be called before any query on a multi-tenant table.  It sets
    the PostgreSQL session variable ``app.tenant_id`` which the RLS policy
    on ``semantic_memory`` evaluates via ``current_setting('app.tenant_id')``.

    Args:
        conn: An active psycopg connection.
        tenant_id: The tenant identifier derived from the API key authorizer.
    """
    with conn.cursor() as cur:
        # SET does not support parameterized queries in PostgreSQL.
        # Use set_config() instead — it accepts $1-style parameters safely.
        cur.execute(
            "SELECT set_config('app.tenant_id', %s, false)",
            (tenant_id,),
        )


def execute_query(
    query: str,
    params: tuple[Any, ...] | None = None,
    tenant_id: str | None = None,
    *,
    fetch: bool = True,
) -> list[dict[str, Any]]:
    """Execute a parameterized query with optional tenant context.

    This is a convenience wrapper that acquires a connection, sets the RLS
    tenant context (if provided), executes the query, and returns results
    as a list of dicts.

    Args:
        query: SQL query string with ``%s`` placeholders.
        params: Tuple of parameter values (never use string interpolation).
        tenant_id: If provided, ``SET app.tenant_id`` is called first.
        fetch: If True (default), fetch and return all result rows.
            Set to False for INSERT/UPDATE/DELETE with no RETURNING clause.

    Returns:
        List of dicts (one per row) when fetch=True, empty list otherwise.

    Raises:
        psycopg.Error: On any database error.
    """
    with get_connection() as conn:
        if tenant_id is not None:
            set_tenant_context(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch and cur.description is not None:
                return cur.fetchall()
    return []


def health_check() -> bool:
    """Verify Aurora connectivity by executing ``SELECT 1``.

    Returns:
        True if the database is reachable, False otherwise.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return result is not None
    except Exception:
        logger.exception("Aurora health check failed")
        return False


def close_pool() -> None:
    """Close the connection pool and release all connections.

    Call this during graceful shutdown or in test teardown.  After calling
    this, the next ``get_connection()`` call will create a fresh pool.
    """
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            logger.info("Aurora connection pool closed")
        except Exception:
            logger.exception("Error closing Aurora connection pool")
        finally:
            _pool = None


def get_direct_connection() -> Any:
    """Create a standalone connection outside the pool.

    Used by the migration runner which needs superuser-level access for
    DDL operations like ``CREATE EXTENSION``.  The caller is responsible
    for closing the returned connection.

    Returns:
        A ``psycopg.Connection`` with ``dict_row`` row factory and
        autocommit enabled (migrations manage their own transactions).

    Raises:
        psycopg.OperationalError: On connection failure.
    """
    import psycopg  # noqa: PLC0415
    from psycopg.rows import dict_row  # noqa: PLC0415

    conninfo = _build_conninfo()
    conn = psycopg.connect(conninfo, row_factory=dict_row, autocommit=True)
    logger.info("Direct Aurora connection established (outside pool)")
    return conn
