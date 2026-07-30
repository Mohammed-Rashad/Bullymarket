"use client";

import { useParams, useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import {
  Button,
  Card,
  ErrorNotice,
  Input,
  Loading,
} from "@/components/ui";
import {
  useBet,
  useCancelBet,
  useEditEndTime,
  useEditEvents,
  useResolutionEvents,
  useResolveBet,
} from "@/features/bets/hooks";
import { useGroups } from "@/features/groups/hooks";
import { TradeTicket } from "@/features/trading/components/trade-ticket";
import { useMyPositions } from "@/features/trading/hooks";
import { useMe } from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api-client";

export default function BetDetailPage() {
  const params = useParams<{ betId: string }>();
  const router = useRouter();
  const betId = params.betId;
  const betQuery = useBet(betId);
  const me = useMe();
  const groups = useGroups();
  const positions = useMyPositions(betId);
  const resolutionEvents = useResolutionEvents(betId);
  const editEvents = useEditEvents(betId);
  const resolve = useResolveBet(betId);
  const cancel = useCancelBet(betId);
  const editEndTime = useEditEndTime(betId);
  const [newEndTime, setNewEndTime] = useState("");

  const bet = betQuery.data;
  const group = useMemo(
    () => groups.data?.find((item) => item.id === bet?.group_id),
    [bet?.group_id, groups.data],
  );
  const canResolve =
    bet?.visibility === "public" || group?.role === "admin";
  const canManage =
    bet?.created_by === me.data?.id || group?.role === "admin";

  if (betQuery.isLoading) return <Loading label="Loading market…" />;
  if (betQuery.error) {
    return <ErrorNotice message={errorMessage(betQuery.error)} />;
  }
  if (!bet) return null;

  async function submitEndTime(event: FormEvent) {
    event.preventDefault();
    await editEndTime.mutateAsync(new Date(newEndTime).toISOString());
    setNewEndTime("");
  }

  return (
    <div className="stack">
      <Card className="market-detail-header">
        <div className="market-meta">
          <span className="scope-chip">
            {bet.visibility === "public" ? "standalone public" : group?.name ?? "group"}
          </span>
          <span className={`status ${bet.status}`}>{bet.status}</span>
        </div>
        <h1>{bet.question}</h1>
        {bet.description ? <p className="muted">{bet.description}</p> : null}
        <p className="market-meta">
          Betting closes {new Date(bet.end_time).toLocaleString()}
        </p>
        <div className="odds-grid">
          {bet.outcomes.map((outcome) => (
            <div className="odds-card" key={outcome.id}>
              <span>{outcome.label}</span>
              <strong>{(Number(outcome.price) * 100).toFixed(1)}%</strong>
              <small>{Number(outcome.pool_shares).toFixed(2)} pool shares</small>
            </div>
          ))}
        </div>
      </Card>

      <div className="content-grid">
        <section className="stack">
          {bet.status === "open" ? (
            <Card className="card-pad">
              <span className="eyebrow">API-calculated preview</span>
              <h2>Take a position</h2>
              <TradeTicket bet={bet} />
            </Card>
          ) : null}

          <Card className="card-pad">
            <div className="section-heading">
              <div>
                <span className="eyebrow">Your exposure</span>
                <h2>Positions</h2>
              </div>
            </div>
            {positions.data?.length ? (
              <div className="stack">
                {positions.data.map((position) => {
                  const outcome = bet.outcomes.find(
                    (item) => item.id === position.outcome_id,
                  );
                  return (
                    <div className="leader-row" key={position.outcome_id}>
                      <strong className="leader-name">{outcome?.label}</strong>
                      <span>{Number(position.shares).toFixed(4)} shares</span>
                      <span className="muted">
                        {Number(position.points_spent).toFixed(2)} pts staked
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="muted">You do not hold a position in this market.</p>
            )}
          </Card>

          {resolutionEvents.data?.length ? (
            <Card className="card-pad">
              <span className="eyebrow">Audit trail</span>
              <h2>Resolution history</h2>
              <div className="stack">
                {resolutionEvents.data.map((event) => {
                  const outcome = bet.outcomes.find(
                    (item) => item.id === event.outcome_id,
                  );
                  return (
                    <div className="leader-row" key={event.id}>
                      <strong className="leader-name">
                        {event.is_correction ? "Corrected to" : "Resolved"}{" "}
                        {outcome?.label}
                      </strong>
                      <span className="muted">
                        {new Date(event.created_at).toLocaleString()}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>
          ) : null}

          {editEvents.data?.length ? (
            <Card className="card-pad">
              <span className="eyebrow">Change log</span>
              <h2>End-time edits</h2>
              {editEvents.data.map((event) => (
                <p className="muted" key={event.id}>
                  {new Date(event.old_value).toLocaleString()} →{" "}
                  {new Date(event.new_value).toLocaleString()}
                </p>
              ))}
            </Card>
          ) : null}
        </section>

        <aside className="stack">
          {canResolve && (bet.status === "closed" || bet.status === "resolved") ? (
            <Card className="card-pad">
              <span className="eyebrow">
                {bet.status === "resolved" ? "Correction" : "Settlement"}
              </span>
              <h2>
                {bet.status === "resolved" ? "Correct outcome" : "Pick the winner"}
              </h2>
              <p className="muted">
                Payouts and any later reversal are recorded in the ledger.
              </p>
              <div className="form-stack">
                {bet.outcomes.map((outcome) => (
                  <Button
                    className="secondary"
                    disabled={
                      resolve.isPending ||
                      bet.resolved_outcome_id === outcome.id
                    }
                    key={outcome.id}
                    onClick={() => resolve.mutate(outcome.id)}
                    type="button"
                  >
                    {outcome.label} wins
                  </Button>
                ))}
              </div>
              {resolve.error ? (
                <ErrorNotice message={errorMessage(resolve.error)} />
              ) : null}
            </Card>
          ) : null}

          {canManage && bet.status !== "resolved" ? (
            <Card className="card-pad">
              <span className="eyebrow">Market controls</span>
              <h2>Edit close time</h2>
              <form className="form-stack" onSubmit={submitEndTime}>
                <Input
                  min={new Date().toISOString().slice(0, 16)}
                  onChange={(event) => setNewEndTime(event.target.value)}
                  required
                  type="datetime-local"
                  value={newEndTime}
                />
                <Button
                  className="secondary"
                  disabled={editEndTime.isPending}
                  type="submit"
                >
                  Save new time
                </Button>
              </form>
              <hr style={{ border: 0, borderTop: "1px solid var(--line)", margin: "22px 0" }} />
              <Button
                className="danger"
                disabled={cancel.isPending}
                onClick={() =>
                  cancel.mutate(undefined, {
                    onSuccess: () =>
                      router.push(
                        bet.group_id ? `/groups/${bet.group_id}` : "/public",
                      ),
                  })
                }
                type="button"
              >
                Cancel and refund
              </Button>
              {editEndTime.error ? (
                <ErrorNotice message={errorMessage(editEndTime.error)} />
              ) : null}
              {cancel.error ? (
                <ErrorNotice message={errorMessage(cancel.error)} />
              ) : null}
            </Card>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

