import json

import httpx

from carp.shopify.client import ShopifyClient, ShopifyConfig

CONFIG = ShopifyConfig("example.myshopify.com", "client-id", "client-secret", "2026-07")


def test_exchanges_client_credentials_once_and_reuses_token():
    token_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/admin/oauth/access_token":
            token_requests.append(dict(httpx.QueryParams(request.content.decode())))
            return httpx.Response(200, json={"access_token": "tok-1", "expires_in": 86399})
        assert request.headers["X-Shopify-Access-Token"] == "tok-1"
        assert json.loads(request.content)["query"] == "{ shop { name } }"
        return httpx.Response(200, json={"data": {"shop": {"name": "ChampKoi"}}})

    client = ShopifyClient(CONFIG, httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.graphql("{ shop { name } }") == {"shop": {"name": "ChampKoi"}}
    client.graphql("{ shop { name } }")

    assert token_requests == [
        {"grant_type": "client_credentials", "client_id": "client-id",
         "client_secret": "client-secret"}
    ]


def test_refetches_token_after_401():
    tokens = iter(["stale", "fresh"])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/admin/oauth/access_token":
            return httpx.Response(200, json={"access_token": next(tokens), "expires_in": 86399})
        if request.headers["X-Shopify-Access-Token"] == "stale":
            return httpx.Response(401)
        return httpx.Response(200, json={"data": {"ok": True}})

    client = ShopifyClient(CONFIG, httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.graphql("{ ok }") == {"ok": True}
