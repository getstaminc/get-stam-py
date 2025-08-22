# espn.py

from flask import jsonify
from nfl_rankings import fetch_nfl_rankings
from ncaaf_rankings import fetch_ncaaf_rankings

def get_nfl_rankings():
    """Get NFL team rankings for offense and defense"""
    try:
        rankings_data = fetch_nfl_rankings()
        print("Rankings data fetched successfully11111")
        
        # Clean up the field names for better formatting
        def clean_stats(stats):
            cleaned = {}
            for key, value in stats.items():
                # Remove "(Yds/G)" and "(Pts/G)" from keys
                clean_key = key.replace(" (Yds/G)", "").replace(" (Pts/G)", "")
                cleaned[clean_key] = value
            return cleaned
        
        # Transform the data into a more structured format for your React app
        formatted_rankings = {}
        
        # Get all team names from offense data (they should be the same in both)
        offense_teams = rankings_data.get('offense', {})
        defense_teams = rankings_data.get('defense', {})
        
        for team_name in offense_teams.keys():
            # Skip abbreviations, only process full team names
            if len(team_name) > 3:  # Assuming abbreviations are 3 chars or less
                offense_stats = offense_teams.get(team_name, {})
                defense_stats = defense_teams.get(team_name, {})
                
                formatted_rankings[team_name] = {
                    'offense': clean_stats(offense_stats),
                    'defense': clean_stats(defense_stats)
                }
        
        return jsonify({
            'rankings': formatted_rankings,
            'teams_count': len(formatted_rankings)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch NFL rankings: {str(e)}'}), 500


def get_ncaaf_rankings():
    """Get NCAAF team rankings for offense and defense"""
    try:
        rankings_data = fetch_ncaaf_rankings()
        print("NCAAF rankings data fetched successfully")
        
        # Clean up the field names for better formatting
        def clean_stats(stats):
            cleaned = {}
            for key, value in stats.items():
                # Remove "(Yds/G)" and "(Pts/G)" from keys
                clean_key = key.replace(" (Yds/G)", "").replace(" (Pts/G)", "")
                cleaned[clean_key] = value
            return cleaned
        
        # Transform the data into a more structured format for your React app
        formatted_rankings = {}
        
        # Get all team names from offense data (they should be the same in both)
        offense_teams = rankings_data.get('offense', {})
        defense_teams = rankings_data.get('defense', {})
        
        for team_name in offense_teams.keys():
            # Skip abbreviations, only process full team names
            if len(team_name) > 3:  # Assuming abbreviations are 3 chars or less
                offense_stats = offense_teams.get(team_name, {})
                defense_stats = defense_teams.get(team_name, {})
                
                formatted_rankings[team_name] = {
                    'offense': clean_stats(offense_stats),
                    'defense': clean_stats(defense_stats)
                }
        
        return jsonify({
            'rankings': formatted_rankings,
            'teams_count': len(formatted_rankings)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch NCAAF rankings: {str(e)}'}), 500
