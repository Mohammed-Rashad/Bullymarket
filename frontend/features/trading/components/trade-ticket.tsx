"use client";

import { FormEvent, useMemo, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import { errorMessage } from "@/lib/api-client";
import type { Bet, TradeSide } from "@/lib/types";
import {
  useBuy,
  useBuyPreview,
  useLmsrPrice,
  useLmsrQuote,
  useLmsrTrade,
  useMyPositions,
} from "../hooks";

export function TradeTicket({ bet }: { bet: Bet }) {
  return bet.pricing_method === "lmsr" ? (
    <LmsrTradeTicket bet={bet} />
  ) : (
    <LegacyBuyTicket bet={bet} />
  );
}

function LmsrTradeTicket({ bet }: { bet: Bet }) {
  const [side, setSide] = useState<TradeSide>("yes");
  const [action, setAction] = useState<"buy" | "sell">("buy");
  const [shares, setShares] = useState("10");
  const signedShares = action === "sell" ? `-${shares || "0"}` : shares;
  const quote = useLmsrQuote(bet.id, side, signedShares);
  const livePrice = useLmsrPrice(bet.id);
  const positions = useMyPositions(bet.id);
  const execute = useLmsrTrade(bet.id);
  const selectedOutcome = bet.outcomes[side === "yes" ? 0 : 1];
  const heldShares = useMemo(
    () =>
      Number(
        positions.data?.find(
          (position) => position.outcome_id === selectedOutcome?.id,
        )?.shares ?? 0,
      ),
    [positions.data, selectedOutcome?.id],
  );
  const numericShares = Number(shares);
  const invalidSell = action === "sell" && numericShares > heldShares;

  function submit(event: FormEvent) {
    event.preventDefault();
    execute.mutate({ side, shares: signedShares });
  }

  return (
    <form className="form-stack" onSubmit={submit}>
      <div className="form-row">
        <Button
          className={action === "buy" ? "" : "secondary"}
          onClick={() => setAction("buy")}
          type="button"
        >
          Buy
        </Button>
        <Button
          className={action === "sell" ? "" : "secondary"}
          onClick={() => setAction("sell")}
          type="button"
        >
          Sell
        </Button>
      </div>
      <div className="field">
        <label htmlFor="trade-side">Side</label>
        <select
          className="select"
          id="trade-side"
          onChange={(event) => setSide(event.target.value as TradeSide)}
          value={side}
        >
          <option value="yes">
            {bet.outcomes[0]?.label} · {(
              Number(livePrice.data?.price_yes ?? bet.outcomes[0]?.price) * 100
            ).toFixed(1)}%
          </option>
          <option value="no">
            {bet.outcomes[1]?.label} · {(
              Number(livePrice.data?.price_no ?? bet.outcomes[1]?.price) * 100
            ).toFixed(1)}%
          </option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="trade-shares">
          Shares to {action} {action === "sell" ? `(held: ${heldShares.toFixed(4)})` : ""}
        </label>
        <Input
          id="trade-shares"
          min="0.00000001"
          onChange={(event) => setShares(event.target.value)}
          required
          step="0.01"
          type="number"
          value={shares}
        />
      </div>
      {quote.data ? (
        <div className="notice">
          {action === "buy" ? "You pay" : "You receive"}: {" "}
          <strong>{Math.abs(Number(quote.data.cost)).toFixed(4)} points</strong>
          <br />
          Average price: {(Number(quote.data.average_price) * 100).toFixed(2)}¢
          <br />
          Odds after trade: {(Number(quote.data.price_yes_after) * 100).toFixed(1)}% / {" "}
          {(Number(quote.data.price_no_after) * 100).toFixed(1)}%
        </div>
      ) : null}
      {quote.isFetching ? <p className="muted">Updating LMSR quote…</p> : null}
      {invalidSell ? (
        <ErrorNotice message="You cannot sell more shares than you hold." />
      ) : null}
      {quote.error ? <ErrorNotice message={errorMessage(quote.error)} /> : null}
      {execute.error ? <ErrorNotice message={errorMessage(execute.error)} /> : null}
      {execute.data ? (
        <div className="notice pending-notice">
          Trade #{execute.data.trade_id.slice(0, 8)} executed. Position: {" "}
          {Number(execute.data.position_shares).toFixed(4)} shares · Balance: {" "}
          {Number(execute.data.remaining_balance).toFixed(2)} points.
        </div>
      ) : null}
      <Button
        disabled={
          execute.isPending ||
          !quote.data ||
          invalidSell ||
          numericShares <= 0 ||
          bet.status !== "open"
        }
        type="submit"
      >
        {execute.isPending ? "Executing…" : `${action === "buy" ? "Buy" : "Sell"} shares`}
      </Button>
    </form>
  );
}

function LegacyBuyTicket({ bet }: { bet: Bet }) {
  const [outcomeId, setOutcomeId] = useState(bet.outcomes[0]?.id ?? "");
  const [amount, setAmount] = useState("10");
  const preview = useBuyPreview(bet.id, outcomeId, amount);
  const buy = useBuy(bet.id);

  function submit(event: FormEvent) {
    event.preventDefault();
    buy.mutate({ outcome_id: outcomeId, amount });
  }

  return (
    <form className="form-stack" onSubmit={submit}>
      <p className="muted">Historical CPMM market</p>
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
          Estimated shares: {Number(preview.data.shares_out).toFixed(4)}
        </div>
      ) : null}
      {preview.error ? <ErrorNotice message={errorMessage(preview.error)} /> : null}
      {buy.error ? <ErrorNotice message={errorMessage(buy.error)} /> : null}
      <Button
        disabled={buy.isPending || !preview.data || bet.status !== "open"}
        type="submit"
      >
        {buy.isPending ? "Placing trade…" : "Buy shares"}
      </Button>
    </form>
  );
}
