# Backend Deployment Steps (Render)

## Step 1: Push to GitHub

1. Initialize git (if not already):
   ```bash
   cd /Users/duncan/Desktop/Cursor_Projects/spear
   git init
   git add .
   git commit -m "Initial commit - YepAI scheduler"
   ```

2. Create a new repository on GitHub:
   - Go to https://github.com/new
   - Name it: `yepai-scheduler` (or your preferred name)
   - Don't initialize with README
   - Click "Create repository"

3. Push to GitHub:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/yepai-scheduler.git
   git branch -M main
   git push -u origin main
   ```

## Step 2: Deploy on Render

1. Go to https://render.com and sign in (or sign up)

2. Click "New +" → "Web Service"

3. Connect your GitHub account if not already connected

4. Select your repository: `yepai-scheduler`

5. Configure the service:
   - **Name**: `yepai-scheduler-backend`
   - **Region**: Choose closest to you (e.g., Singapore, US East)
   - **Branch**: `main`
   - **Root Directory**: `spearfishes/yepai/backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (or choose paid for better performance)

6. Click "Create Web Service"

7. Wait for deployment (5-10 minutes)

8. Once deployed, copy your service URL (e.g., `https://yepai-scheduler-backend.onrender.com`)

## Step 3: Update Frontend API URL

1. Go to your Vercel dashboard: https://vercel.com/duncansebampitako-7785s-projects/frontend

2. Go to Settings → Environment Variables

3. Add/Update:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://your-backend-url.onrender.com/api` (replace with your actual Render URL)

4. Redeploy:
   ```bash
   cd /Users/duncan/Desktop/Cursor_Projects/spear/spearfishes/yepai/frontend
   vercel --prod
   ```

## Step 4: Update CORS (if needed)

If you get CORS errors, update `backend/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://frontend-j6a8a9f1b-duncansebampitako-7785s-projects.vercel.app",
        "https://your-vercel-domain.vercel.app",  # Add your actual Vercel domain
        "*"  # Or be more specific
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then push and redeploy on Render.

## Testing

1. Test backend health:
   ```bash
   curl https://your-backend-url.onrender.com/health
   ```

2. Test frontend:
   - Visit: https://frontend-j6a8a9f1b-duncansebampitako-7785s-projects.vercel.app
   - Click "Generate Roster"
   - Should connect to backend and generate roster

## Notes

- Render free tier spins down after 15 min inactivity (first request may be slow)
- Data files (Excel/CSV) must be in the repository for backend to work
- Update `vercel.json` proxy URL if you change backend URL
