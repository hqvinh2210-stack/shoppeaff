# Deploy Bee Hoan Tien

## 1. Deploy backend on Render

1. Open Render and choose **New > Blueprint**.
2. Connect the GitHub repository `hqvinh2210-stack/shoppeaff`.
3. Select the repository root. Render reads `render.yaml` and creates the API, PostgreSQL, and Redis services.
4. After the first deploy, open the API service and copy its `onrender.com` URL.
5. In the API service environment, fill the secret values marked `sync: false` in `render.yaml`.
6. Run the database schema from `backend/001_accesstrade.sql` against the created PostgreSQL database if the service does not run migrations automatically.
7. Verify `https://<render-api-host>/health` returns `{"status":"ok"}`.

## 2. Connect Cloudflare

In Cloudflare DNS for `beehoantien.asia`, add:

- Type: `CNAME`
- Name: `api`
- Target: the Render API hostname, for example `shoppeaff-api.onrender.com`
- Proxy status: DNS only during the first test; enable Proxied after HTTPS works

Then verify `https://api.beehoantien.asia/health`.

## 3. Connect the frontend

In the frontend hosting provider, set this production environment variable:

```env
NEXT_PUBLIC_API_URL=https://api.beehoantien.asia/api/v1
```

Redeploy the frontend after saving the variable.

## 4. Required backend values

The backend must include:

```env
ENVIRONMENT=production
CORS_ORIGINS=https://www.beehoantien.asia,https://beehoantien.asia
APP_BASE_URL=https://www.beehoantien.asia
JWT_SECRET=<generated-secret>
JWT_REFRESH_SECRET=<generated-secret>
```

Add the real affiliate, bot, Zalo, and SMTP credentials when those features are enabled. Never commit `.env` files or secret values to GitHub.
