import type { Bet, Group } from "@/lib/types";

export function canEditEndTime(
  bet: Bet,
  userId: string | undefined,
  group: Group | undefined,
) {
  if (bet.status === "resolved" || bet.status === "cancelled") return false;
  if (bet.visibility === "group") return group?.role === "admin";
  return bet.created_by === userId;
}

export function canCancelBet(
  bet: Bet,
  userId: string | undefined,
  group: Group | undefined,
) {
  if (bet.status === "resolved" || bet.status === "cancelled") return false;
  if (bet.visibility === "group") {
    return bet.created_by === userId || group?.role === "admin";
  }
  return bet.created_by === userId;
}

export function canResolveBet(bet: Bet, group: Group | undefined) {
  if (bet.status !== "closed") return false;
  return bet.visibility === "public" || group?.role === "admin";
}
