// static/js/filterSports.js

// Static list of allowed sports keys
const allowedSportsKeys = [
    'americanfootball_ncaaf', // NCAAF
    'americanfootball_nfl', // NFL
    'baseball_mlb', // MLB
    'basketball_nba', // NBA
    'basketball_ncaab', // NCAAB
    'boxing_boxing', // BOXING
    'icehockey_nhl', // NHL
    'mma_mixed_martial_arts', // MMA
    'soccer_epl', // EPL
    'soccer_france_ligue_one', // Ligue 1- France
    'soccer_germany_bundesliga', // Bundesliga- Germany
    'soccer_italy_serie_a', // Serie A Italy
    'soccer_spain_la_liga', // La Liga- Spain
    'soccer_uefa_champs_league', // UEFA Champions League
    'soccer_uefa_europa_league' // Uefa Europa League
];

// Function to filter sports based on the static list of allowed sports keys
function filterSports(data) {
    return data.filter(sport => allowedSportsKeys.includes(sport.key));
}

// Export the function if using ES6 modules
export { filterSports };