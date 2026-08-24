# SIWES Platform — Multi-Tenant Edition

A multi-tenant version of the SIWES Report generator. One platform, many universities.

- **Super admin (you)** — onboard schools, manage school admins, see platform-wide revenue.
- **School admin** — manages their school's orders, students, settings, pricing. Cannot see other schools' data.
- **Students** — visit `/<school_slug>` (e.g. `/lmu`) for a fully branded experience.

A platform cut (default 20%) is taken from every order; the rest goes to the school admin.

## Stack
- Backend: FastAPI + SQLite (WAL)
- Generation: Anthropic Claude (Sonnet) + python-docx / python-pptx
- Payments: Paystack (per-school keys, fallback to platform-level)
- Admin UI: React + TypeScript + Tailwind + Vite

## Quick start

### 1. Install backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env — at minimum:
#   ANTHROPIC_API_KEY=sk-ant-...
#   SUPER_ADMIN_INITIAL_PIN=<choose>
#   PAYSTACK_SECRET_KEY=sk_test_...
#   PAYSTACK_PUBLIC_KEY=pk_test_...
```

### 3. Initialise database & seed Landmark
```bash
cd backend
python seed_lmu.py
```
This creates the `lmu` school + a default school admin (`lmu_admin` / PIN `1234` — **change it**).

### 4. Run backend
```bash
cd backend
uvicorn api.main:app --reload
```

### 5. Build admin SPA
```bash
cd admin
npm install
npm run build         # produces admin/dist/ served by FastAPI at /admin
# or for dev with hot reload:
npm run dev           # http://localhost:5173 (proxies /admin/api to backend)
```

### 6. Visit
- Student landing: <http://localhost:8000/lmu>
- Admin login: <http://localhost:8000/admin/> — `superadmin` + your `SUPER_ADMIN_INITIAL_PIN`
- Root index: <http://localhost:8000/> — lists all schools

## Onboarding a new school

1. Log in as super admin.
2. Schools → **+ Add school**:
   - Slug: short URL fragment (e.g. `covenant`)
   - Name & Full name (full goes on docs)
   - Referral prefix (e.g. `CU` → `CU-XXXXX` codes)
   - Platform cut % (default 20)
   - Paystack keys (optional — falls back to platform-level env)
3. Open the new school, **Upload logo** (PNG/JPG ≤2MB).
4. Add a school admin and share the PIN with them.
5. Tell the school admin to log in and fill out **Settings**: their degrees, departments, colleges, prices, submission clause.

## Data isolation
Every school-admin route filters by `school_id` from the session. Super admins may operate on any school by passing `?school_id=<n>`. No school admin can read or write another school's data.

## Project layout
```
backend/
  api/                    # FastAPI app
  services/               # report_generator, ppt_generator, claude_client (school-config-aware)
  assets/schools/<slug>/  # logos
  data/platform.db        # SQLite (WAL)
  outputs/<order_id>/     # generated docx + pptx
  uploads/<order_id>/     # student-uploaded photos
admin/                    # React SPA (super + school admin in one bundle)
```

## Webhooks
Paystack webhook URL per school: `POST /webhook/paystack/<slug>`.

## Notes
- `SUPER_ADMIN_INITIAL_PIN` is consumed on first start when the `super_admin` table is empty.
- Re-run `python seed_lmu.py` any time — it's idempotent.
- Generation uses an in-process thread pool (max 6 concurrent). Orders stuck in `generating` for >20 min are marked failed by the watchdog.
