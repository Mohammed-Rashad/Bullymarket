"use client";

import { EmptyState, ErrorNotice, Loading } from "@/components/ui";
import { errorMessage } from "@/lib/api-client";
import type {
  Leaderboard,
  LeaderboardWindow,
} from "@/lib/types";

const windows: { value: LeaderboardWindow; label: string }[] = [
  { value: "weekly", label: "7 days" },
  { value: "biweekly", label: "14 days" },
  { value: "monthly", label: "30 days" },
  { value: "all_time", label: "All time" },
];

export function WindowTabs({
  value,
  onChange,
}: {
  value: LeaderboardWindow;
  onChange: (value: LeaderboardWindow) => void;
}) {
  return (
    <div className="tabs">
      {windows.map((window) => (
        <button
          className={window.value === value ? "active" : ""}
          key={window.value}
          onClick={() => onChange(window.value)}
          type="button"
        >
          {window.label}
        </button>
      ))}
    </div>
  );
}

export function LeaderboardPanel({
  data,
  isLoading,
  error,
}: {
  data?: Leaderboard;
  isLoading: boolean;
  error: unknown;
}) {
  if (isLoading) return <Loading label="Calculating realized results…" />;
  if (error) return <ErrorNotice message={errorMessage(error)} />;
  if (!data?.entries.length) {
    return (
      <EmptyState
        body="Resolved bets in this exact scope will appear here."
        title="No settled calls yet"
      />
    );
  }
  return (
    <div className="card leaderboard">
      {data.entries.map((entry) => {
        const amount = Number(entry.net_profit_loss);
        return (
          <div className="leader-row" key={entry.user_id}>
            <span className="rank">{entry.rank}</span>
            <strong className="leader-name">{entry.display_name}</strong>
            <strong className={amount >= 0 ? "positive" : "negative"}>
              {amount >= 0 ? "+" : ""}
              {amount.toFixed(2)} pts
            </strong>
          </div>
        );
      })}
    </div>
  );
}

