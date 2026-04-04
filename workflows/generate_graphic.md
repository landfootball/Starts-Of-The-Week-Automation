# Workflow: Generate Weekly Graphics

## Objective
For each player you're featuring in the video, generate the relevant matchup cards (defensive stats, player logs, odds) and upload them to Google Drive for your video editor.

## Required inputs
- The opposing defense (e.g. "Seattle Seahawks")
- The player's team (e.g. "Los Angeles Rams") — for odds card
- The position (QB / RB / WR / TE)

## Step-by-step

### 1. Open the app
Go to your Streamlit URL (bookmarked after setup). The app shows the current week's data automatically.

### 2. Set up the matchup (sidebar)
- **Opposing Defense**: the team your player is FACING
- **Player's Team**: the team your player plays FOR
- **Position**: select QB / RB / WR / TE

The **Pickle Score** displays immediately at the top.

### 3. Generate the Defensive Stats Card (Tab 1)
- Review the stat checkboxes — uncheck any stats you don't want on the card
- Your selections are saved automatically for next time
- Click **Generate Defensive Stats Card**
- Preview appears on the right — download or continue to upload

### 4. Generate the Player Log Card (Tab 2)
- Click **Fetch [Position] Logs vs [Team]**
- All notable performances from the last 3–4 weeks appear as checkboxes
- Check only the lines you want to feature (the ones that help make your case)
- Click **Generate Player Log Card**

### 5. Generate the Odds Card (Tab 3) — optional
- Shows game O/U and implied team totals automatically
- Click **Generate Odds Card** if you want to show this in the video

### 6. Upload to Google Drive
- Scroll to the bottom of the app
- Click **Upload All Cards to Google Drive**
- All PNGs are uploaded to your Google Drive root with shareable links
- Download from Drive and send to your video editor

## Card naming convention
Cards are saved with this pattern:
- `{team_name}_def_card_{date}.png`
- `{team_name}_player_card_{date}.png`
- `{team_name}_odds_card_{date}.png`

## Tips
- For WR/TE takes: use Pass Yards Allowed/G, Pass TDs Allowed/G, and Receptions Allowed/G for the def card
- For RB takes: Rush Yards Allowed/G, Yards/Carry Allowed, and Rush TDs Allowed/G
- For QB takes: Pass Yards Allowed/G, Pass TDs Allowed/G, and Passer Rating Allowed
- The player log card works best with 3–5 lines — too many gets crowded
- Pickle Score ≥ 8.0 is a must-start; anything below 4.0 needs a strong counter-argument to make the case
