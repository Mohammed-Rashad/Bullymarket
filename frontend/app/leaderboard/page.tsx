"use client";

import { useState } from "react";

import { Card } from "@/components/ui";
import {
  LeaderboardPanel,
  WindowTabs,
} from "@/features/leaderboard/components/leaderboard-panel";
import { usePublicLeaderboard } from "@/features/leaderboard/hooks";
import type { LeaderboardWindow } from "@/lib/types";

export default function LeaderboardPage() {
  const [window, setWindow] = useState<LeaderboardWindow>("weekly");
  const leaderboard = usePublicLeaderboard(window);

  return (
    <>
      <header className="page-title">
        <div>
          <span className="eyebrow">Standalone public performance</span>
          <h1>Global leaderboard</h1>
          <p>
            Realized net points from resolved public bets—never wallet
            balances or private group activity.
          </p>
        </div>
        <WindowTabs onChange={setWindow} value={window} />
      </header>
      <Card className="card-pad">
        <LeaderboardPanel
          data={leaderboard.data}
          error={leaderboard.error}
          isLoading={leaderboard.isLoading}
        />
      </Card>
    </>
  );
}

