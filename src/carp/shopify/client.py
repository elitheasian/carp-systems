"""Minimal Shopify Admin GraphQL client, with bulk operations for full-catalog exports.

ChampKoi has 10,000+ koi variants, so exports use bulk operations (one async job that
produces a JSONL file) instead of paginating thousands of throttled requests.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_API_VERSION = "2026-07"

_BULK_RUN = """
mutation($query: String!) {
  bulkOperationRunQuery(query: $query) {
    bulkOperation { id status }
    userErrors { field message }
  }
}
"""

_BULK_STATUS = """
query($id: ID!) {
  node(id: $id) {
    ... on BulkOperation { id status errorCode objectCount url }
  }
}
"""


class ShopifyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ShopifyConfig:
    """Credentials for the CARP Systems app (apps/shopify).

    Uses the client credentials grant: the app's client ID and secret are exchanged for an
    Admin API token that lasts 24 hours. This only works for stores in the same Shopify
    organization as the app.
    """

    store: str
    client_id: str
    client_secret: str
    api_version: str = DEFAULT_API_VERSION

    @classmethod
    def from_env(cls) -> ShopifyConfig:
        names = ("SHOPIFY_STORE", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET")
        values = [os.environ.get(name) for name in names]
        if not all(values):
            raise ShopifyError(f"Set {', '.join(names)} (see .env.example)")
        store, client_id, client_secret = values
        return cls(
            store, client_id, client_secret,
            os.environ.get("SHOPIFY_API_VERSION", DEFAULT_API_VERSION),
        )


class ShopifyClient:
    # Refresh this long before Shopify's 24-hour expiry so a long bulk export never hits it.
    TOKEN_REFRESH_MARGIN = 3600

    def __init__(self, config: ShopifyConfig, http: httpx.Client | None = None):
        self.config = config
        self._http = http or httpx.Client(timeout=60)
        self._token: str | None = None
        self._token_expires_at = 0.0

    @property
    def endpoint(self) -> str:
        return f"https://{self.config.store}/admin/api/{self.config.api_version}/graphql.json"

    def access_token(self) -> str:
        if self._token is None or time.monotonic() >= self._token_expires_at:
            resp = self._http.post(
                f"https://{self.config.store}/admin/oauth/access_token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
            )
            if resp.is_error:
                raise ShopifyError(f"Token request failed ({resp.status_code}): {resp.text}")
            body = resp.json()
            self._token = body["access_token"]
            lifetime = body.get("expires_in", 86399)
            self._token_expires_at = time.monotonic() + lifetime - self.TOKEN_REFRESH_MARGIN
        return self._token

    def graphql(
        self, query: str, variables: dict[str, Any] | None = None, max_retries: int = 6
    ) -> dict[str, Any]:
        for attempt in range(max_retries):
            resp = self._http.post(
                self.endpoint,
                json={"query": query, "variables": variables or {}},
                headers={"X-Shopify-Access-Token": self.access_token()},
            )
            if resp.status_code == 401 and attempt == 0:
                self._token = None  # revoked or rotated secret: fetch a fresh token once
                continue
            if resp.status_code == 429:
                time.sleep(2**attempt)
                continue
            resp.raise_for_status()
            body = resp.json()
            errors = body.get("errors")
            if errors:
                if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors):
                    time.sleep(2**attempt)
                    continue
                raise ShopifyError(errors)
            return body["data"]
        raise ShopifyError("Gave up after repeated throttling")

    def run_bulk_query(self, query: str, poll_seconds: float = 5.0) -> Iterator[dict[str, Any]]:
        """Run a bulk query and yield each JSONL object (children carry `__parentId`)."""
        result = self.graphql(_BULK_RUN, {"query": query})["bulkOperationRunQuery"]
        if result["userErrors"]:
            raise ShopifyError(result["userErrors"])
        op_id = result["bulkOperation"]["id"]

        while True:
            op = self.graphql(_BULK_STATUS, {"id": op_id})["node"]
            if op["status"] == "COMPLETED":
                break
            if op["status"] in {"FAILED", "CANCELED", "EXPIRED"}:
                raise ShopifyError(f"Bulk operation {op['status']}: {op.get('errorCode')}")
            time.sleep(poll_seconds)

        if not op["url"]:
            return
        with self._http.stream("GET", op["url"]) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.strip():
                    yield json.loads(line)
