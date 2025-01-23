import pytz

eastern_tz = pytz.timezone('US/Eastern')

def convert_to_eastern(utc_time):
    if utc_time is None:
        return None
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    eastern_time = utc_time.astimezone(eastern_tz)
    return eastern_time

def convert_team_name(full_team_name):
    # Dummy implementation for converting team names
    return full_team_name

def convert_sport_key(sport_key):
    sport_mapping = {
        'americanfootball_nfl': 'NFL',
        'americanfootball_nfl_preseason': 'NFL',
        'icehockey_nhl': 'NHL',
        'americanfootball_ncaaf': 'NCAAFB',
        'basketball_ncaab': 'NCAABB'
        # Add other mappings as needed
    }
    return sport_mapping.get(sport_key, sport_key)