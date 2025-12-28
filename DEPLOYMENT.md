# Deployment Guide

## Quick Deploy

### 1. Backend Deployment (Render)

1. **Push to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy on Render**:
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository
   - Configure:
     - **Name**: `yepai-scheduler-backend`
     - **Root Directory**: `spearfishes/yepai/backend`
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
     - **Health Check Path**: `/health`
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Copy the service URL (e.g., `https://yepai-scheduler-backend.onrender.com`)

### 2. Frontend Deployment (Vercel)

1. **Deploy on Vercel**:
   - Go to https://vercel.com
   - Click "Add New..." → "Project"
   - Import your GitHub repository
   - Configure:
     - **Framework Preset**: `Vite`
     - **Root Directory**: `spearfishes/yepai/frontend`
     - **Build Command**: `npm run build`
     - **Output Directory**: `dist`
   - Add Environment Variable:
     - **Key**: `VITE_API_URL`
     - **Value**: `https://yepai-scheduler-backend.onrender.com/api` (use your actual Render URL)
   - Click "Deploy"
   - Wait for deployment (2-3 minutes)

2. **Update vercel.json** (if needed):
   - Edit `frontend/vercel.json`
   - Replace `yepai-scheduler-backend.onrender.com` with your actual Render backend URL

## Alternative: Railway Deployment

### Backend on Railway

1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Select repository
4. Add service → Python
5. Set root directory: `spearfishes/yepai/backend`
6. Railway auto-detects FastAPI and deploys

### Frontend on Railway

1. Add another service → Static
2. Set root directory: `spearfishes/yepai/frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Add environment variable: `VITE_API_URL` = your backend URL

## Environment Variables

### Backend (Render/Railway)
- `PYTHON_VERSION`: `3.11.0` (optional, Render auto-detects)

### Frontend (Vercel/Railway)
- `VITE_API_URL`: Your backend API URL (e.g., `https://yepai-scheduler-backend.onrender.com/api`)

## Post-Deployment

1. **Test Backend**:
   ```bash
   curl https://your-backend-url.onrender.com/health
   ```

2. **Test Frontend**:
   - Visit your Vercel/Railway frontend URL
   - Click "Generate Roster"
   - Verify it connects to backend

3. **Update CORS** (if needed):
   - Edit `backend/api/main.py`
   - Update `allow_origins` in CORS middleware to include your frontend URL

## Troubleshooting

### Backend Issues
- **Build fails**: Check Python version (needs 3.11+)
- **Data files missing**: Ensure Excel/CSV files are in project root
- **Health check fails**: Verify `/health` endpoint works locally

### Frontend Issues
- **API calls fail**: Check `VITE_API_URL` environment variable
- **CORS errors**: Update backend CORS settings
- **Build fails**: Check Node.js version (needs 18+)

## Notes

- Render free tier spins down after 15 minutes of inactivity (first request may be slow)
- Vercel has generous free tier with instant deployments
- Data files (Excel/CSV) must be included in repository or uploaded separately
