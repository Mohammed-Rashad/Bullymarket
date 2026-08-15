import { apiFetch } from "@/lib/api-client";
import type {
  BuyPreview,
  LmsrPrice,
  LmsrQuote,
  LmsrTradeResult,
  Position,
  TradeAudit,
  TradeResult,
  TradeSide,
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

export function getLmsrPrice(betId: string) {
  return apiFetch<LmsrPrice>(`/markets/${betId}/price`);
}

export function quoteLmsrTrade(
  betId: string,
  input: { side: TradeSide; shares: string },
) {
  const params = new URLSearchParams(input);
  return apiFetch<LmsrQuote>(`/markets/${betId}/quote?${params.toString()}`);
}

export function executeLmsrTrade(
  betId: string,
  input: { side: TradeSide; shares: string },
) {
  return apiFetch<LmsrTradeResult>(`/markets/${betId}/trade`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listTrades(betId: string) {
  return apiFetch<TradeAudit[]>(`/markets/${betId}/trades`);
}
