"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { NotificationPreferences } from "@/lib/types";
import * as notificationsApi from "./api";

export function useNotifications(page: number, enabled = true) {
  return useQuery({
    queryKey: ["notifications", page],
    queryFn: () => notificationsApi.listNotifications(page),
    enabled,
    refetchInterval: 15_000,
  });
}

export function useUnreadNotifications(enabled = true) {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () =>
      notificationsApi.listNotifications(1, {
        unreadOnly: true,
        pageSize: 1,
      }),
    enabled,
    refetchInterval: 15_000,
  });
}

function useNotificationMutation<TInput, TResult>(
  mutationFn: (input: TInput) => Promise<TResult>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkNotificationRead() {
  return useNotificationMutation((notificationId: string) =>
    notificationsApi.markRead(notificationId),
  );
}

export function useMarkAllNotificationsRead() {
  return useNotificationMutation(() => notificationsApi.markAllRead());
}

export function useNotificationPreferences(enabled = true) {
  return useQuery({
    queryKey: ["notification-preferences"],
    queryFn: notificationsApi.getPreferences,
    enabled,
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NotificationPreferences) =>
      notificationsApi.updatePreferences(input),
    onSuccess: (preferences) => {
      queryClient.setQueryData(["notification-preferences"], preferences);
    },
  });
}
