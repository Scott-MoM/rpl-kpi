# FastAPI + React Migration Backlog

## Goals

- Replace the current Streamlit runtime with a faster web app architecture.
- Preserve the current dashboard layout, theme, and information hierarchy.
- Keep Supabase as the primary data source and role authority.
- Migrate incrementally so Streamlit remains the fallback during development.

## Current App Domains

- Auth and session management
- KPI dashboard
- Custom reports dashboard
- ML dashboard
- Funder dashboard
- Admin dashboard
- Case studies
- Manual sync and audit workflows

## Target Architecture

- `backend/`: FastAPI API, service layer, Supabase integration, auth, reporting
- `frontend/`: React app with routing, theme system, query caching, Plotly charts

## Delivery Phases

### Phase 1: Foundation

- Create backend and frontend app shells
- Define API route groups and response schemas
- Recreate the current visual theme as reusable CSS tokens
- Add placeholder routes/pages for all current dashboard areas

### Phase 2: Shared Backend Extraction

- Extract reusable Supabase client setup
- Extract auth and password change logic from `app.py`
- Extract shared date filter and region filter logic
- Extract dashboard data loaders into backend services

### Phase 3: KPI Dashboard

- Implement `GET /dashboard/kpi`
- Rebuild sidebar, filters, metric cards, section switching, and drill-down panels
- Verify KPI parity against Streamlit output for sample regions/date ranges

### Phase 4: Funder and ML Dashboards

- Implement `GET /dashboard/funder`
- Implement `GET /dashboard/ml`
- Recreate chart/table views and role-based access restrictions

### Phase 5: Custom Reports

- Implement `GET /reports/custom`
- Rebuild report builder controls, charts, exports, and comparison mode
- Optimize expensive report queries and aggregations

### Phase 6: Admin and Sync

- Implement user management endpoints
- Implement audit log endpoints
- Implement manual sync start/status endpoints
- Replace Streamlit rerun-driven progress UI with polling in React

### Phase 7: Case Studies and Cutover

- Implement case study list/create endpoints
- Complete parity testing
- Freeze Streamlit changes and switch primary deployment to the new app

## Backend Backlog

- Add application config and environment loading
- Add Supabase client provider
- Add auth service and current-user dependency
- Add typed schemas for each dashboard response
- Add dashboard service modules
- Add report query service modules
- Add admin action service modules
- Add sync job service modules
- Add smoke tests for route availability

## Frontend Backlog

- Add app shell with sidebar and header
- Add route protection and session handling
- Add shared filter bar components
- Add dashboard metric card component
- Add chart container and table container components
- Add API client and query hooks
- Add page implementations in migration order

## Phase 1 Exit Criteria

- `backend/app/main.py` starts a FastAPI app
- `frontend/src/main.tsx` starts a React app
- Placeholder routes/pages exist for every current Streamlit dashboard
- The visual theme direction reflects the existing Streamlit design

## Immediate Next Slice

- Wire backend config from environment variables
- Move Supabase setup out of `app.py`
- Implement login/current-user backend endpoints
- Replace placeholder login page with a working auth flow
