import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Bet } from "@/lib/types";
import { TradeTicket } from "./trade-ticket";

vi.mock("../hooks", () => ({
  useLmsrPrice: () => ({ data: { price_yes: "0.5", price_no: "0.5" } }),
  useLmsrQuote: () => ({
    data: {
      cost: "5.12494795",
      average_price: "0.51249480",
      price_yes_after: "0.52497919",
      price_no_after: "0.47502081",
    },
    error: null,
    isFetching: false,
  }),
  useLmsrTrade: () => ({
    data: null,
    error: null,
    isPending: false,
    mutate: vi.fn(),
  }),
  useBuyPreview: vi.fn(),
  useBuy: vi.fn(),
}));

afterEach(cleanup);

const bet: Bet = {
  id: "bet-1",
  group_id: null,
  created_by: "user-1",
  question: "Will it happen?",
  description: null,
  visibility: "public",
  status: "open",
  end_time: "2030-01-01T00:00:00Z",
  resolved_outcome_id: null,
  resolved_at: null,
  created_at: "2029-12-01T00:00:00Z",
  pricing_method: "lmsr",
  b_liquidity: "100",
  q_yes: "0",
  q_no: "0",
  house_reserve: "69.31471806",
  house_cash_balance: "0",
  house_profit_loss: null,
  outcomes: [
    { id: "yes", label: "Yes", display_order: 0, pool_shares: "0", price: "0.5" },
    { id: "no", label: "No", display_order: 1, pool_shares: "0", price: "0.5" },
  ],
};

describe("TradeTicket", () => {
  it("accepts whole-number shares and temporarily exposes buying only", () => {
    render(<TradeTicket bet={bet} />);

    const shares = screen.getByLabelText("Shares to buy");
    expect(shares).toHaveValue(10);
    expect(shares).toHaveAttribute("min", "0.01");
    expect(shares).toHaveAttribute("step", "0.01");
    expect(shares).toBeValid();
    expect(screen.getByRole("button", { name: "Buy shares" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sell" })).not.toBeInTheDocument();
  });
});
