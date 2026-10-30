import { buildGameDetailsLink, MATCHUP_SLUG_SPORTS } from './teamSlugUtils';
import { decodeGameId } from './gameIdCrypto';

describe('buildGameDetailsLink', () => {
  const fullGame = {
    game_id: 'ab12',
    home: { team: 'Lille' },
    away: { team: 'RC Lens' },
    commence_time: '2026-10-30T19:00:00Z',
  };

  it('builds a pretty slug URL for a sport with team-slug support', () => {
    expect(MATCHUP_SLUG_SPORTS.has('nba')).toBe(true);
    const link = buildGameDetailsLink('nba', fullGame);
    expect(link).toBe('/game-details/nba/rc-lens-vs-lille-2026-10-30');
  });

  it('falls back to the query-param URL for soccer, which has no team-slug support', () => {
    // Regression test: HomePage.tsx previously built a slug URL for every sport
    // unconditionally, including soccer -- but soccer has no slug-resolution
    // support on either the frontend (SPORT_MAPS) or backend
    // (api/utils/team_slugs.py's SPORT_TEAMS), so clicking "Game Details" from
    // a soccer card 404'd. This must stay on the query-param route.
    expect(MATCHUP_SLUG_SPORTS.has('ligue1')).toBe(false);
    const link = buildGameDetailsLink('ligue1', fullGame);
    expect(link.startsWith('/game-details/ligue1?game_id=')).toBe(true);
    const encoded = link.split('game_id=')[1];
    expect(decodeGameId(encoded)).toBe('ab12');
  });

  it('falls back to the query-param URL when team names or commence_time are missing, even for a supported sport', () => {
    const link = buildGameDetailsLink('nba', { game_id: 'ab12', home: { team: 'Lille' } });
    expect(link.startsWith('/game-details/nba?game_id=')).toBe(true);
    expect(decodeGameId(link.split('game_id=')[1])).toBe('ab12');
  });
});
