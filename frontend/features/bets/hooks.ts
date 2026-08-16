"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { BetListStatus, CreateBetInput } from "@/lib/types";
import * as betsApi from "./api";

export interface BetListOptions {
  page: number;
  status: BetListStatus;
}

export function useGroupBets(
  groupId: string,
  options: BetListOptions,
  enabled = true,
) {
  return useQuery({
    queryKey: ["group-bets", groupId, options],
    queryFn: () => betsApi.listGroupBets(groupId, options),
    enabled: Boolean(groupId) && enabled,
    refetchInterval: 8_000,
  });
}

export function usePublicBets(options: BetListOptions) {
  return useQuery({
    queryKey: ["public-bets", options],
    queryFn: () => betsApi.listPublicBets(options),
    refetchInterval: 8_000,
  });
}

export function useBet(betId: string) {
  return useQuery({
    queryKey: ["bet", betId],
    queryFn: () => betsApi.getBet(betId),
    enabled: Boolean(betId),
    refetchInterval: 5_000,
  });
}

export function useCreateBet(groupId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateBetInput) =>
      groupId
        ? betsApi.createGroupBet(groupId, input)
        : betsApi.createPublicBet(input),
    onSuccess: (bet) => {
      void queryClient.invalidateQueries({
        queryKey: groupId ? ["group-bets", groupId] : ["public-bets"],
      });
      queryClient.setQueryData(["bet", bet.id], bet);
    },
  });
}

function useBetMutation<TInput, TResult>(
  betId: string,
  mutationFn: (input: TInput) => Promise<TResult>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["bet", betId] });
      void queryClient.invalidateQueries({ queryKey: ["group-bets"] });
      void queryClient.invalidateQueries({ queryKey: ["public-bets"] });
      void queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
      void queryClient.invalidateQueries({ queryKey: ["me"] });
      void queryClient.invalidateQueries({ queryKey: ["groups"] });
    },
  });
}

export function useEditEndTime(betId: string) {
  return useBetMutation(betId, (endTime: string) =>
    betsApi.editEndTime(betId, endTime),
  );
}

export function useCancelBet(betId: string) {
  return useBetMutation(betId, () => betsApi.cancelBet(betId));
}

export function useResolveBet(betId: string) {
  return useBetMutation(betId, (outcomeId: string) =>
    betsApi.resolveBet(betId, outcomeId),
  );
}

export function useResolutionEvents(betId: string) {
  return useQuery({
    queryKey: ["bet", betId, "resolution-events"],
    queryFn: () => betsApi.listResolutionEvents(betId),
    enabled: Boolean(betId),
  });
}

export function useEditEvents(betId: string) {
  return useQuery({
    queryKey: ["bet", betId, "edit-events"],
    queryFn: () => betsApi.listEditEvents(betId),
    enabled: Boolean(betId),
  });
}
