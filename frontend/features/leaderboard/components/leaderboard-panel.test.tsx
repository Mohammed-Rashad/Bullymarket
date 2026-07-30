import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { Leaderboard } from "@/lib/types";
import { LeaderboardPanel } from "./leaderboard-panel";

afterEach(cleanup);

describe("LeaderboardPanel", () => {
  it("labels realized net results with positive and negative signs", () => {
    const data: Leaderboard = {
      scope: "group:one",
      window: "all_time",
      entries: [
        {
          rank: 1,
          user_id: "one",
          display_name: "Maha",
          net_profit_loss: "12.5",
        },
        {
          rank: 2,
          user_id: "two",
          display_name: "Omar",
          net_profit_loss: "-4",
        },
      ],
    };

    render(<LeaderboardPanel data={data} error={null} isLoading={false} />);

    expect(screen.getByText("+12.50 pts")).toHaveClass("positive");
    expect(screen.getByText("-4.00 pts")).toHaveClass("negative");
    expect(screen.queryByText(/balance/i)).not.toBeInTheDocument();
  });
});

