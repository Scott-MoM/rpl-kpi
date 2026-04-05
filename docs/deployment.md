# FastAPI + React Deployment Notes

## Required environment variables

### Backend

- `RPL_SUPABASE_URL`
- `RPL_SUPABASE_KEY`
- `RPL_SUPABASE_SERVICE_ROLE_KEY`
- `RPL_BEACON_API_KEY`
- `RPL_BEACON_ACCOUNT_ID` or `RPL_BEACON_BASE_URL`

### Frontend

- `VITE_API_BASE_URL`

## Recommended backend variables

- `RPL_ENVIRONMENT=production`
- `RPL_CORS_ORIGINS=["https://your-frontend-host"]`
- `RPL_ALLOWED_HOSTS=["your-api-host"]`
- `RPL_FORCE_HTTPS=true`
- `RPL_ENABLE_API_DOCS=false`
- `RPL_LOG_LEVEL=INFO`

## Local verification

### Backend

```powershell
cd backend
python -m pytest
python -m py_compile app\main.py
python -c "import sys; sys.path.insert(0, '.'); from app.main import app; print(app.title)"
```

### Frontend

```powershell
cd frontend
npm.cmd run build
```

## Health endpoints

- `GET /health`: process liveness
- `GET /health/ready`: configuration readiness summary

`/health/ready` returns `503` only when the core API cannot operate because Supabase client settings are missing. Admin and Beacon sync requirements are reported separately so partial deployments are easy to diagnose.
