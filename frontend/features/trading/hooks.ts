"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import * as tradingApi from "./api";

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

