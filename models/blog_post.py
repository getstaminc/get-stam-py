from sqlalchemy import Column, Date, Integer, String, Text, TIMESTAMP, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from .base import Base


class BlogPost(Base):
    __tablename__ = 'blog_posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    youtube_video_id = Column(String(20), unique=True, nullable=True)
    youtube_title = Column(String(500), nullable=True)
    youtube_description = Column(Text, nullable=True)
    youtube_thumbnail_url = Column(String(500), nullable=True)
    youtube_published_at = Column(TIMESTAMP, nullable=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(600), unique=True, nullable=False)
    meta_description = Column(String(200), nullable=True)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    tags = Column(postgresql.ARRAY(String), nullable=True)
    reading_time_minutes = Column(Integer, nullable=True)
    og_image_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default='draft')
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(TIMESTAMP, nullable=True)
    category = Column(String(50), nullable=True)
    sport = Column(String(20), nullable=True)
    sport_key = Column(String(50), nullable=True)
    home_team = Column(String(100), nullable=True)
    away_team = Column(String(100), nullable=True)
    odds_event_id = Column(String(255), nullable=True)
    game_date = Column(Date, nullable=True)
    game_data = Column(postgresql.JSONB, nullable=True)
