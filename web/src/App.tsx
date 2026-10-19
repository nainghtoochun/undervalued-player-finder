import { NavLink, Route, Routes } from "react-router-dom";
import { useData } from "./data";
import Explorer from "./pages/Explorer";
import Home from "./pages/Home";
import Method from "./pages/Method";
import PlayerPage from "./pages/Player";

const REPO = "https://github.com/nainghtoochun/undervalued-player-finder";

function NavItem({ to, children }: { to: string; children: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          isActive ? "bg-accent-soft text-accent" : "text-ink-2 hover:text-ink"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  const { players, error } = useData();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="inline-block h-6 w-6 rounded-full bg-accent" aria-hidden />
            Undervalued Player Finder
          </NavLink>
          <nav className="flex items-center gap-1">
            <NavItem to="/">Home</NavItem>
            <NavItem to="/explore">Explorer</NavItem>
            <NavItem to="/method">Method</NavItem>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        {error ? (
          <p className="rounded-lg border border-line bg-panel p-6 text-bad">Something went wrong. {error}</p>
        ) : !players ? (
          <p className="py-24 text-center text-ink-2">Loading 1,352 players…</p>
        ) : (
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explorer />} />
            <Route path="/method" element={<Method />} />
            <Route path="/player/:id" element={<PlayerPage />} />
            <Route path="*" element={<p className="text-ink-2">Page not found.</p>} />
          </Routes>
        )}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-6 text-sm text-ink-3">
          <span>
            Built by Naing Htoo Chun ·{" "}
            <a className="underline hover:text-ink" href={REPO}>
              Source on GitHub
            </a>
          </span>
          <span>
            Data:{" "}
            <a className="underline hover:text-ink" href="https://github.com/statsbomb/open-data">
              StatsBomb Open Data
            </a>{" "}
            and{" "}
            <a className="underline hover:text-ink" href="https://github.com/dcaribou/transfermarkt-datasets">
              transfermarkt-datasets
            </a>
          </span>
        </div>
      </footer>
    </div>
  );
}
