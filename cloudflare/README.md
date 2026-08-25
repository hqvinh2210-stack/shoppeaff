# Cloudflare API proxy

This Worker exposes `api.beehoantien.asia` and forwards requests to the existing
FastAPI deployment. It lets the Vercel frontend use a stable API domain without
migrating the PostgreSQL, Redis, and background workers into Workers.

## Deploy

Install Wrangler and authenticate:

```bash
npm install -g wrangler
wrangler login
```

From this directory, set the real backend URL and deploy:

```bash
wrangler secret put BACKEND_ORIGIN
wrangler deploy
```

Use a value such as `https://shoppeaff-api.onrender.com`. Do not commit the
backend URL if it contains credentials or private routing information.

In Cloudflare, attach the custom domain `api.beehoantien.asia` to this Worker.
Then set the Vercel production variable:

```env
NEXT_PUBLIC_API_URL=https://api.beehoantien.asia/api/v1
```

The backend must allow both frontend origins:

```env
CORS_ORIGINS=https://www.beehoantien.asia,https://beehoantien.asia
```

Verify the chain in this order:

1. `https://<backend-host>/health`
2. `https://api.beehoantien.asia/health`
3. Login from `https://www.beehoantien.asia`

This is a proxy deployment, not a full FastAPI-to-Python-Workers rewrite.
Cloudflare Python Workers migration still requires replacing the current
SQLAlchemy/psycopg2 database layer and long-running workers.