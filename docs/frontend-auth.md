# Frontend authentication and evidence upload

The React app in `frontend/frontend` uses Supabase Auth only for sign-in. It
does not read or write forensic tables through the Supabase browser Data API.
Every case, evidence upload, and parse request goes to FastAPI with the
Supabase access token in an `Authorization: Bearer` header.

## Configure the backend

In the root `.env` file, use the existing Supabase database URL and set:

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
AUTH_REQUIRED=true
CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
```

For modern Supabase signing keys, the backend validates tokens using the
project JWKS endpoint. `SUPABASE_JWT_SECRET` is optional and only needed for a
legacy HS256 project.

Install the new backend dependency before running the API:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload --env-file .env
```

## Configure the frontend

Copy `frontend/frontend/.env.example` to `frontend/frontend/.env.local` and
set the project URL and **publishable/anon** key from Supabase Connect/API
settings. Never use the service-role key in the browser.

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY
```

Then install the frontend dependency and start Vite:

```powershell
cd frontend/frontend
npm install
npm run dev
```

Enable Email authentication in Supabase Auth if it is not already enabled.
With email confirmation enabled, a new user must confirm their email before
they can sign in and start a case.

## Security boundary

Keep RLS enabled with no direct browser policies on `cases`, `evidence`,
`devices`, and `recordings`. The frontend has no database credentials and the
FastAPI service enforces the case owner derived from the verified token.
