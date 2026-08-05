# 知航屿前端

Vue 3 + Vite frontend for 知航屿，智能网站导航与资源推荐平台。

## Local Development

From the repository root:

```bash
npm ci --legacy-peer-deps --prefix backend/frontend
npm run dev --prefix backend/frontend
```

Copy `backend/frontend/.env.example` to
`backend/frontend/.env.development` when the backend API address changes.
`VITE_API_BASE_URL` may point to a local or remote backend:

```bash
VITE_API_BASE_URL=http://127.0.0.1:5000/api
```

## Vercel Deployment

The root `vercel.json` builds both the frontend and Python function. Keep the
Vercel project Root Directory at the repository root:

- Root Directory: repository root (leave the Dashboard field empty)
- Install Command: `npm ci --legacy-peer-deps --prefix backend/frontend`
- Build Command: `npm run build --prefix backend/frontend`
- Output Directory: `backend/frontend/dist`

For the same-origin Vercel deployment, keep `VITE_API_BASE_URL` unset so the
frontend uses `/api`. For a separately hosted backend, set it to that public
API endpoint:

```bash
VITE_API_BASE_URL=https://backend.example.com/api
```

See `DEPLOY_VERCEL.md` in the repository root for backend environment
variables and deployment checks.
