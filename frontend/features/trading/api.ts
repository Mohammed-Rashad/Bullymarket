import { apiFetch } from "@/lib/api-client";
import type {
  BuyPreview,
  Position,
  TradeResult,
} from "@/lib/types";

export function previewBuy(
  betId: string,
  input: { outcome_id: string; amount: string },
) {
  return apiFetch<BuyPreview>(`/bets/${betId}/preview-buy`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function buy(
  betId: string,
  input: { outcome_id: string; amount: string },
) {
  return apiFetch<TradeResult>(`/bets/${betId}/buy`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listMyPositions(betId: string) {
  return apiFetch<Position[]>(`/bets/${betId}/positions/me`);
}

