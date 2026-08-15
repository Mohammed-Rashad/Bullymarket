import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { Bet } from "@/lib/types";
import { MarketCard } from "./market-card";

afterEach(cleanup);

const bet: Bet = {
  id: "bet-1",
  group_id: null,
  created_by: "user-1",
  question: "Will the launch happen on time?",
  description: null,
  visibility: "public",
  status: "open",
  end_time: "2030-01-01T00:00:00Z",
  resolved_outcome_id: null,
  resolved_at: null,
  created_at: "2029-12-01T00:00:00Z",
  pricing_method: "lmsr",
  b_liquidity: "100",
  q_yes: "20",
  q_no: "10",
  house_reserve: "69.31471806",
  house_cash_balance: "5",
  house_profit_loss: null,
  outcomes: [
    {
      id: "yes",
      label: "Yes",
      display_order: 0,
      pool_shares: "100",
      price: "0.64",
    },
    {
      id: "no",
      label: "No",
      display_order: 1,
      pool_shares: "100",
      price: "0.36",
    },
  ],
};

describe("MarketCard", () => {
  it("renders API-provided odds without recalculating them", () => {
    render(<MarketCard bet={bet} />);

    expect(
      screen.getByText("Will the launch happen on time?"),
    ).toBeInTheDocument();
    expect(screen.getByText("64%")).toBeInTheDocument();
    expect(screen.getByText("36%")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/bets/bet-1");
  });
});
