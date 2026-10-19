import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Percentiles = Record<
  "npxg_p90" | "xa_p90" | "xt_p90" | "xt_pass_p90" | "xt_carry_p90" | "np_shots_p90",
  number | null
>;

export interface Player {
  player_id: number;
  name: string;
  full_name: string;
  team: string;
  league: string;
  position: string | null;
  position_group: "GK" | "DEF" | "MID" | "FWD" | "UNK";
  age: number | null;
  minutes: number;
  npxg_p90: number;
  xa_p90: number;
  xt_p90: number;
  xt_pass_p90: number;
  xt_carry_p90: number;
  np_goals_p90: number;
  np_shots_p90: number;
  value_2016_eur: number | null;
  predicted_value_eur: number | null;
  value_gap_pct: number | null;
  gap_rank: number | null;
  value_2018_eur: number | null;
  relegated: boolean | null;
  percentiles: Percentiles;
}

export interface Quintile {
  gap_quintile: string;
  players: number;
  median_growth: number;
  share_rose: number;
  extra_growth_pct: number;
}

export interface Summary {
  players: number;
  scored_players: number;
  season: string;
  backtest: {
    players_with_2018_value: number;
    top_n: number;
    top_median_growth: number;
    rest_median_growth: number;
    top_share_rose: number;
    rest_share_rose: number;
    extra_growth_log_top_minus_rest: number;
    extra_growth_ci95: [number, number];
  };
  backtest_by_quintile: Quintile[];
  value_model: Record<string, { r2_log_value: number; median_abs_pct_error: number } | string>;
}

export type History = Record<string, [string, number][]>;

interface DataState {
  players: Player[] | null;
  summary: Summary | null;
  error: string | null;
  byId: Map<number, Player>;
  loadHistory: () => Promise<History>;
}

const DataContext = createContext<DataState | null>(null);
const url = (file: string) => `${import.meta.env.BASE_URL}data/${file}`;

async function getJson<T>(file: string): Promise<T> {
  const res = await fetch(url(file));
  if (!res.ok) throw new Error(`Could not load ${file} (${res.status})`);
  return res.json() as Promise<T>;
}

let historyPromise: Promise<History> | null = null;

export function DataProvider({ children }: { children: ReactNode }) {
  const [players, setPlayers] = useState<Player[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [byId, setById] = useState<Map<number, Player>>(new Map());

  useEffect(() => {
    Promise.all([getJson<Player[]>("players.json"), getJson<Summary>("summary.json")])
      .then(([p, s]) => {
        setPlayers(p);
        setSummary(s);
        setById(new Map(p.map((x) => [x.player_id, x])));
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  // value history is only needed on player pages, so it loads on first use
  const loadHistory = () => (historyPromise ??= getJson<History>("history.json"));

  return (
    <DataContext.Provider value={{ players, summary, error, byId, loadHistory }}>{children}</DataContext.Provider>
  );
}

export function useData(): DataState {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error("useData must be used inside DataProvider");
  return ctx;
}

// ---------- formatting ----------

export function euro(v: number | null | undefined): string {
  if (v == null) return "n/a";
  if (v >= 1e6) return `€${(v / 1e6).toFixed(v >= 1e7 ? 0 : 1)}m`;
  if (v >= 1e3) return `€${Math.round(v / 1e3)}k`;
  return `€${v}`;
}

export function pct(v: number | null | undefined, digits = 0, sign = true): string {
  if (v == null || Number.isNaN(v)) return "n/a";
  const s = (v * 100).toFixed(digits);
  if (Number(s) === 0) return "0%"; // avoid "-0%"
  return `${sign && v > 0 ? "+" : ""}${s}%`;
}

export function change(from: number | null, to: number | null): number | null {
  if (!from || to == null) return null;
  return to / from - 1;
}

export const POSITION_LABEL: Record<string, string> = {
  GK: "Goalkeeper",
  DEF: "Defender",
  MID: "Midfielder",
  FWD: "Forward",
  UNK: "Unknown",
};

export const LEAGUES = ["Premier League", "La Liga", "Serie A", "Ligue 1"] as const;
