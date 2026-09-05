export type BetVisibility = "group" | "public";
export type BetStatus = "open" | "closed" | "resolved" | "cancelled";
export type BetListStatus = Exclude<BetStatus, "cancelled"> | "all";
export type PricingMethod = "cpmm" | "lmsr";
export type TradeSide = "yes" | "no";
export type LeaderboardWindow = "weekly" | "biweekly" | "monthly" | "all_time";
export type NotificationKind =
  | "bet_created"
  | "bet_closed"
  | "resolution_reminder"
  | "bet_resolved"
  | "bet_refunded";

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
  image_url: string | null;
  invite_code: string | null;
  created_by: string;
  created_at: string;
  role: "member" | "admin";
  membership_status: "active" | "removed";
  pending_settlement: boolean;
}

export interface GroupMember {
  user_id: string;
  display_name: string;
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
  image_url: string | null;
  visibility: BetVisibility;
  status: BetStatus;
  end_time: string;
  resolved_outcome_id: string | null;
  resolved_at: string | null;
  created_at: string;
  pricing_method: PricingMethod;
  b_liquidity: string | null;
  q_yes: string | null;
  q_no: string | null;
  house_reserve: string;
  house_cash_balance: string;
  house_profit_loss: string | null;
  outcomes: Outcome[];
}

export interface PaginatedBets {
  items: Bet[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface Notification {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string;
  group_id: string | null;
  bet_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface PaginatedNotifications {
  items: Notification[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  unread_count: number;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  bet_created_email: boolean;
  bet_closed_email: boolean;
  bet_resolved_email: boolean;
  bet_refunded_email: boolean;
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

export interface LmsrPrice {
  bet_id: string;
  price_yes: string;
  price_no: string;
  q_yes: string;
  q_no: string;
  b_liquidity: string;
}

export interface LmsrQuote extends LmsrPrice {
  side: TradeSide;
  delta_shares: string;
  cost: string;
  average_price: string;
  q_yes_after: string;
  q_no_after: string;
  price_yes_after: string;
  price_no_after: string;
}

export interface LmsrTradeResult extends LmsrQuote {
  trade_id: string;
  outcome_id: string;
  remaining_balance: string;
  position_shares: string;
  house_cash_flow: string;
}

export interface TradeAudit {
  id: string;
  bet_id: string;
  user_id: string;
  outcome_id: string;
  sequence: number;
  side: TradeSide;
  delta_shares: string;
  cost: string;
  house_cash_flow: string;
  q_yes_after: string;
  q_no_after: string;
  created_at: string;
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
  image_url?: string;
  end_time: string;
  outcome_labels: [string, string];
  visible_to_user_ids?: string[];
  b_liquidity?: string;
}
