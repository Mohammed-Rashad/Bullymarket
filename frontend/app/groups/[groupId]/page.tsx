"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import {
  Button,
  Card,
  EmptyState,
  ErrorNotice,
  Loading,
} from "@/components/ui";
import { CreateBetForm } from "@/features/bets/components/create-bet-form";
import { MarketCard } from "@/features/bets/components/market-card";
import { useGroupBets } from "@/features/bets/hooks";
import {
  useGroupMembers,
  useGroups,
  useRemoveMember,
} from "@/features/groups/hooks";
import {
  LeaderboardPanel,
  WindowTabs,
} from "@/features/leaderboard/components/leaderboard-panel";
import { useGroupLeaderboard } from "@/features/leaderboard/hooks";
import { errorMessage } from "@/lib/api-client";
import type { LeaderboardWindow } from "@/lib/types";

export default function GroupDetailPage() {
  const params = useParams<{ groupId: string }>();
  const router = useRouter();
  const groupId = params.groupId;
  const groups = useGroups();
  const group = groups.data?.find((item) => item.id === groupId);
  const isActive = group?.membership_status === "active";
  const bets = useGroupBets(groupId, Boolean(group));
  const members = useGroupMembers(groupId, Boolean(group && isActive));
  const removeMember = useRemoveMember(groupId);
  const [window, setWindow] = useState<LeaderboardWindow>("weekly");
  const leaderboard = useGroupLeaderboard(
    groupId,
    window,
    Boolean(group && isActive),
  );
  const [showCreate, setShowCreate] = useState(false);

  if (groups.isLoading) return <Loading label="Opening group…" />;
  if (groups.error) return <ErrorNotice message={errorMessage(groups.error)} />;
  if (!group) {
    return (
      <EmptyState
        body="This group is not in your active or pending-settlement list."
        title="Group unavailable"
      />
    );
  }

  return (
    <>
      <header className="page-title">
        <div>
          <span className="eyebrow">
            {isActive && group.invite_code
              ? `Invite · ${group.invite_code}`
              : "Settlement access"}
          </span>
          <h1>{group.name}</h1>
          <p>{group.description ?? "Private group markets and standings."}</p>
        </div>
        {isActive ? (
          <Button onClick={() => setShowCreate((value) => !value)} type="button">
            {showCreate ? "Close form" : "Create bet"}
          </Button>
        ) : null}
      </header>

      {!isActive ? (
        <div className="notice pending-notice" style={{ marginBottom: 24 }}>
          You were removed from this group. The markets below are only the ones
          where you already hold a position. You may continue them until they
          resolve or are cancelled; newer group markets remain hidden.
        </div>
      ) : null}

      {showCreate && isActive ? (
        <Card className="card-pad" style={{ marginBottom: 24 }}>
          <div className="section-heading">
            <div>
              <span className="eyebrow">Group-only market</span>
              <h2>Open a new call</h2>
            </div>
          </div>
          <CreateBetForm
            groupId={groupId}
            members={members.data}
            onCreated={(betId) => router.push(`/bets/${betId}`)}
          />
        </Card>
      ) : null}

      <div className="content-grid">
        <section className="stack">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Markets</span>
              <h2>{isActive ? "Group calls" : "Your unsettled positions"}</h2>
            </div>
          </div>
          {bets.isLoading ? <Loading /> : null}
          {bets.error ? (
            <ErrorNotice message={errorMessage(bets.error)} />
          ) : null}
          {!bets.isLoading && !bets.data?.length ? (
            <EmptyState
              body={
                isActive
                  ? "Open the first market for this group."
                  : "All your positions from this group are settled."
              }
              title="Nothing open here"
            />
          ) : null}
          {bets.data?.map((bet) => <MarketCard bet={bet} key={bet.id} />)}
        </section>

        <aside className="stack">
          {isActive ? (
            <Card className="card-pad">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Realized P/L</span>
                  <h2>Group leaderboard</h2>
                </div>
              </div>
              <WindowTabs onChange={setWindow} value={window} />
              <div style={{ marginTop: 16 }}>
                <LeaderboardPanel
                  data={leaderboard.data}
                  error={leaderboard.error}
                  isLoading={leaderboard.isLoading}
                />
              </div>
            </Card>
          ) : null}

          {isActive ? (
            <Card className="card-pad">
              <h2>Members</h2>
              <div className="stack">
                {members.data?.map((member) => (
                  <div className="market-meta" key={member.user_id}>
                    <span>
                      {member.user_id.slice(0, 8)} · {member.role}
                    </span>
                    {group.role === "admin" &&
                    member.role !== "admin" &&
                    member.status === "active" ? (
                      <button
                        className="text-button"
                        disabled={removeMember.isPending}
                        onClick={() => removeMember.mutate(member.user_id)}
                        type="button"
                      >
                        Remove
                      </button>
                    ) : (
                      <span>{member.status}</span>
                    )}
                  </div>
                ))}
              </div>
              {removeMember.error ? (
                <ErrorNotice message={errorMessage(removeMember.error)} />
              ) : null}
            </Card>
          ) : null}
        </aside>
      </div>
    </>
  );
}
