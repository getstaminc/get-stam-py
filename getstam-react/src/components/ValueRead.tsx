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

// Static demo for the preview dialog — matches the design mock.
const SAMPLE_GAME = {
  home: { team: "Knicks", odds: { h2h: -120, spread_point: -4.5, spread_price: -110 } },
  away: { team: "Hornets", odds: { h2h: 100, spread_point: 4.5, spread_price: -110 } },
  totals: { over_point: 221.5, over_price: -110, under_point: 221.5, under_price: -110 },
};
const SAMPLE_ROWS: { market: "moneyline" | "spread" | "total"; label: string; pick: string; entry: MarketOverviewEntry }[] = [
  { market: "moneyline", label: "Moneyline", pick: "Knicks", entry: { lean: "Knicks", probability: 0.6, trend_count: 3, sample_size: 25, contributing_trends: [] } },
  { market: "spread", label: "Spread", pick: "Knicks -4.5", entry: { lean: "Knicks", probability: 0.58, trend_count: 2, sample_size: 25, contributing_trends: [] } },
  { market: "total", label: "Total", pick: "Over 221.5", entry: { lean: "Over", probability: 0.54, trend_count: 2, sample_size: 25, contributing_trends: [] } },
];

/** Explains Value Reads with a fully unlocked example, then hands off to UpgradeDialog. */
export const ValueReadPreviewDialog: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const [upgradeOpen, setUpgradeOpen] = useState(false);
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
          <Box sx={{ p: 1.5, background: "#f8fafc", borderRadius: "12px", border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: 1 }}>
            <Typography sx={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8" }}>
              Example · Knicks vs Hornets
            </Typography>
            {SAMPLE_ROWS.map(({ market, label, pick, entry }) => {
              const read = getValueRead(market, entry, SAMPLE_GAME)!;
              return (
                <Box key={market}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <Typography sx={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>{label}</Typography>
                    <Typography sx={{ fontSize: "0.85rem", fontWeight: 700, color: "#334155" }}>
                      {pick} <Box component="span" sx={{ color: "#16a34a" }}>{Math.round(entry.probability * 100)}%</Box>
                      <Box component="span" sx={{ color: "#94a3b8", fontWeight: 500, fontSize: "0.72rem" }}> (n={entry.sample_size})</Box>
                    </Typography>
                  </Box>
                  <ValueReadRow probability={entry.probability} read={read} />
                </Box>
              );
            })}
            <Typography sx={{ fontSize: "0.68rem", color: tokens.text.tertiary }}>
              Tick = break-even rate from today's price. Small samples are pulled toward break-even before we call it value.
            </Typography>
          </Box>
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
