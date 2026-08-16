import { apiFetch } from "@/lib/api-client";
import type {
  Bet,
  BetListStatus,
  BetEditEvent,
  CreateBetInput,
  PaginatedBets,
  ResolutionEvent,
} from "@/lib/types";

export interface BetListParams {
  page: number;
  pageSize?: number;
  status: BetListStatus;
}

function listQuery({ page, pageSize = 6, status }: BetListParams) {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status !== "all") query.set("status", status);
  return query.toString();
}

export function listGroupBets(groupId: string, params: BetListParams) {
  return apiFetch<PaginatedBets>(
    `/groups/${groupId}/bets?${listQuery(params)}`,
  );
}

export function listPublicBets(params: BetListParams) {
  return apiFetch<PaginatedBets>(`/public-bets?${listQuery(params)}`);
}

export function getBet(betId: string) {
  return apiFetch<Bet>(`/bets/${betId}`);
}

export function createGroupBet(groupId: string, input: CreateBetInput) {
  return apiFetch<Bet>(`/groups/${groupId}/bets`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createPublicBet(input: CreateBetInput) {
  return apiFetch<Bet>("/public-bets", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function editEndTime(betId: string, end_time: string) {
  return apiFetch<Bet>(`/bets/${betId}/end-time`, {
    method: "PATCH",
    body: JSON.stringify({ end_time }),
  });
}

export function cancelBet(betId: string) {
  return apiFetch<{ refunded_users: number; refunded_points: string }>(
    `/bets/${betId}`,
    { method: "DELETE" },
  );
}

export function resolveBet(betId: string, outcome_id: string) {
  return apiFetch<{
    is_correction: boolean;
    total_payout: string;
    affected_users: number;
  }>(`/bets/${betId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ outcome_id }),
  });
}

export function listResolutionEvents(betId: string) {
  return apiFetch<ResolutionEvent[]>(`/bets/${betId}/resolution-events`);
}

export function listEditEvents(betId: string) {
  return apiFetch<BetEditEvent[]>(`/bets/${betId}/edit-events`);
}
