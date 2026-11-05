import { VALUE_READ_EXAMPLES, exampleSportFor, ExampleSport } from './ValueRead';
import { getValueRead } from '../utils/valueRead';

jest.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isPro: false, user: null }) }));

// Each example's takeaway text describes these verdicts — keep them in sync if the math changes.
const EXPECTED: Record<ExampleSport, Record<string, string[]>> = {
  nfl: {
    'Chiefs vs Raiders': ['pass', 'value', 'value'],
    'Bills vs Dolphins': ['value', 'value', 'pass'],
    'Eagles vs Cowboys': ['fair', 'fair'],
  },
  ncaaf: {
    'Georgia vs Vanderbilt': ['pass', 'fair', 'value'],
    'Michigan vs Iowa': ['value', 'value', 'value'],
    'Texas vs Oklahoma': ['fair', 'fair'],
  },
  nba: {
    'Knicks vs Hornets': ['value', 'value', 'fair'],
    'Celtics vs Bucks': ['pass', 'fair', 'value'],
    'Magic vs Hornets': ['value', 'pass', 'fair'],
  },
  ncaab: {
    'Duke vs Wake Forest': ['pass', 'value', 'value'],
    "Gonzaga vs Saint Mary's": ['value', 'fair', 'fair'],
    'Kansas vs Baylor': ['fair', 'fair'],
  },
  nhl: {
    'Avalanche vs Blackhawks': ['pass', 'value', 'value'],
    'Panthers vs Sharks': ['value', 'pass', 'pass'],
    'Rangers vs Devils': ['fair', 'fair'],
  },
  mlb: {
    'Yankees vs Athletics': ['pass', 'value', 'value'],
    'Astros vs Rays': ['value', 'value', 'fair'],
    'Dodgers vs Giants': ['fair', 'fair'],
  },
  soccer: {
    'Man City vs Ipswich': ['pass', 'fair'],
    'Spurs vs Brentford': ['value', 'value'],
    'Arsenal vs Brighton': ['value', 'value'],
  },
};

const verdictsOf = (ex: (typeof VALUE_READ_EXAMPLES)['nba'][number]) =>
  ex.rows.map((r) => getValueRead(r.market, r.entry, ex.game)?.verdict);

describe('VALUE_READ_EXAMPLES', () => {
  const cases = (Object.keys(VALUE_READ_EXAMPLES) as ExampleSport[]).flatMap((sport) =>
    VALUE_READ_EXAMPLES[sport].map((ex) => [sport, ex.title, ex] as const));

  it.each(cases)('%s: %s lands on the verdicts its takeaway describes', (sport, title, ex) => {
    expect(verdictsOf(ex)).toEqual(EXPECTED[sport][title]);
  });

  it.each(Object.keys(VALUE_READ_EXAMPLES) as ExampleSport[])('%s includes a red PASS example', (sport) => {
    expect(VALUE_READ_EXAMPLES[sport].flatMap(verdictsOf)).toContain('pass');
  });
});

describe('exampleSportFor', () => {
  it.each([
    ['nfl', 'nfl'], ['americanfootball_nfl', 'nfl'],
    ['ncaaf', 'ncaaf'], ['americanfootball_ncaaf', 'ncaaf'],
    ['ncaab', 'ncaab'], ['basketball_ncaab', 'ncaab'],
    ['nba', 'nba'], ['basketball_nba', 'nba'],
    ['nhl', 'nhl'], ['icehockey_nhl', 'nhl'],
    ['mlb', 'mlb'], ['baseball_mlb', 'mlb'],
    ['epl', 'soccer'], ['laliga', 'soccer'], ['soccer_germany_bundesliga', 'soccer'],
  ])('maps %s → %s', (input, expected) => {
    expect(exampleSportFor(input)).toBe(expected);
  });
});
