import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
engine = create_engine(DATABASE_URL)

def get_team_id_by_odds_api_team_name(team_name):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT team_id FROM teams WHERE odds_api_team_name = :name AND sport = 'NBA'"), {"name": team_name}).fetchone()
        if result:
            return result[0]
        return None
