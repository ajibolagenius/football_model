# Deployment Options

You are currently running the app locally or on Streamlit Community Cloud. Here are other deployment options:

## 1. Render (Recommended for ease of use)
Render is a unified cloud to build and run all your apps and websites.
- **Type**: Web Service
- **Cost**: Free tier available (spins down on inactivity).
- **Setup**:
    1. Push your code to GitHub.
    2. Create a new "Web Service" on Render.
    3. Connect your GitHub repo.
    4. **Runtime**: Python 3
    5. **Build Command**: `pip install -r requirements.txt`
    6. **Start Command**: `streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0`
    7. **Environment Variables**: Add your `.env` variables (DB_CONNECTION, API keys) in the Render dashboard.

## 2. Heroku
Popular platform as a service.
- **Type**: Dyno
- **Cost**: Paid (Eco dynos start at ~$5/mo).
- **Setup**:
    1. Install Heroku CLI.
    2. `heroku create`
    3. Add `Procfile`: `web: streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0`
    4. `git push heroku master`
    5. Set env vars: `heroku config:set DB_CONNECTION=...`

## 3. Railway
Similar to Render, very developer friendly.
- **Type**: Service
- **Setup**: Connect GitHub, it auto-detects Python.

## 4. Google Cloud Run
Serverless containers. Good for scaling.
- **Type**: Docker Container
- **Setup**:
    1. Build Docker image: `docker build -t football-app .`
    2. Push to Container Registry.
    3. Deploy to Cloud Run.

## 5. Supabase (Database)
You are already using Supabase for the database. Ensure your deployed app (Render/Heroku) uses the **Supabase Connection String** in its environment variables.
