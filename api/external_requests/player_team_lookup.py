import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from utils.player_name_utils import normalize_name

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
engine = create_engine(DATABASE_URL)

def get_team_id_for_player(player_name):
    normalized = normalize_name(player_name)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT team_id, id FROM nba_players WHERE normalized_name = :name"), {"name": normalized}).fetchone()
        if result:
            return result[0], result[1]
        return None, None
