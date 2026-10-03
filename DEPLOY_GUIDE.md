# Stage 2: 24/7 Cloud Deployment Guide

This guide explains how to deploy your Scratch AI Bot (`Verity`) to the cloud so it runs **24 hours a day, 7 days a week**, completely free, with your laptop turned off.

---

## 🌟 Recommended Option 1: Koyeb (100% Free, Never Sleeps)

Koyeb provides a free **Nano** instance that runs 24/7 without going to sleep.

### Steps:
1. Create a free account at [koyeb.com](https://www.koyeb.com).
2. Push your `stage 2` folder to a GitHub repository (e.g. `scratch-verity-bot`).
3. In the Koyeb control panel, click **Create App** ➔ **GitHub**.
4. Select your repository.
5. In **Environment Variables**, add the 5 variables from your [`.env.example`](file:///C:/Users/Ruchi/Downloads/verdent/AIdoneRight/stage%202/.env.example):
   - `SCRATCH_USERNAME` = `VVFPFoodProject`
   - `SCRATCH_PASSWORD` = (your Scratch password)
   - `SCRATCH_PROJECT_ID` = `1387678175`
   - `OPENROUTER_API_KEY` = (your OpenRouter key starting with `sk-or-v1-...`)
   - `OPENROUTER_MODEL` = `liquid/lfm-2.5-2.6b:free`
6. Click **Deploy**.
7. In ~60 seconds, Koyeb will build the Docker container and start your bot. You can visit the public Koyeb URL to see the status page:  
   `🤖 Verity Scratch AI Bot is Live! Status: 24/7 Online`

---

## 🌟 Recommended Option 2: Hugging Face Spaces (Easiest — No GitHub Needed!)

Hugging Face Spaces gives you a free 24/7 container with **direct drag-and-drop file upload** in your browser!

### Steps:
1. Go to [huggingface.co](https://huggingface.co) and create a free account.
2. Go to **Spaces** ➔ click **Create new Space**.
3. Set:
   - **Space name**: `verity-scratch-bot`
   - **Space SDK**: **Docker** ➔ **Blank**
   - **Space Hardware**: **CPU Basic (Free)**
4. Click **Create Space**.
5. Click **Files** ➔ **Add file** ➔ **Upload files**.
   - Drag and drop the files from your [`stage 2`](file:///C:/Users/Ruchi/Downloads/verdent/AIdoneRight/stage%202/) folder:
     - `bot.py`
     - `requirements.txt`
     - `Dockerfile`
   - Click **Commit changes to main**.
6. Go to **Settings** ➔ scroll down to **Variables and secrets**.
   - Click **New secret** and add each:
     - `SCRATCH_USERNAME`
     - `SCRATCH_PASSWORD`
     - `SCRATCH_PROJECT_ID`
     - `OPENROUTER_API_KEY`
     - `OPENROUTER_MODEL` (`liquid/lfm-2.5-2.6b:free`)
7. Click **Restart this Space**.
8. Hugging Face builds and runs the container. The bot is now online 24/7!

---

## 🌟 Option 3: Render (Free Web Service)

1. Create a free account at [render.com](https://render.com).
2. Connect your GitHub repository with the `stage 2` code.
3. Click **New +** ➔ **Web Service**.
4. Set:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. In **Environment Variables**, add the 5 variables from `.env.example`.
6. Click **Create Web Service**.
7. *(Optional tip for Render)*: Render's free tier sleeps after 15 minutes of no web visits. Because `bot.py` has an embedded health check server on port 8080, you can paste your Render URL into a free service like [UptimeRobot.com](https://uptimerobot.com) to ping it every 5 minutes and keep it awake 24/7!

---

## 🛠️ Testing Your 24/7 Bot Locally First

You can test `stage 2/bot.py` right on your laptop before uploading:

1. Copy your root [`.env`](file:///C:/Users/Ruchi/Downloads/verdent/AIdoneRight/.env) into the `stage 2` folder:
   ```powershell
   Copy-Item .env "stage 2\.env"
   ```
2. Run it:
   ```powershell
   cd "stage 2"
   python bot.py
   ```
3. Open your browser to [http://localhost:8080](http://localhost:8080). You will see the health dashboard confirming everything is live!
