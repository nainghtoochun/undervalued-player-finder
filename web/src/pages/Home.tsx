import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import PlayerTable from "../components/PlayerTable";
import { Section, Select, StatTile } from "../components/ui";
import { pct, useData, type Quintile } from "../data";

const QUINTILE_LABEL = ["Most overpriced", "2", "3", "4", "Most underpriced"];

function QuintileTooltip({ active, payload }: { active?: boolean; payload?: { payload: Quintile & { label: string } }[] }) {
  if (!active || !payload?.length) return null;
  const q = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-ink">{q.label} fifth · {q.players} players</div>
      <div className="mt-1 text-ink-2">Extra value change: <span className="num text-ink">{pct(q.extra_growth_pct, 1)}</span></div>
      <div className="text-ink-2">Median raw change: <span className="num text-ink">{pct(q.median_growth)}</span></div>
      <div className="text-ink-2">Share whose value rose: <span className="num text-ink">{pct(q.share_rose, 0, false)}</span></div>
    </div>
  );
}

export default function Home() {
  const { players, summary } = useData();
  const [maxAge, setMaxAge] = useState<"25" | "30" | "99">("30");
  const [position, setPosition] = useState<"ALL" | "DEF" | "MID" | "FWD">("ALL");
  const [relegated, setRelegated] = useState<"no" | "yes">("no");

  const bargains = useMemo(
    () =>
      (players ?? [])
        .filter((p) => p.gap_rank != null)
        .filter((p) => (p.age ?? 99) <= Number(maxAge))
        .filter((p) => position === "ALL" || p.position_group === position)
        .filter((p) => relegated === "yes" || !p.relegated)
        .slice(0, 10),
    [players, maxAge, position, relegated],
  );

  if (!summary) return null;
  const b = summary.backtest;
  const extra = Math.exp(b.extra_growth_log_top_minus_rest) - 1;
  const [lo, hi] = b.extra_growth_ci95.map((x) => Math.exp(x) - 1);
  const quintiles = summary.backtest_by_quintile.map((q, i) => ({ ...q, label: QUINTILE_LABEL[i] }));

  return (
    <div>
      <section className="pt-4">
        <p className="text-sm font-medium text-accent">
          {summary.season} season · {summary.players.toLocaleString()} players · Premier League, La Liga, Serie A, Ligue 1
        </p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Which players was the market getting wrong?
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-ink-2">
          A model scores every player on what he actually did with the ball, then compares that with his price. In
          summer 2016 it flagged 50 players as cheap.{" "}
          <span className="font-medium text-ink">
            Two years later their value had risen {pct(extra, 0, false)} more than similar players.
          </span>
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/explore" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90">
            Explore all players
          </Link>
          <Link to="/method" className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-panel">
            How it works
          </Link>
        </div>
      </section>

      <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Extra value gained, top 50" value={pct(extra)} tone="good"
          note={`95% range ${pct(lo)} to ${pct(hi)}, after age, position, league and price`} />
        <StatTile label="Median value change, top 50" value={pct(b.top_median_growth)} tone="good"
          note={`Everyone else ${pct(b.rest_median_growth)}`} />
        <StatTile label="Share whose value rose, top 50" value={pct(b.top_share_rose, 0, false)}
          note={`Everyone else ${pct(b.rest_share_rose, 0, false)}`} />
        <StatTile label="Players with a fair value" value={summary.scored_players.toLocaleString()}
          note="Outfield players, 900+ minutes, with a 2016 price" />
      </div>

      <Section
        title="The cheaper the model said a player was, the more his value rose"
        subtitle="All scored players in five equal groups by value gap in summer 2016. Bars show value change to 2018 beyond what age, position, league and price predict."
      >
        <div className="rounded-xl border border-line bg-panel p-4">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={quintiles} margin={{ top: 24, right: 8, bottom: 8, left: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--line)" />
                <XAxis dataKey="label" tick={{ fill: "var(--ink-2)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(v: number) => pct(v)} tick={{ fill: "var(--ink-2)", fontSize: 12 }}
                  axisLine={false} tickLine={false} width={48} />
                <ReferenceLine y={0} stroke="var(--ink-3)" />
                <Tooltip content={<QuintileTooltip />} cursor={{ fill: "var(--accent-soft)" }} />
                <Bar dataKey="extra_growth_pct" radius={[4, 4, 4, 4]} maxBarSize={72}>
                  {quintiles.map((q) => (
                    <Cell key={q.label} fill={q.extra_growth_pct >= 0 ? "var(--accent)" : "var(--ink-3)"} />
                  ))}
                  <LabelList dataKey="extra_growth_pct" position="top" formatter={(v) => pct(Number(v))}
                    style={{ fill: "var(--ink)", fontSize: 12 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="sr-only">
            <caption>Extra value change by value gap group</caption>
            <tbody>
              {quintiles.map((q) => (
                <tr key={q.label}><th>{q.label}</th><td>{pct(q.extra_growth_pct, 1)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Top bargains of summer 2016"
        subtitle="Biggest gap between fair value and market price. Click a player for the full profile."
        right={
          <div className="flex flex-wrap gap-3">
            <Select label="Max age" value={maxAge} onChange={setMaxAge}
              options={[{ value: "25", label: "25" }, { value: "30", label: "30" }, { value: "99", label: "Any" }]} />
            <Select label="Position" value={position} onChange={setPosition}
              options={[{ value: "ALL", label: "All" }, { value: "DEF", label: "Defenders" },
                { value: "MID", label: "Midfielders" }, { value: "FWD", label: "Forwards" }]} />
            <Select label="Relegated clubs" value={relegated} onChange={setRelegated}
              options={[{ value: "no", label: "Hide" }, { value: "yes", label: "Show" }]} />
          </div>
        }
      >
        <PlayerTable rows={bargains} />
        <p className="mt-3 text-xs text-ink-3">
          Prices are Transfermarkt estimates. Fair value comes from a model that never saw the player's own price.
        </p>
      </Section>
    </div>
  );
}
