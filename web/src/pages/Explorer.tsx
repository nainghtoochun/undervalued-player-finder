import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import PlayerTable from "../components/PlayerTable";
import { Section, Select } from "../components/ui";
import { euro, LEAGUES, pct, useData, type Player } from "../data";

type SortKey = "value_gap_pct" | "xt_p90" | "npxg_p90" | "xa_p90" | "value_2016_eur";
const SORTS: { value: SortKey; label: string }[] = [
  { value: "value_gap_pct", label: "Biggest value gap" },
  { value: "xt_p90", label: "xT per 90" },
  { value: "npxg_p90", label: "xG per 90" },
  { value: "xa_p90", label: "xA per 90" },
  { value: "value_2016_eur", label: "Price 2016" },
];
const MIN_V = 50_000;
const MAX_V = 200_000_000;
const TICKS = [1e5, 1e6, 1e7, 1e8];

function PointTooltip({ active, payload }: { active?: boolean; payload?: { payload: Player }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-ink">{p.name}</div>
      <div className="text-ink-3">{p.team} · {p.position_group} · age {p.age?.toFixed(0)}</div>
      <div className="mt-1 text-ink-2">Price 2016 <span className="num text-ink">{euro(p.value_2016_eur)}</span></div>
      <div className="text-ink-2">Fair value <span className="num text-ink">{euro(p.predicted_value_eur)}</span></div>
      <div className="text-ink-2">Gap <span className="num text-accent">{pct(p.value_gap_pct)}</span></div>
      <div className="mt-1 text-ink-3">Click to open</div>
    </div>
  );
}

export default function Explorer() {
  const { players } = useData();
  const navigate = useNavigate();
  const [league, setLeague] = useState<string>("ALL");
  const [position, setPosition] = useState<string>("ALL");
  const [maxAge, setMaxAge] = useState<string>("99");
  const [maxPrice, setMaxPrice] = useState<string>("0");
  const [sort, setSort] = useState<SortKey>("value_gap_pct");
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(25);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (players ?? [])
      .filter((p) => p.position_group !== "GK")
      .filter((p) => league === "ALL" || p.league === league)
      .filter((p) => position === "ALL" || p.position_group === position)
      .filter((p) => maxAge === "99" || (p.age ?? 99) <= Number(maxAge))
      .filter((p) => maxPrice === "0" || (p.value_2016_eur ?? Infinity) <= Number(maxPrice))
      .filter((p) => !q || `${p.name} ${p.full_name} ${p.team}`.toLowerCase().includes(q))
      .sort((a, b) => ((b[sort] ?? -Infinity) as number) - ((a[sort] ?? -Infinity) as number));
  }, [players, league, position, maxAge, maxPrice, sort, query]);

  const scored = filtered.filter((p) => p.value_2016_eur && p.predicted_value_eur);
  const cheap = scored.filter((p) => (p.value_gap_pct ?? 0) >= 1);
  const rest = scored.filter((p) => (p.value_gap_pct ?? 0) < 1);
  const open = (p: Player) => navigate(`/player/${p.player_id}`);

  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight">Explore every player</h1>
      <p className="mt-2 max-w-2xl text-ink-2">
        Each dot is a player. Dots above the line had a fair value higher than their market price in summer 2016.
        Blue dots were priced at less than half their fair value.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-3 rounded-xl border border-line bg-panel p-4">
        <label className="flex min-w-[180px] flex-1 flex-col gap-1 text-xs font-medium text-ink-2">
          Search
          <input value={query} onChange={(e) => { setQuery(e.target.value); setShown(25); }}
            placeholder="Player or club" className="rounded-md border border-line bg-panel px-2 py-1.5 text-sm text-ink" />
        </label>
        <Select label="League" value={league} onChange={(v) => { setLeague(v); setShown(25); }}
          options={[{ value: "ALL", label: "All leagues" }, ...LEAGUES.map((l) => ({ value: l, label: l }))]} />
        <Select label="Position" value={position} onChange={(v) => { setPosition(v); setShown(25); }}
          options={[{ value: "ALL", label: "All" }, { value: "DEF", label: "Defenders" },
            { value: "MID", label: "Midfielders" }, { value: "FWD", label: "Forwards" }]} />
        <Select label="Max age" value={maxAge} onChange={(v) => { setMaxAge(v); setShown(25); }}
          options={[{ value: "99", label: "Any" }, { value: "21", label: "21" }, { value: "25", label: "25" }, { value: "30", label: "30" }]} />
        <Select label="Max price 2016" value={maxPrice} onChange={(v) => { setMaxPrice(v); setShown(25); }}
          options={[{ value: "0", label: "Any" }, { value: "1000000", label: "€1m" }, { value: "5000000", label: "€5m" },
            { value: "10000000", label: "€10m" }, { value: "25000000", label: "€25m" }]} />
        <Select label="Sort table by" value={sort} onChange={setSort} options={SORTS} />
      </div>

      <Section title="Market price vs fair value" subtitle={`${scored.length.toLocaleString()} players shown. Both axes use a log scale.`}>
        <div className="rounded-xl border border-line bg-panel p-4">
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 16 }}>
                <CartesianGrid stroke="var(--line)" />
                <XAxis type="number" dataKey="value_2016_eur" name="Price 2016" scale="log" domain={[MIN_V, MAX_V]}
                  ticks={TICKS} tickFormatter={euro} allowDataOverflow tick={{ fill: "var(--ink-2)", fontSize: 12 }}
                  label={{ value: "Market price, summer 2016", position: "bottom", offset: 8, fill: "var(--ink-2)", fontSize: 12 }} />
                <YAxis type="number" dataKey="predicted_value_eur" name="Fair value" scale="log" domain={[MIN_V, MAX_V]}
                  ticks={TICKS} tickFormatter={euro} allowDataOverflow tick={{ fill: "var(--ink-2)", fontSize: 12 }}
                  label={{ value: "Fair value (model)", angle: -90, position: "insideLeft", fill: "var(--ink-2)", fontSize: 12 }} />
                <ReferenceLine segment={[{ x: MIN_V, y: MIN_V }, { x: MAX_V, y: MAX_V }]} stroke="var(--ink-3)" strokeDasharray="4 4"
                  label={{ value: "price = fair value", position: "insideTopLeft", fill: "var(--ink-3)", fontSize: 11 }} />
                <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3" }} />
                <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12, color: "var(--ink-2)" }} />
                <Scatter name="Other players" data={rest} fill="var(--ink-3)" fillOpacity={0.35} onClick={(d) => open(d.payload as Player)} cursor="pointer" />
                <Scatter name="Priced under half their fair value" data={cheap} fill="var(--accent)" stroke="var(--panel)" strokeWidth={1}
                  onClick={(d) => open(d.payload as Player)} cursor="pointer" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Section>

      <Section title="Players" subtitle={`${filtered.length.toLocaleString()} match your filters`}>
        <PlayerTable rows={filtered.slice(0, shown)} />
        {shown < filtered.length && (
          <button onClick={() => setShown((s) => s + 25)}
            className="mt-3 rounded-md border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-panel">
            Show 25 more
          </button>
        )}
      </Section>
    </div>
  );
}
