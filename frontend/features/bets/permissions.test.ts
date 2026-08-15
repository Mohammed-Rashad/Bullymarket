import { describe, expect, it } from "vitest";

import type { Bet, Group } from "@/lib/types";
import { canCancelBet, canEditEndTime, canResolveBet } from "./permissions";

const bet = {
  id: "bet-1",
  created_by: "creator",
  visibility: "group",
  status: "open",
} as Bet;

const memberGroup = { role: "member" } as Group;
const adminGroup = { role: "admin" } as Group;

describe("bet management permissions", () => {
  it("does not let a non-admin group creator edit the end time", () => {
    expect(canEditEndTime(bet, "creator", memberGroup)).toBe(false);
    expect(canCancelBet(bet, "creator", memberGroup)).toBe(true);
  });

  it("lets a group admin edit an unresolved end time", () => {
    expect(canEditEndTime(bet, "admin", adminGroup)).toBe(true);
  });

  it("makes resolution final", () => {
    const resolvedBet = { ...bet, status: "resolved" } as Bet;
    expect(canEditEndTime(resolvedBet, "admin", adminGroup)).toBe(false);
    expect(canCancelBet(resolvedBet, "admin", adminGroup)).toBe(false);
    expect(canResolveBet(resolvedBet, adminGroup)).toBe(false);
  });

  it("retains end-time editing for a public market creator", () => {
    const publicBet = { ...bet, visibility: "public" } as Bet;
    expect(canEditEndTime(publicBet, "creator", undefined)).toBe(true);
    expect(canEditEndTime(publicBet, "someone-else", undefined)).toBe(false);
  });
});
