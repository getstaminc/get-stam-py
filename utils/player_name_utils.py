#!/usr/bin/env python3

import unicodedata
import re
from typing import List, Tuple, Optional

def normalize_name(name: str) -> str:
    """
    Normalize a player name for consistent matching across different sources.
    
    Args:
        name: Raw player name from any source
        
    Returns:
        Normalized name (lowercase, no accents, no punctuation)
    """
    if not name:
        return ""
    
    # Remove unicode accents and diacritics
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove all non-letter characters except spaces
    name = re.sub(r"[^a-z\s]", "", name)
    
    # Collapse multiple spaces into single space and strip
    name = re.sub(r"\s+", " ", name).strip()
    
    return name


def extract_name_parts(name: str) -> dict:
    """
    Extract first, middle, and last name parts for better matching.
    
    Args:
        name: Full player name
        
    Returns:
        Dict with 'first', 'middle', 'last', 'suffix' keys
    """
    parts = name.strip().split()
    
    if not parts:
        return {'first': '', 'middle': '', 'last': '', 'suffix': ''}
    
    # Handle suffixes (Jr, Sr, III, etc)
    suffixes = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
    suffix = ''
    
    if len(parts) > 1 and parts[-1].lower().replace('.', '') in suffixes:
        suffix = parts.pop()
    
    if len(parts) == 1:
        return {'first': parts[0], 'middle': '', 'last': '', 'suffix': suffix}
    elif len(parts) == 2:
        return {'first': parts[0], 'middle': '', 'last': parts[1], 'suffix': suffix}
    else:
        # 3+ parts: first + middle(s) + last
        return {
            'first': parts[0], 
            'middle': ' '.join(parts[1:-1]), 
            'last': parts[-1], 
            'suffix': suffix
        }


def generate_name_variations(name: str) -> List[str]:
    """
    Generate common variations of a player name for alias matching.
    
    Args:
        name: Full player name
        
    Returns:
        List of name variations to try for matching
    """
    variations = []
    
    # Original normalized name
    normalized = normalize_name(name)
    variations.append(normalized)
    
    parts = extract_name_parts(normalized)
    first = parts['first']
    middle = parts['middle']
    last = parts['last']
    
    if not first or not last:
        return variations
    
    # Common variations
    variations.extend([
        f"{first} {last}",  # Drop middle
        f"{first[0]} {last}" if first else "",  # First initial + last
        f"{first} {middle[0]} {last}" if middle else "",  # Middle initial
        f"{first[0]} {middle[0]} {last}" if first and middle else "",  # Both initials
    ])
    
    # Handle hyphenated names
    if '-' in name:
        # Try without hyphens
        no_hyphen = name.replace('-', ' ')
        variations.append(normalize_name(no_hyphen))
    
    # Remove empty strings and duplicates
    variations = list(filter(None, set(variations)))
    
    return variations


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity score between two player names.
    Uses a combination of exact match, token matching, and character similarity.
    
    Args:
        name1: First name to compare
        name2: Second name to compare
        
    Returns:
        Similarity score between 0.0 and 1.0 (1.0 = identical)
    """
    # Normalize both names
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Exact match
    if norm1 == norm2:
        return 1.0
    
    # Token-based matching
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    # Jaccard similarity for tokens
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    token_similarity = intersection / union if union > 0 else 0.0
    
    # Character-level similarity (simple)
    char_similarity = len(set(norm1) & set(norm2)) / len(set(norm1) | set(norm2))
    
    # Combine scores with weights
    final_score = (token_similarity * 0.7) + (char_similarity * 0.3)
    
    return final_score


# Common NBA name mappings that we know will cause issues
KNOWN_NAME_MAPPINGS = {
    # Format: 'odds_api_name': 'espn_canonical_name'
    'j tatum': 'jayson tatum',
    'j williams': 'jaylin williams',  # This will need context
    'k towns': 'karl anthony towns',
    'rj barrett': 'rowan barrett jr',
    'og anunoby': 'ogugua anunoby',
    'sga': 'shai gilgeous alexander',
    'ant edwards': 'anthony edwards',
    'jjj': 'jaren jackson jr',
    'mpj': 'michael porter jr',
    'kg': 'kevin garnett',  # If he ever comes back :)
}


def get_manual_mapping(odds_name: str) -> Optional[str]:
    """
    Check if we have a manual mapping for this odds API name.
    
    Args:
        odds_name: Name from Odds API
        
    Returns:
        Canonical name if mapping exists, None otherwise
    """
    normalized = normalize_name(odds_name)
    return KNOWN_NAME_MAPPINGS.get(normalized)


if __name__ == "__main__":
    # Test the normalization functions
    test_names = [
        "Nikola Jokić",
        "Karl-Anthony Towns", 
        "J. Tatum",
        "Onyeka Okongwu",
        "Giannis Antetokounmpo",
        "Robert Williams III"
    ]
    
    print("=== Name Normalization Test ===")
    for name in test_names:
        normalized = normalize_name(name)
        variations = generate_name_variations(name)
        print(f"{name} -> {normalized}")
        print(f"  Variations: {variations}")
        print()