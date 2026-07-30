export type BetVisibility = "group" | "public";
export type BetStatus = "open" | "closed" | "resolved" | "cancelled";
export type LeaderboardWindow = "weekly" | "biweekly" | "monthly" | "all_time";

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
  balance: string;
}

export interface Group {
  id: string;
  name: string;
  description: string | null;
  invite_code: string | null;
  created_by: string;
  created_at: string;
  role: "member" | "admin";
  membership_status: "active" | "removed";
  pending_settlement: boolean;
}

export interface GroupMember {
  user_id: string;
  role: "member" | "admin";
  status: "active" | "removed";
  joined_at: string;
  removed_at: string | null;
}

export interface Outcome {
  id: string;
  label: string;
  display_order: number;
  pool_shares: string;
  price: string;
}

export interface Bet {
  id: string;
  group_id: string | null;
  created_by: string;
  question: string;
  description: string | null;
  visibility: BetVisibility;
  status: BetStatus;
  end_time: string;
  resolved_outcome_id: string | null;
  resolved_at: string | null;
  created_at: string;
  outcomes: Outcome[];
}

export interface Position {
  outcome_id: string;
  shares: string;
  points_spent: string;
}

export interface BuyPreview {
  outcome_id: string;
  amount: string;
  shares_out: string;
  price_yes_after: string;
  price_no_after: string;
}

export interface TradeResult extends BuyPreview {
  remaining_balance: string;
  position_shares: string;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  display_name: string;
  net_profit_loss: string;
}

export interface Leaderboard {
  scope: string;
  window: LeaderboardWindow;
  entries: LeaderboardEntry[];
}

export interface ResolutionEvent {
  id: string;
  outcome_id: string;
  resolved_by: string;
  is_correction: boolean;
  created_at: string;
}

export interface BetEditEvent {
  id: string;
  edited_by: string;
  edit_type: string;
  old_value: string;
  new_value: string;
  created_at: string;
}

export interface CreateBetInput {
  question: string;
  description?: string;
  end_time: string;
  outcome_labels: [string, string];
  visible_to_user_ids?: string[];
}
