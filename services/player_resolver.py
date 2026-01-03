#!/usr/bin/env python3

import os
import sys
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.player_name_utils import (
    normalize_name, 
    generate_name_variations,
    calculate_name_similarity,
    get_manual_mapping
)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")


class PlayerResolver:
    """
    Service for resolving player identities across different data sources.
    Handles exact matching, alias lookup, fuzzy matching, and player creation.
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize the player resolver.
        
        Args:
            db_connection: Optional existing database connection
        """
        if db_connection:
            self.conn = db_connection
            self.own_connection = False
        else:
            engine = create_engine(DATABASE_URL)
            self.conn = engine.connect()
            self.own_connection = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.own_connection and self.conn:
            self.conn.close()
    
    def resolve_player_from_odds_api(self, odds_name: str, game_date: date) -> int:
        """
        Resolve a player from Odds API name to database player_id.
        Creates player if not found.
        
        Args:
            odds_name: Player name from Odds API
            game_date: Date of the game
            
        Returns:
            player_id in the database
        """
        print(f"Resolving Odds API player: '{odds_name}'")
        
        # Step 1: Check manual mappings first
        manual_mapping = get_manual_mapping(odds_name)
        if manual_mapping:
            print(f"  Found manual mapping: {odds_name} -> {manual_mapping}")
            odds_name = manual_mapping
        
        # Step 2: Normalize the name
        normalized = normalize_name(odds_name)
        if not normalized:
            print(f"  Warning: Could not normalize name '{odds_name}'")
            return self._create_placeholder_player(odds_name, game_date)
        
        # Step 3: Try exact alias match (fastest)
        player_id = self._find_by_alias(normalized, 'odds_api')
        if player_id:
            print(f"  Found by odds_api alias: {player_id}")
            return player_id
        
        # Step 4: Try exact player name match
        player_id = self._find_by_normalized_name(normalized)
        if player_id:
            print(f"  Found by exact name match: {player_id}")
            # Add odds_api alias for future lookups
            self._add_player_alias(player_id, 'odds_api', odds_name, normalized)
            return player_id
        
        # Step 5: Try name variations
        variations = generate_name_variations(odds_name)
        for variation in variations:
            if variation != normalized:  # Skip already tried
                player_id = self._find_by_normalized_name(variation)
                if player_id:
                    print(f"  Found by variation '{variation}': {player_id}")
                    self._add_player_alias(player_id, 'odds_api', odds_name, normalized)
                    return player_id
        
        # Step 6: Fuzzy matching (careful threshold)
        player_id = self._fuzzy_match_player(normalized)
        if player_id:
            print(f"  Found by fuzzy match: {player_id}")
            self._add_player_alias(player_id, 'odds_api', odds_name, normalized)
            return player_id
        
        # Step 7: Create new placeholder player
        print(f"  No match found, creating placeholder player")
        return self._create_placeholder_player(odds_name, game_date)
    
    def resolve_player_from_espn(self, espn_athlete: dict, game_date: date) -> int:
        """
        Resolve/upsert a player from ESPN athlete data.
        ESPN is authoritative, so this always succeeds.
        
        Args:
            espn_athlete: ESPN athlete object with 'id' and 'displayName'
            game_date: Date of the game
            
        Returns:
            player_id in the database
        """
        espn_id = str(espn_athlete.get('id', ''))
        espn_name = espn_athlete.get('displayName', '')
        
        print(f"Resolving ESPN player: {espn_name} (ID: {espn_id})")
        
        if not espn_id or not espn_name:
            raise ValueError(f"Invalid ESPN athlete data: {espn_athlete}")
        
        # Check if player already exists by ESPN ID
        existing = self.conn.execute(text("""
            SELECT id FROM nba_players WHERE espn_player_id = :espn_id
        """), {'espn_id': espn_id}).fetchone()
        
        normalized = normalize_name(espn_name)
        position = espn_athlete.get('position', {}).get('abbreviation', '')
        
        if existing:
            player_id = existing[0]
            print(f"  Updating existing player: {player_id}")
            
            # Update player info
            self.conn.execute(text("""
                UPDATE nba_players 
                SET espn_player_name = :name,
                    normalized_name = :normalized,
                    position = :position,
                    last_seen_date = :date,
                    updated_at = now()
                WHERE id = :player_id
            """), {
                'name': espn_name,
                'normalized': normalized,
                'position': position,
                'date': game_date,
                'player_id': player_id
            })
        else:
            print(f"  Creating new player from ESPN data")
            
            # Create new player
            result = self.conn.execute(text("""
                INSERT INTO nba_players (
                    espn_player_id, espn_player_name, normalized_name,
                    position, first_seen_date, last_seen_date
                ) VALUES (
                    :espn_id, :name, :normalized,
                    :position, :date, :date
                ) RETURNING id
            """), {
                'espn_id': espn_id,
                'name': espn_name,
                'normalized': normalized,
                'position': position,
                'date': game_date
            })
            
            player_id = result.scalar()
        
        # Always add/update ESPN alias
        self._add_player_alias(player_id, 'espn', espn_name, normalized)
        
        # If this was a placeholder player (espn_player_id starts with 'pending_'),
        # we need to upgrade it
        self._upgrade_placeholder_player(player_id, espn_id, espn_name, normalized, game_date)
        
        print(f"  ESPN player resolved to ID: {player_id}")
        return player_id
    
    def _find_by_alias(self, normalized_name: str, source: str) -> Optional[int]:
        """Find player by existing alias."""
        result = self.conn.execute(text("""
            SELECT p.id
            FROM nba_player_aliases a
            JOIN nba_players p ON p.id = a.player_id
            WHERE a.source = :source AND a.normalized_name = :name
        """), {'source': source, 'name': normalized_name}).fetchone()
        
        return result[0] if result else None
    
    def _find_by_normalized_name(self, normalized_name: str) -> Optional[int]:
        """Find player by normalized name in nba_players table."""
        result = self.conn.execute(text("""
            SELECT id FROM nba_players WHERE normalized_name = :name
        """), {'name': normalized_name}).fetchone()
        
        return result[0] if result else None
    
    def _fuzzy_match_player(self, normalized_name: str, threshold: float = 0.92) -> Optional[int]:
        """
        Attempt fuzzy matching against existing players.
        High threshold to avoid false matches.
        """
        # Get all existing player names
        existing_players = self.conn.execute(text("""
            SELECT id, normalized_name, espn_player_name
            FROM nba_players
            WHERE espn_player_id NOT LIKE 'pending_%'  -- Skip placeholders
        """)).fetchall()
        
        best_match = None
        best_score = 0.0
        
        for player_id, player_normalized, player_espn in existing_players:
            # Try both normalized and original name
            score1 = calculate_name_similarity(normalized_name, player_normalized)
            score2 = calculate_name_similarity(normalized_name, normalize_name(player_espn))
            
            score = max(score1, score2)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = player_id
        
        if best_match:
            print(f"    Fuzzy match found (score: {best_score:.3f})")
        
        return best_match
    
    def _add_player_alias(self, player_id: int, source: str, source_name: str, normalized_name: str):
        """Add an alias for a player."""
        try:
            self.conn.execute(text("""
                INSERT INTO nba_player_aliases (player_id, source, source_name, normalized_name)
                VALUES (:player_id, :source, :source_name, :normalized)
                ON CONFLICT (source, normalized_name) DO NOTHING
            """), {
                'player_id': player_id,
                'source': source,
                'source_name': source_name,
                'normalized': normalized_name
            })
            print(f"    Added alias: {source} -> '{source_name}'")
        except Exception as e:
            print(f"    Warning: Could not add alias: {e}")
    
    def _create_placeholder_player(self, odds_name: str, game_date: date) -> int:
        """Create a placeholder player that will be upgraded when ESPN data is available."""
        normalized = normalize_name(odds_name)
        pending_id = f"pending_{normalized.replace(' ', '_')}"
        
        # Check if placeholder already exists
        existing = self.conn.execute(text("""
            SELECT id FROM nba_players WHERE espn_player_id = :pending_id
        """), {'pending_id': pending_id}).fetchone()
        
        if existing:
            return existing[0]
        
        # Create new placeholder
        result = self.conn.execute(text("""
            INSERT INTO nba_players (
                espn_player_id, espn_player_name, normalized_name,
                first_seen_date, last_seen_date
            ) VALUES (
                :pending_id, :name, :normalized, :date, :date
            ) RETURNING id
        """), {
            'pending_id': pending_id,
            'name': odds_name,
            'normalized': normalized,
            'date': game_date
        })
        
        player_id = result.scalar()
        
        # Add odds_api alias
        self._add_player_alias(player_id, 'odds_api', odds_name, normalized)
        
        print(f"    Created placeholder player: {player_id}")
        return player_id
    
    def _upgrade_placeholder_player(self, player_id: int, espn_id: str, espn_name: str, normalized: str, game_date: date):
        """Upgrade a placeholder player with real ESPN data."""
        # Check if this is a placeholder
        current = self.conn.execute(text("""
            SELECT espn_player_id FROM nba_players WHERE id = :player_id
        """), {'player_id': player_id}).fetchone()
        
        if current and current[0].startswith('pending_'):
            print(f"    Upgrading placeholder player {player_id} with ESPN ID {espn_id}")
            
            self.conn.execute(text("""
                UPDATE nba_players 
                SET espn_player_id = :espn_id,
                    espn_player_name = :espn_name,
                    normalized_name = :normalized,
                    last_seen_date = :date,
                    updated_at = now()
                WHERE id = :player_id
            """), {
                'espn_id': espn_id,
                'espn_name': espn_name,
                'normalized': normalized,
                'date': game_date,
                'player_id': player_id
            })
    
    def get_player_info(self, player_id: int) -> Optional[Dict]:
        """Get full player information by ID."""
        result = self.conn.execute(text("""
            SELECT id, espn_player_id, espn_player_name, normalized_name,
                   position, team_id, first_seen_date, last_seen_date
            FROM nba_players 
            WHERE id = :player_id
        """), {'player_id': player_id}).fetchone()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'espn_player_id': result[1],
            'espn_player_name': result[2],
            'normalized_name': result[3],
            'position': result[4],
            'team_id': result[5],
            'first_seen_date': result[6],
            'last_seen_date': result[7]
        }


if __name__ == "__main__":
    # Test the player resolver
    test_date = date.today()
    
    with PlayerResolver() as resolver:
        # Test odds API resolution
        print("=== Testing Odds API Resolution ===")
        test_odds_names = [
            "Nikola Jokic",
            "J. Tatum",
            "Karl-Anthony Towns",
            "Unknown Player"
        ]
        
        for name in test_odds_names:
            try:
                player_id = resolver.resolve_player_from_odds_api(name, test_date)
                info = resolver.get_player_info(player_id)
                print(f"'{name}' -> Player ID {player_id}: {info['espn_player_name']}")
            except Exception as e:
                print(f"Error resolving '{name}': {e}")
            print()
        
        # Test ESPN resolution
        print("=== Testing ESPN Resolution ===")
        test_espn_athletes = [
            {"id": "4431680", "displayName": "Nikola Jokic", "position": {"abbreviation": "C"}},
            {"id": "4066648", "displayName": "Jayson Tatum", "position": {"abbreviation": "F"}}
        ]
        
        for athlete in test_espn_athletes:
            try:
                player_id = resolver.resolve_player_from_espn(athlete, test_date)
                info = resolver.get_player_info(player_id)
                print(f"ESPN {athlete['displayName']} -> Player ID {player_id}")
            except Exception as e:
                print(f"Error resolving ESPN athlete {athlete}: {e}")
            print()