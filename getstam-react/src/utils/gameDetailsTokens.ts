// Shared design tokens for the Game Details page redesign.
// Source of truth for exact values: the design handoff README
// (~/Downloads/design_handoff_game_details/README.md, "Design tokens" section).
export const gameDetailsTokens = {
  cardBg: '#ffffff',
  cardBorder: '#e6e7e3',
  cardRadius: 16,
  tableRadius: 12,
  subtlePanelBg: '#fafbf8',
  chipTrackBg: '#f1f3ef',
  trackBg2: '#eceee9',
  borders: {
    light: '#f1f2ee',
    lighter: '#f4f5f2',
  },
  text: {
    primary: '#14171c',
    secondary: '#5d636b',
    tertiary: '#8a9097',
    muted: '#9aa0a6',
  },
  link: '#1f5fd6',
  linkHover: '#163f8f',
  collisionIcon: '#5b3fd6',
  hit: {
    bg: '#e3f4ea',
    text: '#14713d',
    dot: '#1f9d55',
  },
  miss: {
    bg: '#fbe7e7',
    text: '#b42f2f',
  },
  // A draw/tie is a real game outcome, not a neutral "no info" state -- kept
  // visually distinct from trackBg2 (used for betting-line pushes) so it
  // doesn't read as blank/missing data, especially in sports like soccer
  // where draws are common.
  draw: {
    bg: '#e3ecfb',
    text: '#1d4ed8',
  },
  neutralBar: '#4a5361',
  shadowHover: '0 4px 14px rgba(0,0,0,.06)',
  shadowActiveSegment: '0 1px 2px rgba(0,0,0,.12)',
};

export default gameDetailsTokens;
