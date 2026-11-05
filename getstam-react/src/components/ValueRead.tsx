import React, { useState } from "react";
import { Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions } from "@mui/material";
import LockIcon from "@mui/icons-material/Lock";
import { ValueRead, ValueVerdict, getValueRead } from "../utils/valueRead";
import { MarketOverviewEntry } from "../utils/trendAnalysis";
import { gameDetailsTokens as tokens } from "../utils/gameDetailsTokens";
import UpgradeDialog from "./UpgradeDialog";

const VERDICT_STYLE: Record<ValueVerdict, { label: string; bg: string; text: string; bar: string }> = {
  value: { label: "VALUE", bg: tokens.hit.bg, text: tokens.hit.text, bar: tokens.hit.dot },
  fair: { label: "FAIR", bg: tokens.chipTrackBg, text: tokens.text.secondary, bar: tokens.neutralBar },
  pass: { label: "PASS", bg: tokens.miss.bg, text: tokens.miss.text, bar: tokens.miss.text },
};

const fmtPrice = (price: number) => (price > 0 ? `+${price}` : String(price));
const fmtPct = (rate: number) => `${(rate * 100).toFixed(1)}%`;

const Chip: React.FC<{ bg: string; color: string; children: React.ReactNode }> = ({ bg, color, children }) => (
  <Box sx={{
    px: 1, py: 0.25, borderRadius: "999px", bgcolor: bg, color,
    fontSize: "0.62rem", fontWeight: 800, letterSpacing: "0.06em",
    display: "inline-flex", alignItems: "center", gap: 0.4, whiteSpace: "nowrap",
  }}>
    {children}
  </Box>
);

const Bar: React.FC<{ fill: number; tick: number; color: string }> = ({ fill, tick, color }) => (
  <Box sx={{ position: "relative", flex: 1, height: 6, borderRadius: "999px", bgcolor: tokens.trackBg2 }}>
    <Box sx={{ position: "absolute", inset: 0, width: `${Math.min(fill, 1) * 100}%`, borderRadius: "999px", bgcolor: color }} />
    <Box sx={{ position: "absolute", top: -3, bottom: -3, left: `${tick * 100}%`, width: 2, bgcolor: tokens.text.primary, borderRadius: 1 }} />
  </Box>
);

/** Bar + verdict chip + break-even line for one Overview market row (Pro view). */
export const ValueReadRow: React.FC<{ probability: number; read: ValueRead }> = ({ probability, read }) => {
  const style = VERDICT_STYLE[read.verdict];
  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
        <Bar fill={probability} tick={read.breakEven} color={style.bar} />
        <Chip bg={style.bg} color={style.text}>{style.label}</Chip>
      </Box>
      <Typography sx={{ fontSize: "0.7rem", color: tokens.text.tertiary, mt: 0.25 }}>
        {fmtPrice(read.price)} needs {fmtPct(read.breakEven)} to break even
      </Typography>
    </Box>
  );
};

const verdictLineLayout = { display: "flex", alignItems: "center", gap: 1, mt: 0.5 } as const;

/** Chip + break-even line without a bar — for cards that already draw their own bar (Game Details). */
export const ValueVerdictLine: React.FC<{ read: ValueRead | null; isPro: boolean; onUnlock: () => void }> = ({ read, isPro, onUnlock }) => {
  if (!read) return null;
  if (!isPro) {
    return (
      <Box
        component="button"
        type="button"
        onClick={onUnlock}
        aria-label="Unlock Value Read with Pro"
        sx={{ ...verdictLineLayout, width: "100%", p: 0, border: "none", background: "none", cursor: "pointer", textAlign: "left" }}
      >
        <Chip bg={tokens.text.primary} color="#fff"><LockIcon sx={{ fontSize: "0.7rem" }} /> PRO</Chip>
        <Typography aria-hidden sx={{ fontSize: "0.75rem", color: tokens.text.tertiary, filter: "blur(3px)", userSelect: "none" }}>
          -110 needs 52.4% to break even
        </Typography>
      </Box>
    );
  }
  const style = VERDICT_STYLE[read.verdict];
  return (
    <Box sx={verdictLineLayout}>
      <Chip bg={style.bg} color={style.text}>{style.label}</Chip>
      <Typography sx={{ fontSize: "0.75rem", color: tokens.text.tertiary }}>
        {fmtPrice(read.price)} needs {fmtPct(read.breakEven)} to break even
      </Typography>
    </Box>
  );
};

/** Free-tier teaser: the same shape, blurred over placeholder values so no real read leaks. */
export const LockedValueRow: React.FC<{ onUnlock: () => void }> = ({ onUnlock }) => (
  <Box
    component="button"
    type="button"
    onClick={onUnlock}
    aria-label="Unlock Value Read with Pro"
    sx={{ display: "block", width: "100%", p: 0, m: 0, border: "none", background: "none", cursor: "pointer", textAlign: "left" }}
  >
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
      <Box aria-hidden sx={{ flex: 1, display: "flex", filter: "blur(3px)", opacity: 0.7 }}>
        <Bar fill={0.6} tick={0.52} color={tokens.hit.dot} />
      </Box>
      <Chip bg={tokens.text.primary} color="#fff">
        <LockIcon sx={{ fontSize: "0.7rem" }} /> PRO
      </Chip>
    </Box>
    <Typography aria-hidden sx={{ fontSize: "0.7rem", color: tokens.text.tertiary, mt: 0.25, filter: "blur(3px)", userSelect: "none" }}>
      -110 needs 52.4% to break even
    </Typography>
  </Box>
);

// Static demos for the preview dialog. Numbers are chosen so the real math
// lands on the verdict each takeaway describes (see ValueRead.test.tsx).
type SampleRow = { market: "moneyline" | "spread" | "total"; label: string; pick: string; entry: MarketOverviewEntry };
export interface ValueReadExample { title: string; takeaway: string; game: any; rows: SampleRow[] }

const row = (market: SampleRow["market"], label: string, pick: string, lean: string, probability: number, sample_size: number): SampleRow =>
  ({ market, label, pick, entry: { lean, probability, trend_count: 2, sample_size, contributing_trends: [] } });

const odds = (homeTeam: string, awayTeam: string, homeH2h: number, awayH2h: number, homeSpread: [number, number], awaySpread: [number, number], total: [number, number, number]) => ({
  home: { team: homeTeam, odds: { h2h: homeH2h, spread_point: homeSpread[0], spread_price: homeSpread[1] } },
  away: { team: awayTeam, odds: { h2h: awayH2h, spread_point: awaySpread[0], spread_price: awaySpread[1] } },
  totals: { over_point: total[0], over_price: total[1], under_point: total[0], under_price: total[2] },
});

export type ExampleSport = "nfl" | "ncaaf" | "nba" | "ncaab" | "nhl" | "mlb" | "soccer";

// Each sport tells the same three stories: a steep favorite that's a PASS, an
// underdog that's VALUE, and a thin sample pulled back to FAIR.
export const VALUE_READ_EXAMPLES: Record<ExampleSport, ValueReadExample[]> = {
  nfl: [
    {
      title: "Chiefs vs Raiders",
      takeaway: "Teams in the Chiefs' spot won 74% of past games, but −400 needs 80%. Strong lean, bad price.",
      game: odds("Chiefs", "Raiders", -400, 310, [-9.5, -110], [9.5, -110], [44.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Chiefs", "Chiefs", 0.74, 40),
        row("spread", "Spread", "Chiefs -9.5", "Chiefs", 0.55, 40),
        row("total", "Total", "Under 44.5", "Under", 0.58, 30),
      ],
    },
    {
      title: "Bills vs Dolphins",
      takeaway: "Teams in the Dolphins' spot only won 46%, but at +150 the Dolphins only need 40%. Underdogs can be value.",
      game: odds("Bills", "Dolphins", -180, 150, [-3.5, -110], [3.5, -110], [47.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Dolphins", "Dolphins", 0.46, 30),
        row("spread", "Spread", "Dolphins +3.5", "Dolphins", 0.56, 30),
        row("total", "Total", "Over 47.5", "Over", 0.49, 30),
      ],
    },
    {
      title: "Eagles vs Cowboys",
      takeaway: "70% sounds great, but it's only 5 past games. We pull thin samples toward break-even.",
      game: odds("Eagles", "Cowboys", -200, 170, [-4.5, -110], [4.5, -110], [46.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Eagles", "Eagles", 0.7, 5),
        row("spread", "Spread", "Eagles -4.5", "Eagles", 0.58, 5),
      ],
    },
  ],
  ncaaf: [
    {
      title: "Georgia vs Vanderbilt",
      takeaway: "Teams in Georgia's spot won 88% of past games, but −1200 needs 92%. Even big favorites can be a pass.",
      game: odds("Georgia", "Vanderbilt", -1200, 750, [-24.5, -110], [24.5, -110], [52.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Georgia", "Georgia", 0.88, 40),
        row("spread", "Spread", "Georgia -24.5", "Georgia", 0.53, 40),
        row("total", "Total", "Under 52.5", "Under", 0.6, 30),
      ],
    },
    {
      title: "Michigan vs Iowa",
      takeaway: "Teams in Iowa's spot only won 42%, but at +190 Iowa only needs 34.5%. Underdogs can be value.",
      game: odds("Michigan", "Iowa", -230, 190, [-6.5, -110], [6.5, -110], [38.5, -115, -105]),
      rows: [
        row("moneyline", "Moneyline", "Iowa", "Iowa", 0.42, 30),
        row("spread", "Spread", "Iowa +6.5", "Iowa", 0.58, 30),
        row("total", "Total", "Under 38.5", "Under", 0.57, 30),
      ],
    },
    {
      title: "Texas vs Oklahoma",
      takeaway: "70% sounds great, but it's only 5 past games. We pull thin samples toward break-even.",
      game: odds("Texas", "Oklahoma", -200, 170, [-4.5, -110], [4.5, -110], [55.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Texas", "Texas", 0.7, 5),
        row("spread", "Spread", "Texas -4.5", "Texas", 0.57, 5),
      ],
    },
  ],
  nba: [
    {
      title: "Knicks vs Hornets",
      takeaway: "A modest favorite at a fair price: the trend rate clears break-even.",
      game: odds("Knicks", "Hornets", -120, 100, [-4.5, -110], [4.5, -110], [221.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Knicks", "Knicks", 0.6, 25),
        row("spread", "Spread", "Knicks -4.5", "Knicks", 0.58, 25),
        row("total", "Total", "Over 221.5", "Over", 0.54, 25),
      ],
    },
    {
      title: "Celtics vs Bucks",
      takeaway: "Teams in the Celtics' spot won 70% of past games, but −500 needs 83%. Strong lean, bad price.",
      game: odds("Celtics", "Bucks", -500, 380, [-11.5, -112], [11.5, -108], [225.5, -115, -105]),
      rows: [
        row("moneyline", "Moneyline", "Celtics", "Celtics", 0.7, 40),
        row("spread", "Spread", "Celtics -11.5", "Celtics", 0.52, 40),
        row("total", "Total", "Under 225.5", "Under", 0.62, 30),
      ],
    },
    {
      title: "Magic vs Hornets",
      takeaway: "Teams in the Hornets' spot only won 40%, but at +210 the Hornets only need 32%. Underdogs can be value.",
      game: odds("Magic", "Hornets", -260, 210, [-6.5, -110], [6.5, -110], [214.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Hornets", "Hornets", 0.4, 30),
        row("spread", "Spread", "Hornets +6.5", "Hornets", 0.47, 30),
        row("total", "Total", "Over 214.5", "Over", 0.5, 30),
      ],
    },
  ],
  ncaab: [
    {
      title: "Duke vs Wake Forest",
      takeaway: "Teams in Duke's spot won 78% of past games, but −600 needs 86%. Strong lean, bad price.",
      game: odds("Duke", "Wake Forest", -600, 425, [-13.5, -110], [13.5, -110], [151.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Duke", "Duke", 0.78, 40),
        row("spread", "Spread", "Duke -13.5", "Duke", 0.55, 40),
        row("total", "Total", "Under 151.5", "Under", 0.59, 30),
      ],
    },
    {
      title: "Gonzaga vs Saint Mary's",
      takeaway: "Teams in Saint Mary's spot only won 36%, but at +240 Saint Mary's only needs 29%. Underdogs can be value.",
      game: odds("Gonzaga", "Saint Mary's", -300, 240, [-7.5, -110], [7.5, -110], [138.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Saint Mary's", "Saint Mary's", 0.36, 30),
        row("spread", "Spread", "Saint Mary's +7.5", "Saint Mary's", 0.55, 30),
        row("total", "Total", "Under 138.5", "Under", 0.5, 30),
      ],
    },
    {
      title: "Kansas vs Baylor",
      takeaway: "72% sounds great, but it's only 5 past games. We pull thin samples toward break-even.",
      game: odds("Kansas", "Baylor", -220, 185, [-5.5, -110], [5.5, -110], [144.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Kansas", "Kansas", 0.72, 5),
        row("spread", "Spread", "Kansas -5.5", "Kansas", 0.57, 6),
      ],
    },
  ],
  nhl: [
    {
      title: "Avalanche vs Blackhawks",
      takeaway: "Teams in the Avs' spot won 68% of past games, but −280 needs 74%. Strong lean, bad price.",
      game: odds("Avalanche", "Blackhawks", -280, 230, [-1.5, -110], [1.5, -110], [6.5, 100, -120]),
      rows: [
        row("moneyline", "Moneyline", "Avalanche", "Avalanche", 0.68, 40),
        row("spread", "Puck line", "Avalanche -1.5", "Avalanche", 0.55, 40),
        row("total", "Total", "Over 6.5", "Over", 0.55, 30),
      ],
    },
    {
      title: "Panthers vs Sharks",
      takeaway: "Teams in the Sharks' spot only won 45%, but at +165 the Sharks only need 38%. Underdogs can be value.",
      game: odds("Panthers", "Sharks", -195, 165, [-1.5, 140], [1.5, -165], [6.5, -120, 100]),
      rows: [
        row("moneyline", "Moneyline", "Sharks", "Sharks", 0.45, 30),
        row("spread", "Puck line", "Panthers -1.5", "Panthers", 0.38, 30),
        row("total", "Total", "Over 6.5", "Over", 0.48, 30),
      ],
    },
    {
      title: "Rangers vs Devils",
      takeaway: "67% sounds great, but it's only 5 past games. We pull thin samples toward break-even.",
      game: odds("Rangers", "Devils", -175, 150, [-1.5, 160], [1.5, -190], [5.5, 100, -115]),
      rows: [
        row("moneyline", "Moneyline", "Rangers", "Rangers", 0.67, 5),
        row("total", "Total", "Under 5.5", "Under", 0.58, 5),
      ],
    },
  ],
  mlb: [
    {
      title: "Yankees vs Athletics",
      takeaway: "Teams in the Yankees' spot won 66% of past games, but −230 needs 70%. Strong lean, bad price.",
      game: odds("Yankees", "Athletics", -230, 190, [-1.5, 105], [1.5, -125], [8.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Yankees", "Yankees", 0.66, 40),
        row("spread", "Run line", "Yankees -1.5", "Yankees", 0.52, 40),
        row("total", "Total", "Over 8.5", "Over", 0.58, 30),
      ],
    },
    {
      title: "Astros vs Rays",
      takeaway: "Teams in the Rays' spot only won 48%, but at +135 the Rays only need 43%. Underdogs can be value.",
      game: odds("Astros", "Rays", -155, 135, [-1.5, 140], [1.5, -160], [7.5, -115, -105]),
      rows: [
        row("moneyline", "Moneyline", "Rays", "Rays", 0.48, 30),
        row("spread", "Run line", "Rays +1.5", "Rays", 0.66, 30),
        row("total", "Total", "Under 7.5", "Under", 0.5, 30),
      ],
    },
    {
      title: "Dodgers vs Giants",
      takeaway: "70% sounds great, but it's only 5 past games. We pull thin samples toward break-even.",
      game: odds("Dodgers", "Giants", -200, 170, [-1.5, -110], [1.5, -110], [8.5, -110, -110]),
      rows: [
        row("moneyline", "Moneyline", "Dodgers", "Dodgers", 0.7, 5),
        row("spread", "Run line", "Dodgers -1.5", "Dodgers", 0.55, 6),
      ],
    },
  ],
  soccer: [
    {
      title: "Man City vs Ipswich",
      takeaway: "Teams in City's spot won 76% of past games, but −450 needs 82%. Strong lean, bad price.",
      game: odds("Man City", "Ipswich", -450, 1100, [-1.5, -110], [1.5, -110], [3.5, 110, -130]),
      rows: [
        row("moneyline", "Moneyline", "Man City", "Man City", 0.76, 40),
        row("total", "Total", "Over 3.5", "Over", 0.45, 30),
      ],
    },
    {
      title: "Spurs vs Brentford",
      takeaway: "Teams in Brentford's spot only won 36%, but at +240 Brentford only need 29%. Underdogs can be value.",
      game: odds("Spurs", "Brentford", 110, 240, [-0.5, 110], [0.5, -130], [2.5, -125, 105]),
      rows: [
        row("moneyline", "Moneyline", "Brentford", "Brentford", 0.36, 30),
        row("total", "Total", "Under 2.5", "Under", 0.52, 30),
      ],
    },
    {
      title: "Arsenal vs Brighton",
      takeaway: "A modest favorite at a fair price: the trend rate clears break-even.",
      game: odds("Arsenal", "Brighton", -150, 420, [-1.5, 160], [1.5, -190], [2.5, -120, 100]),
      rows: [
        row("moneyline", "Moneyline", "Arsenal", "Arsenal", 0.66, 40),
        row("total", "Total", "Over 2.5", "Over", 0.6, 30),
      ],
    },
  ],
};

const SOCCER_KEYS = ["soccer", "epl", "laliga", "bundesliga", "ligue1", "seriea", "worldcup"];

/** Map a URL sport key ("nfl", "epl") or Odds API key ("basketball_ncaab") to an example set. */
export const exampleSportFor = (sport?: string): ExampleSport => {
  const s = (sport || "").toLowerCase();
  if (s.includes("ncaaf")) return "ncaaf";
  if (s.includes("ncaab")) return "ncaab";
  if (s.includes("nfl")) return "nfl";
  if (s.includes("nba")) return "nba";
  if (s.includes("nhl")) return "nhl";
  if (s.includes("mlb")) return "mlb";
  if (SOCCER_KEYS.some((k) => s.includes(k))) return "soccer";
  return "nba";
};

const ExampleCard: React.FC<{ example: ValueReadExample; index: number; total: number }> = ({ example, index, total }) => (
  <Box sx={{
    flex: "0 0 88%", scrollSnapAlign: "start",
    p: 1.5, background: "#f8fafc", borderRadius: "12px", border: "1px solid #e2e8f0",
    display: "flex", flexDirection: "column", gap: 1,
  }}>
    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
      <Typography sx={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8" }}>
        Example · {example.title}
      </Typography>
      <Typography sx={{ fontSize: "0.65rem", color: "#94a3b8" }}>{index + 1}/{total}</Typography>
    </Box>
    {example.rows.map(({ market, label, pick, entry }) => {
      const read = getValueRead(market, entry, example.game)!;
      return (
        <Box key={market}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <Typography sx={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>{label}</Typography>
            <Typography sx={{ fontSize: "0.85rem", fontWeight: 700, color: "#334155" }}>
              {pick} <Box component="span" sx={{ color: "#16a34a" }}>{Math.round(entry.probability * 100)}%</Box>
              <Box component="span" sx={{ color: "#94a3b8", fontWeight: 500, fontSize: "0.72rem" }}> ({entry.sample_size} games)</Box>
            </Typography>
          </Box>
          <ValueReadRow probability={entry.probability} read={read} />
        </Box>
      );
    })}
    <Typography sx={{ fontSize: "0.75rem", color: tokens.text.secondary, mt: "auto", pt: 0.5, borderTop: "1px solid #e2e8f0" }}>
      {example.takeaway}
    </Typography>
  </Box>
);

/** Explains Value Reads with a fully unlocked example, then hands off to UpgradeDialog. */
export const ValueReadPreviewDialog: React.FC<{ open: boolean; onClose: () => void; sport?: string }> = ({ open, onClose, sport }) => {
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const examples = VALUE_READ_EXAMPLES[exampleSportFor(sport)];
  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ pb: 0.5 }}>Value Reads <Box component="span" sx={{ fontSize: "0.75rem", color: tokens.text.tertiary }}>· Pro</Box></DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: "0.85rem", color: tokens.text.secondary, mb: 1.5 }}>
            A strong trend isn't always a good bet. Value Reads compare our trend rate to the
            win rate today's price needs to break even. A 70% lean at −500 needs 83% to pay off,
            so it's a pass. A 60% lean at −120 only needs 54.5%.
          </Typography>
          {/* Swipeable carousel; the next card peeks in so it's obvious there's more. */}
          <Box
            role="region"
            aria-label="Value Read examples"
            sx={{
              display: "flex", gap: 1.5, overflowX: "auto", scrollSnapType: "x mandatory",
              pb: 1, mx: -0.5, px: 0.5,
              "&::-webkit-scrollbar": { height: 6 },
              "&::-webkit-scrollbar-thumb": { bgcolor: "#cbd5e1", borderRadius: 3 },
            }}
          >
            {examples.map((ex, i) => (
              <ExampleCard key={ex.title} example={ex} index={i} total={examples.length} />
            ))}
          </Box>
          <Typography sx={{ fontSize: "0.68rem", color: tokens.text.tertiary, mt: 0.5 }}>
            Swipe for more examples →
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={onClose}>Maybe later</Button>
          <Button variant="contained" onClick={() => { onClose(); setUpgradeOpen(true); }}>Unlock with Pro</Button>
        </DialogActions>
      </Dialog>
      <UpgradeDialog open={upgradeOpen} onClose={() => setUpgradeOpen(false)} />
    </>
  );
};
