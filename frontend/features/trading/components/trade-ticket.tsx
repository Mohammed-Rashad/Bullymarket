"use client";

import { FormEvent, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import { errorMessage } from "@/lib/api-client";
import type { Bet } from "@/lib/types";
import { useBuy, useBuyPreview } from "../hooks";

export function TradeTicket({ bet }: { bet: Bet }) {
  const [outcomeId, setOutcomeId] = useState(bet.outcomes[0]?.id ?? "");
  const [amount, setAmount] = useState("10");
  const preview = useBuyPreview(bet.id, outcomeId, amount);
  const buy = useBuy(bet.id);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await buy.mutateAsync({ outcome_id: outcomeId, amount });
  }

  return (
    <form className="form-stack" onSubmit={submit}>
      <div className="field">
        <label htmlFor="trade-outcome">Your call</label>
        <select
          className="select"
          id="trade-outcome"
          onChange={(event) => setOutcomeId(event.target.value)}
          value={outcomeId}
        >
          {bet.outcomes.map((outcome) => (
            <option key={outcome.id} value={outcome.id}>
              {outcome.label} · {(Number(outcome.price) * 100).toFixed(1)}%
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="trade-amount">Points to stake</label>
        <Input
          id="trade-amount"
          min="1"
          onChange={(event) => setAmount(event.target.value)}
          required
          step="0.01"
          type="number"
          value={amount}
        />
      </div>
      {preview.data ? (
        <div className="notice">
          Estimated shares: <strong>{Number(preview.data.shares_out).toFixed(4)}</strong>
          <br />
          Odds after trade:{" "}
          {(Number(preview.data.price_yes_after) * 100).toFixed(1)}% /{" "}
          {(Number(preview.data.price_no_after) * 100).toFixed(1)}%
        </div>
      ) : null}
      {preview.isFetching ? (
        <p className="muted" style={{ margin: 0 }}>
          Updating preview…
        </p>
      ) : null}
      {preview.error ? (
        <ErrorNotice message={errorMessage(preview.error)} />
      ) : null}
      {buy.error ? <ErrorNotice message={errorMessage(buy.error)} /> : null}
      {buy.data ? (
        <div className="notice pending-notice">
          Bought {Number(buy.data.shares_out).toFixed(4)} shares. Remaining
          balance: {Number(buy.data.remaining_balance).toFixed(2)} points.
        </div>
      ) : null}
      <Button
        disabled={buy.isPending || !preview.data || bet.status !== "open"}
        type="submit"
      >
        {buy.isPending ? "Placing trade…" : "Buy shares"}
      </Button>
    </form>
  );
}

