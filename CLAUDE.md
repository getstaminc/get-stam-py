# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Flask/Python)
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server (caching disabled when FLASK_ENV=development)
FLASK_ENV=development python app.py

# Run with gunicorn (production-style)
gunicorn app:app

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Run a data ingestion job (e.g., seed yesterday's NBA games)
python jobs/nba_seed_yesterdays_games.py
```

### Frontend (React)
```bash
# Development
cd getstam-react && npm start

# Production build (output goes to getstam-react/build/, served by Flask)
npm run build
```

### Clear cache (in-app)
```
GET /clear-cache
```

## Architecture

This is a **Flask + React monorepo**. Flask serves the React build at `/` and exposes a JSON API under `/api/`. All API routes require an `X-API-KEY` header.

### Request flow for live game data
1. React → Flask `/api/scores/<sport>` or `/api/games/<sport>`
2. Flask route (`api/routes/`) → `GameService` (`api/services/game_service.py`)
3. `GameService` → `get_odds_data()` in `api/external_requests/odds_api.py`
4. Odds API returns scores + odds; response is formatted and returned

### Request flow for historical/trends data
1. React → Flask `/api/historical/<sport>/games` (GET) or `/api/historical/trends/<sport>` (POST)
2. Flask blueprint (`api/routes/historical/<sport>_games.py`) → sport-specific service
3. Service inherits from `BaseHistoricalService` (`api/services/historical/base_service.py`)
4. Direct PostgreSQL queries via `psycopg2` (no ORM for queries, though SQLAlchemy models exist)
5. Trends endpoints accept `{"games": [...], "limit": 5, "min_trend_length": 3}` in POST body and are cached for 1 hour

### Key data mapping: `shared_utils.py`
The Odds API uses full team names (e.g., `"Los Angeles Lakers"`) while the database stores short names (e.g., `"Lakers"`). `convert_team_name()` bridges this. The `teams` table maps names to IDs with a `sport` column stored as uppercase (e.g., `"NBA"`, `"NFL"`).

### Blueprint/service naming convention
Each sport follows: `api/routes/historical/<sport>_games.py` → `api/services/historical/<sport>_service.py`. Trends have their own parallel files (`<sport>_trends.py` / `<sport>_trends_service.py`).

### Database tables
Named `{sport_key}_games` (e.g., `nba_games`, `nfl_games`). Sport keys used in the codebase: `nba`, `nfl`, `mlb`, `nhl`, `ncaaf`, `ncaab`, `soccer` (with league variants like `epl`, `bundesliga`).

### Caching
`Flask-Caching` with `SimpleCache` in production; set `FLASK_ENV=development` to disable. Trends endpoints use custom cache keys derived from a hash of the sorted game IDs.

## Environment Variables

- `DATABASE_URL` — PostgreSQL connection string
- `ODDS_API_KEY` — Key for [the-odds-api.com](https://the-odds-api.com)
- `API_KEY` — Internal key sent in `X-API-KEY` header by the React frontend
- `FLASK_ENV` — Set to `development` to disable caching

## React Frontend

Lives in `getstam-react/`. The Flask app serves the built React app from `getstam-react/build/` and acts as a reverse proxy for API calls.
