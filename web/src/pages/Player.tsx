import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChangeCell } from "../components/PlayerTable";
import { Pill, Section, StatTile } from "../components/ui";
import { change, euro, pct, POSITION_LABEL, useData, type Percentiles } from "../data";

const PERCENTILE_LABELS: [keyof Percentiles, string, string][] = [
  ["xt_p90", "Threat created (xT per 90)", "How much his passes and dribbles moved the ball into dangerous areas"],
  ["xt_pass_p90", "Threat from passing", "xT added by completed open-play passes"],
  ["xt_carry_p90", "Threat from carrying", "xT added by running with the ball"],
  ["npxg_p90", "Chances taken (xG per 90)", "Quality of his own shots, penalties excluded"],
  ["xa_p90", "Chances created (xA per 90)", "Quality of the shots he set up for team-mates"],
  ["np_shots_p90", "Shots per 90", "How often he shot, penalties excluded"],
];
const SEASON_END = Date.parse("2016-08-31");

function PercentileBar({ label, help, value }: { label: string; help: string; value: number | null }) {
  const v = value ?? 0;
  return (
    <div className="py-2" title={help}>
      <div className="flex justify-between text-sm">
        <span className="text-ink">{label}</span>
        <span className="num font-medium text-ink">{value == null ? "n/a" : `${Math.round(v)}`}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-line" role="img" aria-label={`${label}: percentile ${Math.round(v)}`}>
        <div className="h-2 rounded-full bg-accent" style={{ width: `${Math.max(v, 2)}%` }} />
      </div>
    </div>
  );
}

function HistoryTooltip({ active, payload }: { active?: boolean; payload?: { payload: { t: number; v: number } }[] }) {
  if (!active || !payload?.length) return null;
  const { t, v } = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs shadow-sm">
      <div className="text-ink-3">{new Date(t).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" })}</div>
      <div className="num font-medium text-ink">{euro(v)}</div>
    </div>
  );
}

export default function PlayerPage() {
  const { id } = useParams();
  const { byId, loadHistory } = useData();
  const player = byId.get(Number(id));
  const [history, setHistory] = useState<{ t: number; v: number }[] | null>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    setHistory(null);
    loadHistory().then((h) => setHistory((h[String(id)] ?? []).map(([d, v]) => ({ t: Date.parse(d), v }))));
  }, [id, loadHistory]);

  if (!player) return <p className="text-ink-2">Player not found. <Link className="text-accent underline" to="/explore">Back to the explorer</Link></p>;
  const p = player;
  const rise = change(p.value_2016_eur, p.value_2018_eur);

  return (
    <div>
      <Link to="/explore" className="text-sm text-ink-2 hover:text-ink">← All players</Link>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-2">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{p.name}</h1>
        {p.gap_rank && <Pill>Value gap rank #{p.gap_rank} of 1,249</Pill>}
        {p.relegated && <Pill tone="warn">club relegated in 2016</Pill>}
      </div>
      <p className="mt-1 text-ink-2">
        {p.full_name !== p.name && <>{p.full_name} · </>}
        {p.team} · {p.league} · {p.position ?? POSITION_LABEL[p.position_group]}
        {p.age != null && <> · {p.age.toFixed(0)} in summer 2016</>} · {Math.round(p.minutes).toLocaleString()} minutes
      </p>

      {p.value_2016_eur ? (
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Market price, summer 2016" value={euro(p.value_2016_eur)} />
          <StatTile label="Fair value from his stats" value={euro(p.predicted_value_eur)}
            note={(p.value_gap_pct ?? 0) >= 0 ? "Model says he was cheap" : "Model says he was expensive"} />
          <StatTile label="Value gap" value={pct(p.value_gap_pct)} tone={(p.value_gap_pct ?? 0) >= 0 ? "good" : "bad"}
            note="Fair value vs price" />
          <StatTile label="Market price, summer 2018" value={euro(p.value_2018_eur)}
            tone={rise == null ? undefined : rise >= 0 ? "good" : "bad"}
            note={rise == null ? "No 2018 value (retired or left the data)" : `${pct(rise)} since 2016`} />
        </div>
      ) : (
        <p className="mt-6 rounded-lg border border-line bg-panel p-4 text-sm text-ink-2">
          No fair value for this player. Goalkeepers and players without a 2016 market value are not scored.
        </p>
      )}

      <div className="mt-2 grid gap-6 lg:grid-cols-2">
        <Section title="Market value over time" subtitle="Transfermarkt estimates. Dashed line shows the model's fair value in 2016.">
          <div className="h-72 rounded-xl border border-line bg-panel p-4">
            {history == null ? (
              <p className="py-20 text-center text-sm text-ink-3">Loading…</p>
            ) : history.length === 0 ? (
              <p className="py-20 text-center text-sm text-ink-3">No value history for this player.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 16, right: 16, bottom: 8, left: 8 }}>
                  <CartesianGrid vertical={false} stroke="var(--line)" />
                  <XAxis type="number" dataKey="t" domain={[Date.parse("2014-01-01"), Date.parse("2019-12-31")]}
                    ticks={[2014, 2015, 2016, 2017, 2018, 2019].map((y) => Date.parse(`${y}-01-01`))}
                    tickFormatter={(t: number) => String(new Date(t).getUTCFullYear())}
                    tick={{ fill: "var(--ink-2)", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={euro} tick={{ fill: "var(--ink-2)", fontSize: 12 }} axisLine={false} tickLine={false} width={56} />
                  <ReferenceLine x={SEASON_END} stroke="var(--ink-3)"
                    label={{ value: "2016 scouting date", position: "insideTopLeft", fill: "var(--ink-3)", fontSize: 11 }} />
                  {p.predicted_value_eur && (
                    <ReferenceLine y={p.predicted_value_eur} stroke="var(--series-2)" strokeDasharray="5 4"
                      label={{ value: `fair value ${euro(p.predicted_value_eur)}`, position: "insideBottomRight", fill: "var(--series-2)", fontSize: 11 }} />
                  )}
                  <Tooltip content={<HistoryTooltip />} />
                  <Line type="stepAfter" dataKey="v" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3, fill: "var(--accent)" }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </Section>

        <Section title={`Compared with other ${POSITION_LABEL[p.position_group].toLowerCase()}s`}
          subtitle="Percentile, 2015/16. 90 means better than 90% of players in his position.">
          <div className="rounded-xl border border-line bg-panel px-4 py-2">
            {PERCENTILE_LABELS.map(([k, label, help]) => (
              <PercentileBar key={k} label={label} help={help} value={p.percentiles[k]} />
            ))}
          </div>
        </Section>
      </div>

      <Section title="Per 90 minutes, 2015/16">
        <div className="num grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="xG (no penalties)" value={p.npxg_p90.toFixed(2)} />
          <StatTile label="Goals (no penalties)" value={p.np_goals_p90.toFixed(2)} />
          <StatTile label="xA" value={p.xa_p90.toFixed(2)} />
          <StatTile label="xT" value={p.xt_p90.toFixed(3)} />
        </div>
        {rise != null && p.value_2016_eur && (
          <p className="mt-4 text-sm text-ink-2">
            Between summer 2016 and summer 2018 his market value went from {euro(p.value_2016_eur)} to{" "}
            {euro(p.value_2018_eur)} (<ChangeCell from={p.value_2016_eur} to={p.value_2018_eur} />).
          </p>
        )}
      </Section>
    </div>
  );
}
