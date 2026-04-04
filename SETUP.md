# Setup Guide — FantasyLand Starts of the Week Tool

Complete this guide once before using the app. Takes ~15 minutes.

---

## Step 1: Install Python dependencies (local only)

```bash
pip install -r requirements.txt
```

---

## Step 2: Get a free Odds API key

1. Go to **https://the-odds-api.com**
2. Click **Get API Key** → sign up with email (free, no credit card)
3. Copy your API key from the dashboard
4. Save it for Step 5

---

## Step 3: Set up Google Drive API

### 3a. Create a Google Cloud project

1. Go to **https://console.cloud.google.com**
2. Click the project dropdown (top left) → **New Project**
3. Name it `fantasylandstarts` → **Create**

### 3b. Enable the Google Drive API

1. In your new project, go to **APIs & Services → Library**
2. Search for **Google Drive API** → click it → **Enable**

### 3c. Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. If prompted to configure consent screen:
   - Choose **External**
   - App name: `FantasyLand Starts`
   - Add your Gmail address as a test user
   - Save and continue through all screens
4. Back on Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: `fantasylandstarts`
   - Click **Create**
5. Click **Download JSON** → save as `credentials.json` in this project folder

---

## Step 4: First-time Google auth (local only)

Run this once to generate your token:

```bash
python tools/upload_to_gdrive.py
```

A browser window will open asking you to sign in to Google and grant access. After you approve, a `token.json` file is saved automatically. You won't need to do this again.

---

## Step 5: Create a GitHub repository

1. Go to **https://github.com/new**
2. Create a **private** repository (e.g. `fantasylandstarts`)
3. Push this project folder to it:

```bash
git init
git remote add origin https://github.com/YOUR_USERNAME/fantasylandstarts.git
git add .
git commit -m "initial setup"
git push -u origin main
```

---

## Step 6: Add GitHub Actions secret

1. In your GitHub repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `ODDS_API_KEY`
4. Value: paste your API key from Step 2
5. Save

This lets the weekly scheduled job pull odds data automatically.

---

## Step 7: Deploy to Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with GitHub
2. Click **New app**
3. Select your repository and set:
   - Branch: `main`
   - Main file path: `app.py`
4. Click **Deploy**

### Add secrets to Streamlit Cloud

In your deployed app → **Settings → Secrets**, add:

```toml
ODDS_API_KEY = "your_odds_api_key_here"

GOOGLE_CREDENTIALS_JSON = '''
{paste the full contents of credentials.json here on one line}
'''

GOOGLE_TOKEN_JSON = '''
{paste the full contents of token.json here — generated in Step 4}
'''
```

---

## Step 8: Trigger the first data update

The weekly job runs automatically every Wednesday midnight Sydney time. To run it immediately:

1. Go to your GitHub repo → **Actions** tab
2. Click **Weekly Data Update** → **Run workflow** → **Run workflow**

This will scrape TeamRankings and The Odds API, commit the data files, and your Streamlit app will automatically pick them up.

---

## You're done!

Open your Streamlit app URL, select a team and position, and start generating cards.

**Weekly routine:**
- Data updates automatically every Wednesday midnight Sydney time
- Open the app anytime to generate graphics for your video

---

## Troubleshooting

**"Stats data not found"** → Run the GitHub Actions workflow manually (Step 8)

**"No odds data for this team"** → The Odds API only shows games with current lines — check that the week has lines posted (usually available by Monday)

**"Google credentials not found"** → Make sure `GOOGLE_TOKEN_JSON` is set in Streamlit secrets (Step 7)

**Player logs show 0 results** → Sleeper API only has data for completed weeks. The tool looks back from the current NFL week.
