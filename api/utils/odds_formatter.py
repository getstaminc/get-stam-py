"""
Odds formatting utilities for processing betting data
"""

def extract_scores(match):
    """Extract home and away scores from match data"""
    home_score = None
    away_score = None
    
    if match.get('scores'):
        try:
            home_score = int(match['scores'][0]['score'])
        except (KeyError, ValueError, TypeError):
            home_score = None
        try:
            away_score = int(match['scores'][1]['score'])
        except (KeyError, ValueError, TypeError):
            away_score = None
    
    return home_score, away_score

def initialize_odds_structure():
    """Initialize empty odds structure"""
    home_odds = {"h2h": None, "spread_point": None, "spread_price": None}
    away_odds = {"h2h": None, "spread_point": None, "spread_price": None}
    totals = {"over_point": None, "over_price": None, "under_point": None, "under_price": None}
    
    return home_odds, away_odds, totals

def process_market_outcomes(market, home_team, away_team, home_odds, away_odds, totals):
    """Process outcomes for a specific market (h2h, spreads, totals)"""
    market_key = market['key']
    
    if market_key == "h2h":
        for outcome in market['outcomes']:
            price = int(outcome['price']) if 'price' in outcome else None
            if outcome['name'] == home_team:
                home_odds["h2h"] = price
            elif outcome['name'] == away_team:
                away_odds["h2h"] = price
                
    elif market_key == "spreads":
        for outcome in market['outcomes']:
            point = float(outcome['point']) if 'point' in outcome else None
            price = int(outcome['price']) if 'price' in outcome else None
            if outcome['name'] == home_team:
                home_odds["spread_point"] = point
                home_odds["spread_price"] = price
            elif outcome['name'] == away_team:
                away_odds["spread_point"] = point
                away_odds["spread_price"] = price
                
    elif market_key == "totals":
        for outcome in market['outcomes']:
            point = float(outcome['point']) if 'point' in outcome else None
            price = int(outcome['price']) if 'price' in outcome else None
            if outcome['name'].lower() == "over":
                totals["over_point"] = point
                totals["over_price"] = price
            elif outcome['name'].lower() == "under":
                totals["under_point"] = point
                totals["under_price"] = price

def process_odds_data(match, odds, home_team, away_team):
    """Process all odds data for a match"""
    home_odds, away_odds, totals = initialize_odds_structure()
    
    match_odds = next((o for o in odds if o['id'] == match['id']), None)
    
    if match_odds:
        for bookmaker in match_odds['bookmakers']:
            for market in bookmaker['markets']:
                process_market_outcomes(market, home_team, away_team, home_odds, away_odds, totals)
    
    return home_odds, away_odds, totals
