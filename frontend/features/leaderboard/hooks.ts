"use client";

import { useQuery } from "@tanstack/react-query";

import type { LeaderboardWindow } from "@/lib/types";
import * as leaderboardApi from "./api";

export function useGroupLeaderboard(
  groupId: string,
  window: LeaderboardWindow,
  enabled = true,
) {
  return useQuery({
    queryKey: ["leaderboard", "group", groupId, window],
    queryFn: () => leaderboardApi.getGroupLeaderboard(groupId, window),
    enabled: Boolean(groupId) && enabled,
  });
}

export function usePublicLeaderboard(window: LeaderboardWindow) {
  return useQuery({
    queryKey: ["leaderboard", "public", window],
    queryFn: () => leaderboardApi.getPublicLeaderboard(window),
  });
}
