# McDonald's Workforce Scheduling System

Intelligent multi-agent scheduling system for McDonald's Australia operations.

## Architecture

- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI + Python + OR-Tools (CP-SAT solver)
- **Multi-Agent System**: Orchestrator, Demand, Matcher, Validator, Resolver agents

## Deployment

### Backend (Render)

1. Push code to GitHub
2. Connect repository to Render
3. Create new Web Service
4. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
   - **Python Version**: 3.11.0

Or use the `render.yaml` file for Infrastructure as Code deployment.

### Frontend (Vercel)

1. Push code to GitHub
2. Connect repository to Vercel
3. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Environment Variable**: `VITE_API_URL` = your Render backend URL (e.g., `https://yepai-scheduler-backend.onrender.com/api`)

The `vercel.json` file includes API proxy configuration.

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will proxy `/api` requests to `http://localhost:8001` in development.

## Data Files

The system uses these data files (should be in the project root):
- `employee_availability_2weeks.xlsx` - Employee availability schedules
- `management_roster_simplified.xlsx` - Management shift codes
- `store_structure_staff_estimate.csv` - Store staffing requirements

## Features

- ✅ Intelligent roster generation (< 180s for 2-week roster)
- ✅ Peak period coverage (lunch/dinner peaks, weekends +20%)
- ✅ Conflict detection & resolution
- ✅ Employee skill matching
- ✅ Australian Fair Work Act compliance
- ✅ Multi-agent orchestration
