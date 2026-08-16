import { apiFetch } from "@/lib/api-client";
import type {
  Notification,
  NotificationPreferences,
  PaginatedNotifications,
} from "@/lib/types";

export function listNotifications(
  page = 1,
  options: { unreadOnly?: boolean; pageSize?: number } = {},
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(options.pageSize ?? 20),
    unread_only: String(options.unreadOnly ?? false),
  });
  return apiFetch<PaginatedNotifications>(`/notifications?${params}`);
}

export function markRead(notificationId: string) {
  return apiFetch<Notification>(`/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
}

export function markAllRead() {
  return apiFetch<{ updated: number }>("/notifications/read-all", {
    method: "POST",
  });
}

export function getPreferences() {
  return apiFetch<NotificationPreferences>("/notifications/preferences");
}

export function updatePreferences(input: NotificationPreferences) {
  return apiFetch<NotificationPreferences>("/notifications/preferences", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
