import { apiFetch } from "@/lib/api-client";
import type { Leaderboard, LeaderboardWindow } from "@/lib/types";

export function getGroupLeaderboard(
  groupId: string,
  window: LeaderboardWindow,
) {
  return apiFetch<Leaderboard>(
    `/groups/${groupId}/leaderboard?window=${window}`,
  );
}

export function getPublicLeaderboard(window: LeaderboardWindow) {
  return apiFetch<Leaderboard>(`/leaderboards/public?window=${window}`);
}

