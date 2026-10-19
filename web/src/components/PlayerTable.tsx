import { Link } from "react-router-dom";
import { change, euro, pct, type Player } from "../data";
import { Pill } from "./ui";

export function ChangeCell({ from, to }: { from: number | null; to: number | null }) {
  const c = change(from, to);
  if (c == null) return <span className="text-ink-3">no 2018 value</span>;
  return <span className={c > 0 ? "text-good" : c < 0 ? "text-bad" : "text-ink-2"}>{pct(c)}</span>;
}

export default function PlayerTable({ rows, showRank = true }: { rows: Player[]; showRank?: boolean }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-panel">
      <table className="num w-full min-w-[720px] text-sm">
        <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-3">
          <tr>
            {showRank && <th className="px-3 py-2 font-medium">#</th>}
            <th className="px-3 py-2 font-medium">Player</th>
            <th className="px-3 py-2 font-medium">Age</th>
            <th className="px-3 py-2 text-right font-medium">Price 2016</th>
            <th className="px-3 py-2 text-right font-medium">Fair value</th>
            <th className="px-3 py-2 text-right font-medium">Gap</th>
            <th className="px-3 py-2 text-right font-medium">Price 2018</th>
            <th className="px-3 py-2 text-right font-medium">Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.player_id} className="border-b border-line last:border-0 hover:bg-accent-soft/50">
              {showRank && <td className="px-3 py-2 text-ink-3">{p.gap_rank ?? "–"}</td>}
              <td className="px-3 py-2">
                <Link to={`/player/${p.player_id}`} className="font-medium text-ink hover:text-accent hover:underline">
                  {p.name}
                </Link>
                <div className="text-xs text-ink-3">
                  {p.team} · {p.league} · {p.position_group}{" "}
                  {p.relegated && <Pill tone="warn">relegated</Pill>}
                </div>
              </td>
              <td className="px-3 py-2 text-ink-2">{p.age?.toFixed(0) ?? "–"}</td>
              <td className="px-3 py-2 text-right">{euro(p.value_2016_eur)}</td>
              <td className="px-3 py-2 text-right">{euro(p.predicted_value_eur)}</td>
              <td className="px-3 py-2 text-right font-medium text-accent">{pct(p.value_gap_pct)}</td>
              <td className="px-3 py-2 text-right">{euro(p.value_2018_eur)}</td>
              <td className="px-3 py-2 text-right">
                <ChangeCell from={p.value_2016_eur} to={p.value_2018_eur} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
