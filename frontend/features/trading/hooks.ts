"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import * as tradingApi from "./api";
import type { TradeSide } from "@/lib/types";

export function useBuyPreview(
  betId: string,
  outcomeId: string,
  amount: string,
) {
  const [debouncedAmount, setDebouncedAmount] = useState(amount);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedAmount(amount), 350);
    return () => window.clearTimeout(timeout);
  }, [amount]);
  const numericAmount = Number(debouncedAmount);
  return useQuery({
    queryKey: ["trade-preview", betId, outcomeId, debouncedAmount],
    queryFn: () =>
      tradingApi.previewBuy(betId, {
        outcome_id: outcomeId,
        amount: debouncedAmount,
      }),
    enabled:
      Boolean(betId && outcomeId) &&
      Number.isFinite(numericAmount) &&
      numericAmount >= 1,
    retry: false,
  });
}

export function useBuy(betId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { outcome_id: string; amount: string }) =>
      tradingApi.buy(betId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["bet", betId] });
      void queryClient.invalidateQueries({
        queryKey: ["positions", betId],
      });
      void queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useMyPositions(betId: string) {
  return useQuery({
    queryKey: ["positions", betId],
    queryFn: () => tradingApi.listMyPositions(betId),
    enabled: Boolean(betId),
  });
}

export function useLmsrPrice(betId: string, enabled = true) {
  return useQuery({
    queryKey: ["lmsr-price", betId],
    queryFn: () => tradingApi.getLmsrPrice(betId),
    enabled: Boolean(betId) && enabled,
    refetchInterval: 3_000,
  });
}

export function useLmsrQuote(
  betId: string,
  side: TradeSide,
  shares: string,
  enabled = true,
) {
  const [debouncedShares, setDebouncedShares] = useState(shares);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedShares(shares), 250);
    return () => window.clearTimeout(timeout);
  }, [shares]);
  const numericShares = Number(debouncedShares);
  return useQuery({
    queryKey: ["lmsr-quote", betId, side, debouncedShares],
    queryFn: () =>
      tradingApi.quoteLmsrTrade(betId, {
        side,
        shares: debouncedShares,
      }),
    enabled:
      enabled &&
      Boolean(betId) &&
      Number.isFinite(numericShares) &&
      numericShares !== 0,
    retry: false,
  });
}

export function useLmsrTrade(betId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { side: TradeSide; shares: string }) =>
      tradingApi.executeLmsrTrade(betId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["bet", betId] });
      void queryClient.invalidateQueries({ queryKey: ["lmsr-price", betId] });
      void queryClient.invalidateQueries({ queryKey: ["positions", betId] });
      void queryClient.invalidateQueries({ queryKey: ["trades", betId] });
      void queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useTrades(betId: string) {
  return useQuery({
    queryKey: ["trades", betId],
    queryFn: () => tradingApi.listTrades(betId),
    enabled: Boolean(betId),
  });
}
