"""`carp` command line."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx

from carp.data.manifest import build_manifest, write_manifest
from carp.shopify.client import ShopifyClient, ShopifyConfig
from carp.shopify.listings import (
    CatalogConfig,
    build_bulk_query,
    parse_bulk_export,
    resolve_fish_ids,
)

DEFAULT_CATALOG_CONFIG = Path("config/shopify.local.toml")


def ingest_shopify(out: Path, download_images: bool, config_path: Path) -> None:
    if not config_path.exists():
        raise SystemExit(
            f"{config_path} not found. Copy config/shopify.example.toml there and fill it in."
        )
    catalog = CatalogConfig.load(config_path)
    client = ShopifyClient(ShopifyConfig.from_env())
    out.mkdir(parents=True, exist_ok=True)

    raw_path = out / "koi_listings.jsonl"
    print("Running Shopify bulk export (this can take a few minutes)...")
    with raw_path.open("w") as f:
        for obj in client.run_bulk_query(build_bulk_query(catalog)):
            f.write(json.dumps(obj) + "\n")

    with raw_path.open() as f:
        listings = parse_bulk_export((json.loads(line) for line in f if line.strip()), catalog)
    variants = [v for listing in listings for v in listing.variants]
    rows = build_manifest(listings, resolve_fish_ids(variants))

    if download_images:
        _download_images(rows, out / "images")

    write_manifest(rows, out / "manifest.jsonl")

    kinds = Counter(listing.kind for listing in listings)
    labels = Counter(v.label for v in variants if v.label)
    skipped = [listing for listing in listings if not any(v.label for v in listing.variants)]
    print(f"Listings: {kinds['single']} single, {kinds['group']} group")
    print(f"Skipped (no real variety): {len(skipped)} listings, "
          f"{sum(v.label is None for v in variants)} fish")
    print(f"Fish (variants): {len(variants)}; manifest rows: {len(rows)}")
    print(f"Rows needing review: {sum(r.needs_review for r in rows)}")
    print("Top varieties:", ", ".join(f"{k} ({n})" for k, n in labels.most_common(15)))


def _download_images(rows, image_dir: Path, workers: int = 8, retries: int = 3) -> None:
    """Download each photo once. Safe to re-run: finished files are skipped, and files are
    written under a temporary name so an interrupted run never leaves a truncated image."""
    image_dir.mkdir(parents=True, exist_ok=True)
    urls: dict[str, str] = {}
    for row in rows:
        urls.setdefault(row.media_id, row.image_url)

    def target(media_id: str, url: str) -> Path:
        suffix = Path(urlparse(url).path).suffix.lower() or ".jpg"
        return image_dir / f"{media_id.rsplit('/', 1)[-1]}{suffix}"

    def fetch(http: httpx.Client, media_id: str, url: str) -> Path:
        path = target(media_id, url)
        if path.exists():
            return path
        for attempt in range(retries):
            try:
                resp = http.get(url)
                resp.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == retries - 1:
                    raise
                time.sleep(2**attempt)
        partial = path.with_suffix(path.suffix + ".part")
        partial.write_bytes(resp.content)
        partial.replace(path)
        return path

    paths: dict[str, Path] = {}
    with httpx.Client(timeout=60, follow_redirects=True) as http, \
            ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, http, m, u): m for m, u in urls.items()}
        for done, future in enumerate(as_completed(futures), start=1):
            paths[futures[future]] = future.result()
            if done % 250 == 0 or done == len(futures):
                print(f"Images: {done}/{len(futures)}", flush=True)

    for row in rows:
        row.image_path = str(paths[row.media_id])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="carp")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest-shopify", help="Export koi listings into a dataset manifest")
    ingest.add_argument("--out", type=Path, default=Path("data/shopify"))
    ingest.add_argument("--download-images", action="store_true")
    ingest.add_argument("--config", type=Path, default=DEFAULT_CATALOG_CONFIG,
                        help="Store catalog mapping (see config/shopify.example.toml)")

    args = parser.parse_args(argv)
    if args.command == "ingest-shopify":
        ingest_shopify(args.out, args.download_images, args.config)


if __name__ == "__main__":
    main()
