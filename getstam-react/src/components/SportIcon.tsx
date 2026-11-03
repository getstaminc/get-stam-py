import React from "react";
import SportsFootball from "@mui/icons-material/SportsFootball";
import SportsBasketball from "@mui/icons-material/SportsBasketball";
import SportsBaseball from "@mui/icons-material/SportsBaseball";
import SportsHockey from "@mui/icons-material/SportsHockey";
import SportsSoccer from "@mui/icons-material/SportsSoccer";

/** Monochrome vector icons for sport filters and navigation. */
export default function SportIcon({ sport, className }: { sport: string; className?: string }) {
  const Icon = /NFL|NCAAF/i.test(sport) ? SportsFootball
    : /NBA|NCAAB/i.test(sport) ? SportsBasketball
    : /MLB/i.test(sport) ? SportsBaseball
    : /NHL/i.test(sport) ? SportsHockey : SportsSoccer;
  return <Icon className={className} sx={{ fontSize: 18, color: "#111827" }} aria-hidden="true" />;
}
