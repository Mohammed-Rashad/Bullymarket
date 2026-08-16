"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorNotice, Loading } from "@/components/ui";
import { CreateBetForm } from "@/features/bets/components/create-bet-form";
import { BetListControls } from "@/features/bets/components/bet-list-controls";
import { MarketCard } from "@/features/bets/components/market-card";
import { usePublicBets } from "@/features/bets/hooks";
import {
  LeaderboardPanel,
  WindowTabs,
} from "@/features/leaderboard/components/leaderboard-panel";
import { usePublicLeaderboard } from "@/features/leaderboard/hooks";
import { errorMessage } from "@/lib/api-client";
import type { BetListStatus, LeaderboardWindow } from "@/lib/types";

export default function PublicMarketsPage() {
  const router = useRouter();
  const [betPage, setBetPage] = useState(1);
  const [betStatus, setBetStatus] = useState<BetListStatus>("all");
  const bets = usePublicBets({ page: betPage, status: betStatus });
  const [showCreate, setShowCreate] = useState(false);
  const [window, setWindow] = useState<LeaderboardWindow>("weekly");
  const leaderboard = usePublicLeaderboard(window);

  return (
    <>
      <header className="page-title">
        <div>
          <span className="eyebrow">Standalone platform markets</span>
          <h1>Public calls</h1>
          <p>
            These markets belong to no group. Their results feed only the
            public leaderboard.
          </p>
        </div>
        <Button onClick={() => setShowCreate((value) => !value)} type="button">
          {showCreate ? "Close form" : "Create public bet"}
        </Button>
      </header>

      {showCreate ? (
        <Card className="card-pad" style={{ marginBottom: 24 }}>
          <span className="eyebrow">No group attribution</span>
          <h2>Open a public market</h2>
          <CreateBetForm
            onCreated={(betId) => router.push(`/bets/${betId}`)}
          />
        </Card>
      ) : null}

      <div className="content-grid">
        <section className="stack">
          <BetListControls
            data={bets.data}
            disabled={bets.isFetching}
            onPageChange={setBetPage}
            onStatusChange={(status) => {
              setBetStatus(status);
              setBetPage(1);
            }}
            status={betStatus}
          />
          {bets.isLoading ? <Loading /> : null}
          {bets.error ? <ErrorNotice message={errorMessage(bets.error)} /> : null}
          {!bets.isLoading && !bets.data?.items?.length ? (
            <EmptyState
              body="Create the first standalone market for signed-in players."
              title="No public calls yet"
            />
          ) : null}
          {bets.data?.items?.map((bet) => <MarketCard bet={bet} key={bet.id} />)}
        </section>
        <aside className="stack">
          <Card className="card-pad">
            <span className="eyebrow">Public bets only</span>
            <h2>Global leaderboard</h2>
            <p className="muted">
              Private group performance never enters this ranking.
            </p>
            <WindowTabs onChange={setWindow} value={window} />
            <div style={{ marginTop: 16 }}>
              <LeaderboardPanel
                data={leaderboard.data}
                error={leaderboard.error}
                isLoading={leaderboard.isLoading}
              />
            </div>
          </Card>
        </aside>
      </div>
    </>
  );
}
