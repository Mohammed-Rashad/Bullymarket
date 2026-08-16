import { describe, expect, it } from "vitest";

import type { Bet } from "@/lib/types";
import { normalizeBetPage } from "./api";

const bet = (id: string, status: Bet["status"]): Bet =>
  ({ id, status } as Bet);

describe("normalizeBetPage", () => {
  it("adapts and filters the legacy array response", () => {
    const page = normalizeBetPage(
      [bet("1", "open"), bet("2", "resolved"), bet("3", "resolved")],
      { page: 2, pageSize: 1, status: "resolved" },
    );

    expect(page).toEqual({
      items: [bet("3", "resolved")],
      page: 2,
      page_size: 1,
      total: 2,
      total_pages: 2,
    });
  });

  it("keeps the paginated API response unchanged", () => {
    const response = {
      items: [bet("1", "open")],
      page: 1,
      page_size: 6,
      total: 1,
      total_pages: 1,
    };

    expect(normalizeBetPage(response, { page: 1, status: "all" })).toBe(
      response,
    );
  });
});
