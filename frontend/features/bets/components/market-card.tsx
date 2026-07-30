import Link from "next/link";

import type { Bet } from "@/lib/types";

export function MarketCard({ bet }: { bet: Bet }) {
  return (
    <Link className="card market-card" href={`/bets/${bet.id}`}>
      <div className="market-meta">
        <span className={`status ${bet.status}`}>{bet.status}</span>
        <span>
          closes {new Date(bet.end_time).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
        </span>
      </div>
      <h3>{bet.question}</h3>
      <div className="outcome-bars">
        {bet.outcomes.map((outcome) => (
          <span className="outcome-pill" key={outcome.id}>
            {outcome.label}
            <strong>{Math.round(Number(outcome.price) * 100)}%</strong>
          </span>
        ))}
      </div>
    </Link>
  );
}

