# Cloudflare Workers + D1 Link Manager

## Deploy
1. `npm install`
2. `npx wrangler login`
3. `npx wrangler d1 create link-manager-db`
4. Copy database_id into `wrangler.jsonc`.
5. `npx wrangler d1 execute link-manager-db --remote --file=./schema.sql`
6. `npx wrangler secret put ADMIN_PASSWORD`
7. `npx wrangler secret put SESSION_SECRET` (use a long random value)
8. `npx wrangler deploy`

Then visit `https://human-verification.<your-subdomain>.workers.dev/admin`.

This version runs natively on Cloudflare Workers and D1; it does not run Flask or SQLite.
The login uses a signed-equivalent deterministic token derived from the two secrets; for stronger public production security, add Cloudflare Access and rate limits.
Tracking IDs are random placeholders, not real Meta ad IDs. Facebook supplies `fbclid` when appropriate.
