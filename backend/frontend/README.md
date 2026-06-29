# 智慧导航 Frontend

Vue 3 + Vite frontend for the AI tool navigation app.

## Local Development

```bash
npm install
npm run dev
```

Create or update `.env.development` when the backend API address changes:

```bash
VITE_API_BASE_URL=http://127.0.0.1:5000/api
```

## Vercel Deployment

Use these settings when deploying this repository to Vercel:

- Root Directory: backend/frontend
- Install Command: npm install
- Build Command: npm run build
- Output Directory: dist

Set the production environment variable to your deployed backend API:

```bash
VITE_API_BASE_URL=https://你的后端域名/api
```
