# CARP Shopify app

A config-only Shopify app with no UI and no extensions. It exists so CARP's Python tools can
read the store's catalog through the Admin API.

| Scope | Used for |
|---|---|
| `read_products` | Koi products, variants, media and variant metafields |
| `read_metaobjects` | Variety metaobjects referenced from variants |

Keep it read-only. Add a scope only when code needs it, and note why in the config.

## Setup

The real app config contains the app's client ID and is git-ignored. Only
`shopify.app.toml.example` is committed. Get `shopify.app.<name>.toml` from a teammate, or copy
the example and set `client_id`.

## Changing scopes

```bash
cd apps/shopify
npm install            # first time only
shopify app config validate --config <name> --json
shopify app deploy --config <name> --allow-updates --message "why the scopes changed"
```

Then approve the new scopes on the store. Shopify doesn't apply scope changes to an installed
app automatically.

## Credentials

The Python client uses the **client credentials grant**. It exchanges the app's client ID and
secret for a 24-hour token and refreshes it automatically. Put them in the repo-root `.env` (see
`.env.example`), never in git.

To fill in the secret without printing it, pull the app's variables into the app folder's
default `.env` (the CLI's `--env-file` flag clashes with Node's), copy the value, and delete the
file:

```bash
shopify app env pull --path apps/shopify --config <name> >/dev/null 2>&1 && secret=$(grep '^SHOPIFY_API_SECRET=' apps/shopify/.env | cut -d= -f2-) && sed -i '' "s|^SHOPIFY_CLIENT_SECRET=.*|SHOPIFY_CLIENT_SECRET=${secret}|" .env; unset secret; rm -f apps/shopify/.env
```

The grant only works when the store belongs to the same Shopify organization as the app. A
`shop_not_permitted` error means it doesn't.
