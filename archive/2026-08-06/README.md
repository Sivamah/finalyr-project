# Archive Manifest — 2026-08-06

Dead / obsolete code removed from the live tree, archived here (not deleted)
to preserve history and safe rollback. Verify: no live module references
these files (confirmed by grep across `backend/app` and `frontend/src`).

## Backend — unregistered routers & unused services
| Path (archived) | Original location | Why removed |
| --- | --- | --- |
| `backend/app/api/routes/dmfe.py` | `app/api/routes/dmfe.py` | Obsolete DMFE router; never imported by `app/main.py` (v2 + engine registrations supply all live `/api/dmfe/*` routes the frontend calls) |
| `backend/app/api/routes/generator.py` | `app/api/routes/generator.py` | Obsolete generator router (`/generate`, `/requests`); not imported by `app/main.py`, no frontend caller |
| `backend/app/schemas/generator.py` | `app/schemas/generator.py` | Schema owned exclusively by `generator.py` (now archived) |
| `backend/app/services/dataset_service.py` | `app/services/dataset_service.py` | Unused service; dataset logic is inline in `routes/orchestration.py` |
| `backend/app/services/orchestration_service.py` | `app/services/orchestration_service.py` | Unused service; orchestration lives in `routes/orchestration.py` + `app/engine/optimizer.py` |
| `backend/app/services/provider_service.py` | `app/services/provider_service.py` | Unused service; provider CRUD is inline in `routes/providers.py` |

## Frontend
| Path (archived) | Notes |
| --- | --- |
| `frontend/src/pages/AdminDashboard.jsx` | Dead page: no route/import references anywhere in `src` |
| `frontend/src/App.css` | Scaffold stylesheet; `main.jsx` imports only `index.css` |
| `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg` | Vite scaffold icons; unreferenced (empty `assets/` dir removed) |

## Verification
- `python -c "from app.main import app"` → imports OK (19 routes).
- All 24 live API endpoints return HTTP 200 after the move.
- `npm run build` completes successfully after the move.