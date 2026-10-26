import React, { useState } from "react";
import { Box, Typography, CircularProgress } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import { GameWithTrends, TrendResult, MarketOverviewEntry, TrendType, CollisionTeamTrend } from "../utils/trendAnalysis";
import { getConfidenceScore, getConfidence } from "./TrendInsightCard";
import TeamLogo from './TeamLogo';
import { gameDetailsTokens as tokens } from '../utils/gameDetailsTokens';
import { getTeamColors } from '../utils/teamColors';
import { convertTeamNameBySport } from '../utils/teamNameConverter';
import { getSportType } from '../types/gameTypes';

interface TrendAnalysisSectionProps {
  gameTrends: GameWithTrends | null;
  loading: boolean;
  game: any;
  minTrendLength: number;
  dataSinceYear?: number | null;
  sportKey?: string;
}

const POSITIVE_TYPES = new Set(["win_streak", "cover_streak", "over_streak"]);

// Build the full rich text for the detail page (reconstruct from description parts)
const parseFullDescription = (description: string) => {
  const parts = description.split(" — ");
  const title = parts[0];
  if (parts.length < 2) return { title, fullContext: "" };

  // Capitalize first letter of each part and join cleanly
  const contextParts = parts.slice(1).map((p, i) => {
    const clean = p.replace(/ \([^)]+? today\)/g, (match) => {
      // Keep "(Team today)" but strip the " today" to make it cleaner
      return match.replace(" today", "");
    }).trim();
    return i === 0 ? clean.charAt(0).toUpperCase() + clean.slice(1) : clean.charAt(0).toUpperCase() + clean.slice(1);
  });

  return { title, fullContext: contextParts.join(" — ") };
};

const TrendDetailCard: React.FC<{ trend: TrendResult; dataSinceYear?: number | null }> = ({ trend, dataSinceYear }) => {
  const positive = POSITIVE_TYPES.has(trend.type);
  const trendColor = positive ? tokens.hit.text : tokens.miss.text;
  const borderColor = tokens.cardBorder;
  const bgColor = tokens.cardBg;
  const confidence = getConfidence(trend);
  const { title, fullContext } = parseFullDescription(trend.description);

  const { continuation_rate, sample_size } = trend;
  const pct = continuation_rate != null ? Math.round(continuation_rate * 100) : null;
  const continued = continuation_rate != null && sample_size != null
    ? Math.round(continuation_rate * sample_size)
    : null;

  return (
    <Box sx={{
      px: 2, py: 2,
      background: bgColor,
      borderRadius: `${tokens.cardRadius}px`,
      border: `1px solid ${borderColor}`,
    }}>
      {/* Header: icon + title + badges */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
        <Box sx={{
          width: 44, height: 44, borderRadius: "50%", flexShrink: 0, mt: 0.25,
          background: positive ? tokens.hit.bg : tokens.miss.bg,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {positive
            ? <TrendingUpIcon sx={{ color: tokens.hit.text, fontSize: 24 }} />
            : <TrendingDownIcon sx={{ color: tokens.miss.text, fontSize: 24 }} />}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          {confidence && (
            <Box sx={{
              display: "inline-block", mb: 0.5,
              px: 0.9, py: 0.3, borderRadius: "999px",
              border: `1.5px solid ${confidence.color}`, color: confidence.color,
              fontSize: "0.58rem", fontWeight: 800, letterSpacing: "0.07em", textTransform: "uppercase",
            }}>
              {confidence.label}
            </Box>
          )}
          <Typography sx={{ fontWeight: 800, fontSize: "0.95rem", color: trendColor, lineHeight: 1.3 }}>
            {title}
          </Typography>
        </Box>
      </Box>

      {/* Full prose context */}
      {fullContext && (
        <Typography sx={{ fontSize: "0.875rem", color: "#475569", lineHeight: 1.65, mt: 1.5, mb: pct != null ? 1.5 : 0 }}>
          {fullContext}
        </Typography>
      )}

      {/* Progress bar + sample count */}
      {pct != null && sample_size != null && sample_size >= 3 && (
        <Box>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", mb: 0.75 }}>
            <Typography sx={{ fontSize: "0.78rem", color: "#64748b" }}>
              {continued} out of {sample_size} historical instances{dataSinceYear ? ` since ${dataSinceYear}` : ""}
            </Typography>
            <Typography sx={{ fontSize: "1rem", fontWeight: 800, color: trendColor }}>
              {pct}%
            </Typography>
          </Box>
          <Box sx={{ height: 7, borderRadius: "999px", bgcolor: positive ? tokens.hit.bg : tokens.miss.bg, overflow: "hidden" }}>
            <Box sx={{
              height: "100%",
              width: `${pct}%`,
              bgcolor: trendColor,
              borderRadius: "999px",
              transition: "width 0.6s ease",
            }} />
          </Box>
        </Box>
      )}
    </Box>
  );
};

const MARKET_CARD_TITLES: Record<'moneyline' | 'spread' | 'total', string> = {
  moneyline: 'Moneyline Trends',
  spread: 'Spread Trends',
  total: 'Total Trends',
};

const formatSigned = (n: number): string => `${n > 0 ? '+' : ''}${n}`;

const spreadPointForTeam = (game: any, teamName: string): number | null => {
  if (game?.home?.team === teamName) return game?.home?.odds?.spread_point ?? null;
  if (game?.away?.team === teamName) return game?.away?.odds?.spread_point ?? null;
  return null;
};

const marketCardLabel = (marketKey: 'moneyline' | 'spread' | 'total', entry: MarketOverviewEntry, game: any): string => {
  if (marketKey === 'moneyline') return `${entry.lean} win`;
  if (marketKey === 'total') return entry.lean;
  const point = spreadPointForTeam(game, entry.lean);
  return point != null ? `${entry.lean} cover ${formatSigned(point)}` : `${entry.lean} cover the spread`;
};

const MarketTrendCard: React.FC<{
  marketKey: 'moneyline' | 'spread' | 'total';
  entry: MarketOverviewEntry;
  game: any;
  sportKey: string;
}> = ({ marketKey, entry, game, sportKey }) => {
  const pct = Math.round(entry.probability * 100);
  const wins = Math.round(entry.probability * entry.sample_size);
  const losses = entry.sample_size - wins;
  const dbSport = getSportType(sportKey);
  const barColor =
    marketKey === 'total'
      ? tokens.neutralBar
      : getTeamColors(dbSport, convertTeamNameBySport(sportKey, entry.lean)).primary;
  const { fullContext } = parseFullDescription(entry.supporting_description || '');

  return (
    <Box
      sx={{
        bgcolor: tokens.cardBg,
        border: `1px solid ${tokens.cardBorder}`,
        borderRadius: `${tokens.cardRadius}px`,
        p: '18px 18px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        '&:hover': { borderColor: '#c9ccc5', boxShadow: tokens.shadowHover },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color: tokens.text.secondary }}>
          {MARKET_CARD_TITLES[marketKey]}
        </Typography>
        <Typography sx={{ fontSize: '1.125rem', color: tokens.link }}>›</Typography>
      </Box>
      <Typography sx={{ fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
        {pct}%
      </Typography>
      <Typography sx={{ fontSize: '0.9375rem', fontWeight: 600 }}>{marketCardLabel(marketKey, entry, game)}</Typography>
      <Typography sx={{ fontSize: '0.8125rem', color: tokens.text.secondary }}>
        {wins}-{losses} ({entry.sample_size} games)
      </Typography>
      <Box sx={{ height: 6, borderRadius: '3px', bgcolor: tokens.trackBg2, overflow: 'hidden', mt: 0.5 }}>
        <Box sx={{ height: '100%', width: `${pct}%`, bgcolor: barColor, borderRadius: '3px' }} />
      </Box>
      {fullContext && (
        <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary, lineHeight: 1.45, mt: 0.75 }}>
          {fullContext}
        </Typography>
      )}
    </Box>
  );
};

const COLLISION_PHRASE: Record<TrendType, (n: number) => string> = {
  win_streak: (n) => `Won ${n} straight`,
  loss_streak: (n) => `Lost ${n} straight`,
  cover_streak: (n) => `Covered ${n} straight spreads`,
  no_cover_streak: (n) => `Failed to cover ${n} straight spreads`,
  over_streak: (n) => `Hit the OVER ${n} straight`,
  under_streak: (n) => `Hit the UNDER ${n} straight`,
};

const describeCollisionSide = (trend: CollisionTeamTrend | undefined, side: 'home' | 'away'): string => {
  if (!trend) return '';
  const venueSuffix = trend.venue === 'venue_specific' ? (side === 'home' ? ' at home' : ' on the road') : '';
  return `${COLLISION_PHRASE[trend.type](trend.count)}${venueSuffix}`;
};

type CollisionDimension = 'straight_up' | 'ats' | 'total';

const collisionDimension = (type: TrendType): CollisionDimension => {
  if (type === 'win_streak' || type === 'loss_streak') return 'straight_up';
  if (type === 'cover_streak' || type === 'no_cover_streak') return 'ats';
  return 'total'; // over_streak | under_streak
};

const CollisionCard: React.FC<{ trend: TrendResult; sportKey: string }> = ({ trend, sportKey }) => {
  const { home_trend, away_trend, continuation_rate, sample_size } = trend;
  if (!home_trend || !away_trend || continuation_rate == null || sample_size == null) return null;

  const pct = Math.round(continuation_rate * 100);
  const otherPct = 100 - pct;
  const dbSport = getSportType(sportKey);
  const homeColor = getTeamColors(dbSport, convertTeamNameBySport(sportKey, home_trend.team));
  const awayColor = getTeamColors(dbSport, convertTeamNameBySport(sportKey, away_trend.team));
  const dimension = collisionDimension(home_trend.type);
  const verb = dimension === 'ats' ? 'cover' : 'win';

  return (
    <Box
      sx={{
        bgcolor: tokens.cardBg,
        border: `1px solid ${tokens.cardBorder}`,
        borderRadius: `${tokens.cardRadius}px`,
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '1.1fr 1fr auto' },
        overflow: 'hidden',
        mb: 3,
      }}
    >
      <Box sx={{ p: '18px 22px' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Box sx={{ width: 32, height: 32, borderRadius: '50%', bgcolor: tokens.collisionIcon, display: 'grid', placeItems: 'center' }}>
            <Box sx={{ width: 10, height: 10, bgcolor: '#fff', transform: 'rotate(45deg)' }} />
          </Box>
          <Box>
            <Typography sx={{ fontSize: '1rem', fontWeight: 700 }}>Trend vs. Trend Collision</Typography>
            <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>When both teams' trends meet</Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: 1, mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
            <TeamLogo sportKey={sportKey} teamName={home_trend.team} size={40} />
            <Box>
              <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{home_trend.team}</Typography>
              <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>
                {describeCollisionSide(home_trend, 'home')}
              </Typography>
            </Box>
          </Box>
          <Typography
            sx={{
              fontSize: '0.6875rem',
              fontWeight: 700,
              color: tokens.text.muted,
              bgcolor: tokens.chipTrackBg,
              borderRadius: '999px',
              px: 1,
              py: 0.5,
              textAlign: 'center',
            }}
          >
            VS
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, justifyContent: 'flex-end', textAlign: 'right' }}>
            <Box>
              <Typography sx={{ fontSize: '0.875rem', fontWeight: 700 }}>{away_trend.team}</Typography>
              <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary }}>
                {describeCollisionSide(away_trend, 'away')}
              </Typography>
            </Box>
            <TeamLogo sportKey={sportKey} teamName={away_trend.team} size={40} />
          </Box>
        </Box>
      </Box>

      <Box data-testid="collision-split-panel" sx={{ bgcolor: tokens.subtlePanelBg, borderLeft: { md: `1px solid ${tokens.borders.light}` }, p: '18px 22px' }}>
        <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary, mb: 1 }}>
          Historically when this collision has happened
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'nowrap', gap: 1 }}>
          {dimension === 'total' ? (
            <>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75 }}>
                <Typography sx={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
                  {pct}%
                </Typography>
                <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600 }}>OVER</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75 }}>
                <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600 }}>UNDER</Typography>
                <Typography sx={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
                  {otherPct}%
                </Typography>
              </Box>
            </>
          ) : (
            <>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75 }}>
                <Typography sx={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
                  {pct}%
                </Typography>
                <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600 }}>{home_trend.team} {verb}</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75 }}>
                <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600 }}>{away_trend.team} {verb}</Typography>
                <Typography sx={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>
                  {otherPct}%
                </Typography>
              </Box>
            </>
          )}
        </Box>
        <Box sx={{ display: 'flex', height: 8, borderRadius: '4px', overflow: 'hidden', gap: '2px', mt: 1 }}>
          {dimension === 'total' ? (
            <>
              <Box data-testid="collision-bar-left" sx={{ width: `${pct}%`, bgcolor: tokens.neutralBar }} />
              <Box data-testid="collision-bar-right" sx={{ flex: 1, bgcolor: tokens.trackBg2 }} />
            </>
          ) : (
            <>
              <Box data-testid="collision-bar-left" sx={{ width: `${pct}%`, bgcolor: homeColor.primary }} />
              <Box data-testid="collision-bar-right" sx={{ flex: 1, bgcolor: awayColor.primary }} />
            </>
          )}
        </Box>
        <Typography sx={{ fontSize: '0.75rem', color: tokens.text.secondary, mt: 1 }}>{sample_size} historical meetings</Typography>
      </Box>

      <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center', px: 2, color: tokens.link, fontSize: '1.375rem' }}>›</Box>
    </Box>
  );
};

const TrendAnalysisSection: React.FC<TrendAnalysisSectionProps> = ({
  gameTrends,
  loading,
  game,
  minTrendLength,
  dataSinceYear,
  sportKey = 'baseball_mlb',
}) => {
  const [showAllTrends, setShowAllTrends] = useState(false);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 1.5, pt: 4, pb: 2, maxWidth: 900, mx: "auto" }}>
        <CircularProgress size={20} />
        <Typography sx={{ color: "#64748b", fontSize: "0.875rem" }}>Loading trend analysis…</Typography>
      </Box>
    );
  }

  if (!gameTrends) return null;

  // Collect all trends, dedup venue-specific vs general (prefer venue-specific)
  const homeSpecificTypes = new Set((gameTrends.homeTeamHomeTrends || []).map(t => t.type));
  const awaySpecificTypes = new Set((gameTrends.awayTeamAwayTrends || []).map(t => t.type));
  // The top collision trend gets its own dedicated CollisionCard above this list
  // (see topCollisionTrend below), so it's excluded here to avoid showing the
  // same trend twice — any remaining collision trends still appear generically.
  const topCollisionTrend = (gameTrends.collisionTrends || [])[0] ?? null;
  const remainingCollisionTrends = (gameTrends.collisionTrends || []).slice(1);
  const allTrends: TrendResult[] = [
    ...(gameTrends.headToHeadTrends || []),
    ...(gameTrends.homeAtHomeH2HTrends || []),
    ...remainingCollisionTrends,
    ...(gameTrends.homeTeamHomeTrends || []),
    ...(gameTrends.awayTeamAwayTrends || []),
    ...(gameTrends.homeTeamTrends || []).filter(t => !homeSpecificTypes.has(t.type)),
    ...(gameTrends.awayTeamTrends || []).filter(t => !awaySpecificTypes.has(t.type)),
  ]
    .filter(t => t.count >= minTrendLength)
    .sort((a, b) => getConfidenceScore(b) - getConfidenceScore(a) || b.count - a.count);

  const marketRows = (['moneyline', 'spread', 'total'] as const)
    .map((key) => ({ key, entry: gameTrends.marketOverview?.[key] }))
    .filter((r): r is { key: 'moneyline' | 'spread' | 'total'; entry: MarketOverviewEntry } => !!r.entry);

  // Collision trends are a separate concept from both market rows and the general
  // trends list, so the collision card's own visibility must not depend on this guard.
  if (allTrends.length === 0 && marketRows.length === 0 && !topCollisionTrend) return null;

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", px: { xs: 2, sm: 3 }, pt: 4, mb: 2 }}>
      {marketRows.length > 0 && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', mb: 3 }}>
          {marketRows.map(({ key, entry }) => (
            <MarketTrendCard key={key} marketKey={key} entry={entry} game={game} sportKey={sportKey} />
          ))}
        </Box>
      )}
      {topCollisionTrend && <CollisionCard trend={topCollisionTrend} sportKey={sportKey} />}
      {allTrends.length > 0 && (() => {
        const hasMore = allTrends.length > 2;
        const visibleTrends = showAllTrends ? allTrends : allTrends.slice(0, 2);
        return (
          <>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 2, color: tokens.text.primary }}>
              More trends
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
              {visibleTrends.map((trend, idx) => {
                const isFadedCard = !showAllTrends && hasMore && idx === visibleTrends.length - 1;
                return (
                  <Box
                    key={idx}
                    sx={{
                      position: "relative",
                      ...(isFadedCard ? { maxHeight: 110, overflow: "hidden", borderRadius: `${tokens.cardRadius}px` } : {}),
                    }}
                  >
                    <TrendDetailCard trend={trend} dataSinceYear={dataSinceYear} />
                    {isFadedCard && (
                      <Box
                        data-testid="trend-fade-overlay"
                        sx={{
                          position: "absolute",
                          left: 0,
                          right: 0,
                          bottom: 0,
                          height: "100%",
                          background: `linear-gradient(to bottom, rgba(255,255,255,0) 0%, ${tokens.cardBg} 55%)`,
                          pointerEvents: "none",
                        }}
                      />
                    )}
                  </Box>
                );
              })}
            </Box>
            {hasMore && (
              <Box sx={{ display: "flex", justifyContent: "center", mt: 0.75 }}>
                <Box
                  component="button"
                  onClick={() => setShowAllTrends((v) => !v)}
                  sx={{
                    cursor: "pointer",
                    fontSize: "1rem",
                    fontWeight: 700,
                    fontFamily: "inherit",
                    color: tokens.link,
                    bgcolor: tokens.cardBg,
                    border: `1.5px solid ${tokens.cardBorder}`,
                    borderRadius: "10px",
                    px: 3,
                    py: 1.25,
                    display: "flex",
                    alignItems: "center",
                    gap: 0.75,
                    "&:hover": { borderColor: tokens.link },
                  }}
                >
                  {showAllTrends ? "View Less ▾" : "View More ▾"}
                </Box>
              </Box>
            )}
          </>
        );
      })()}
    </Box>
  );
};

export default TrendAnalysisSection;
