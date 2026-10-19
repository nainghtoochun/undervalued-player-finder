import { Section } from "../components/ui";
import { pct, useData } from "../data";

const REPO = "https://github.com/nainghtoochun/undervalued-player-finder";

const STEPS = [
  ["Measure every action", "5.4 million on-ball events from StatsBomb's free 2015/16 data. Every pass, carry and shot, with where it started and ended."],
  ["Score the shots (xG)", "A gradient boosting model gives each shot a goal probability from its distance, angle and the positions of every defender and the keeper at that moment. It comes within 0.003 log loss of StatsBomb's professional model."],
  ["Score the ball moves (xT)", "The pitch is split into 192 zones. Expected Threat says how likely a goal is to follow from each zone, so every pass or dribble earns credit for moving the ball into danger."],
  ["Build a stat sheet", "Minutes played come from lineups, substitutions and red cards. Then xG, xA and xT per 90 minutes for 1,352 regular players."],
  ["Put a fair price on each player", "A ridge regression learns how Transfermarkt prices relate to stats, age, position and league. Each player's fair value comes from a model that never saw his own price. Club is deliberately left out, so a great season at a small club stands out."],
  ["Check against the future", "Did the players with the biggest gap between fair value and price really rise in value by 2018? The comparison accounts for age, position, league and starting price, because young and cheap players rise anyway."],
];

export default function Method() {
  const { summary } = useData();
  const b = summary?.backtest;
  return (
    <div className="max-w-3xl">
      <h1 className="text-3xl font-semibold tracking-tight">How it works</h1>
      <p className="mt-3 text-lg text-ink-2">Six steps, from raw match events to a list of bargains, and an honest check of whether it worked.</p>

      <ol className="mt-8 space-y-6">
        {STEPS.map(([title, body], i) => (
          <li key={title} className="flex gap-4">
            <span className="num flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">{i + 1}</span>
            <div>
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-1 text-ink-2">{body}</p>
            </div>
          </li>
        ))}
      </ol>

      {b && (
        <Section title="Result">
          <p className="text-ink-2">
            The top {b.top_n} flagged players gained <span className="font-medium text-ink">{pct(Math.exp(b.extra_growth_log_top_minus_rest) - 1)}</span>{" "}
            more value than similar players between summer 2016 and summer 2018 (95% range{" "}
            {pct(Math.exp(b.extra_growth_ci95[0]) - 1)} to {pct(Math.exp(b.extra_growth_ci95[1]) - 1)}). Their median value went{" "}
            {pct(b.top_median_growth)} while everyone else's went {pct(b.rest_median_growth)}.
          </p>
        </Section>
      )}

      <Section title="Limits">
        <ul className="list-disc space-y-2 pl-5 text-ink-2">
          <li>Market values are Transfermarkt estimates, not real transfer fees.</li>
          <li>Some of the rise may be prices that were simply too low by chance moving back up.</li>
          <li>One season of stats, so a lucky season can look like a bargain.</li>
          <li>The signal is strong at the top of the list and weak across all players.</li>
          <li>The free Bundesliga data only covers Bayer Leverkusen, so the Bundesliga trains the models but is not ranked.</li>
        </ul>
      </Section>

      <Section title="Built with">
        <p className="text-ink-2">
          Python (pandas, scikit-learn), Postgres, FastAPI, React, TypeScript, Tailwind and Recharts. Tested with
          pytest and GitHub Actions. Code, design decisions and weekly notes are on{" "}
          <a className="text-accent underline" href={REPO}>GitHub</a>.
        </p>
      </Section>
    </div>
  );
}
