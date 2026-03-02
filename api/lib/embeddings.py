"""Bedrock Titan Text Embeddings v2 client for Mnemora semantic memory.

Generates 1024-dimensional float vectors via Amazon Bedrock's
``amazon.titan-embed-text-v2:0`` model.  The client is lazily initialised
at module level and reused across warm Lambda invocations.

Retry behaviour:
    3 retries with exponential backoff + random jitter (0–0.5 s).
    Base delays: 0.5 s → 1 s → 2 s (doubled each attempt).
    Retried exceptions: botocore ClientError, ReadTimeoutError.

Chunking:
    Text exceeding ~8 000 tokens (approximated as len(text) / 4 > 8000)
    is split into overlapping character windows before embedding.

Usage::

    from lib.embeddings import generate_embedding, generate_embeddings_chunked

    vector = generate_embedding("The agent remembered the user's name.")
    chunks = generate_embeddings_chunked(long_document)
"""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL_ID = "amazon.titan-embed-text-v2:0"
_DIMENSIONS = 1024

# Approximate tokens-per-character ratio (4 chars ≈ 1 token).
_CHARS_PER_TOKEN: int = 4
# Maximum tokens Titan accepts per request.
_MAX_TOKENS: int = 8_000

# Retry configuration.
_MAX_RETRIES: int = 3
_BASE_DELAY_SECONDS: float = 0.5

# ---------------------------------------------------------------------------
# Module-level client cache — survives across warm Lambda invocations.
# ---------------------------------------------------------------------------
_bedrock_client: Any | None = None


def _get_client() -> Any:
    """Lazily initialise and return the Bedrock Runtime client.

    Returns:
        A boto3 ``bedrock-runtime`` client instance, cached at module level.
    """
    global _bedrock_client
    if _bedrock_client is None:
        import boto3  # noqa: PLC0415

        _bedrock_client = boto3.client("bedrock-runtime")
        logger.info("Bedrock Runtime client initialised")
    return _bedrock_client


# ---------------------------------------------------------------------------
# Core embedding function
# ---------------------------------------------------------------------------


def generate_embedding(text: str) -> list[float]:
    """Generate a 1024-dimensional embedding via Bedrock Titan v2.

    Calls ``amazon.titan-embed-text-v2:0`` with ``dimensions=1024`` and
    ``normalize=True``.  Retries up to ``_MAX_RETRIES`` times on transient
    Bedrock errors using exponential backoff with random jitter.

    Args:
        text: The input text to embed.  Must be non-empty.

    Returns:
        A list of 1024 float values representing the embedding vector.

    Raises:
        RuntimeError: If all retry attempts are exhausted.
        Exception: Any non-retryable exception from Bedrock is re-raised
            immediately.
    """
    client = _get_client()
    body = json.dumps(
        {
            "inputText": text,
            "dimensions": _DIMENSIONS,
            "normalize": True,
        }
    )

    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.invoke_model(
                modelId=_MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            return result["embedding"]

        except Exception as exc:  # noqa: BLE001
            exc_type = type(exc).__name__
            is_retryable = _is_retryable(exc)

            if not is_retryable or attempt >= _MAX_RETRIES:
                logger.error(
                    "Bedrock embedding failed (attempt %d/%d, type=%s)",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc_type,
                )
                raise

            delay = _BASE_DELAY_SECONDS * (2**attempt) + random.uniform(0, 0.5)
            logger.warning(
                "Bedrock embedding transient error (attempt %d/%d, type=%s) — "
                "retrying in %.2fs",
                attempt + 1,
                _MAX_RETRIES + 1,
                exc_type,
                delay,
            )
            time.sleep(delay)
            last_exc = exc

    # Should be unreachable; satisfies type checker.
    raise RuntimeError(
        f"Bedrock embedding failed after {_MAX_RETRIES + 1} attempts"
    ) from last_exc


def _is_retryable(exc: Exception) -> bool:
    """Determine whether an exception is safe to retry.

    Uses duck-typing so this function works without importing botocore at
    module level (keeping cold-start cost low and enabling unit testing with
    plain exception subclasses).

    Retryable conditions:
    - Exception class name is ``ReadTimeoutError`` (botocore network timeout).
    - Exception has a ``response["Error"]["Code"]`` attribute whose value is
      one of the known transient Bedrock / AWS error codes.

    Args:
        exc: The exception to classify.

    Returns:
        True if the caller should retry, False otherwise.
    """
    # botocore.exceptions.ReadTimeoutError — always retryable.
    if type(exc).__name__ == "ReadTimeoutError":
        return True

    # Duck-type check for botocore ClientError: any exception that carries
    # a ``response`` dict with an Error.Code is treated as a ClientError.
    error_code: str = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    if error_code:
        retryable_codes = {
            "ThrottlingException",
            "ServiceUnavailableException",
            "InternalServerError",
            "ModelTimeoutException",
        }
        return error_code in retryable_codes

    return False


# ---------------------------------------------------------------------------
# Chunked embedding function
# ---------------------------------------------------------------------------


def generate_embeddings_chunked(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[tuple[str, list[float]]]:
    """Generate embeddings for text that may exceed Titan's token limit.

    Estimates the token count as ``len(text) // _CHARS_PER_TOKEN``.  If
    the text fits within ``_MAX_TOKENS``, a single ``(text, embedding)``
    tuple is returned.  Otherwise the text is split into overlapping
    character windows of ``chunk_size * _CHARS_PER_TOKEN`` characters with
    ``overlap * _CHARS_PER_TOKEN`` characters of overlap between adjacent
    chunks.

    Args:
        text: The full input text to embed.
        chunk_size: Target chunk size in approximate tokens (default 512).
        overlap: Overlap between adjacent chunks in approximate tokens
            (default 50).

    Returns:
        A list of ``(chunk_text, embedding)`` tuples — one per chunk.
        Always contains at least one element.

    Raises:
        RuntimeError: If any individual ``generate_embedding`` call fails
            after all retries.
    """
    estimated_tokens = len(text) // _CHARS_PER_TOKEN

    if estimated_tokens <= _MAX_TOKENS:
        return [(text, generate_embedding(text))]

    chunk_chars = chunk_size * _CHARS_PER_TOKEN
    overlap_chars = overlap * _CHARS_PER_TOKEN
    step = chunk_chars - overlap_chars

    if step <= 0:
        # Guard: overlap must be smaller than chunk_size.
        step = chunk_chars

    results: list[tuple[str, list[float]]] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_chars, text_len)
        chunk_text = text[start:end]
        if chunk_text:
            embedding = generate_embedding(chunk_text)
            results.append((chunk_text, embedding))
        start += step

    return results
