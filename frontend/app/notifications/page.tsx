"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorNotice, Loading } from "@/components/ui";
import { useAuthToken } from "@/features/auth/hooks";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotificationPreferences,
  useNotifications,
  useUpdateNotificationPreferences,
} from "@/features/notifications/hooks";
import { errorMessage } from "@/lib/api-client";
import type { NotificationPreferences } from "@/lib/types";

const preferenceLabels: Array<[keyof NotificationPreferences, string]> = [
  ["email_enabled", "Email notifications"],
  ["bet_created_email", "New group bets"],
  ["bet_closed_email", "Bet closing and resolution reminders"],
  ["bet_resolved_email", "Resolved group bets"],
  ["bet_refunded_email", "Refunded group bets"],
];

export default function NotificationsPage() {
  const token = useAuthToken();
  const [page, setPage] = useState(1);
  const notifications = useNotifications(page, Boolean(token));
  const preferences = useNotificationPreferences(Boolean(token));
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const updatePreferences = useUpdateNotificationPreferences();

  function changePreference(
    key: keyof NotificationPreferences,
    checked: boolean,
  ) {
    if (!preferences.data) return;
    updatePreferences.mutate({ ...preferences.data, [key]: checked });
  }

  return (
    <div className="content-stack">
      <section className="page-title">
        <div>
          <span className="eyebrow">Your activity</span>
          <h1>Notifications</h1>
          <p>Updates are generated only for private group markets.</p>
        </div>
        {notifications.data?.unread_count ? (
          <Button
            className="secondary compact"
            disabled={markAllRead.isPending}
            onClick={() => markAllRead.mutate(undefined)}
            type="button"
          >
            Mark all read
          </Button>
        ) : null}
      </section>

      <div className="content-grid notification-layout">
        <section className="content-stack">
          {notifications.isLoading ? <Loading label="Loading notifications…" /> : null}
          {notifications.error ? (
            <ErrorNotice message={errorMessage(notifications.error)} />
          ) : null}
          {notifications.data && notifications.data.items.length === 0 ? (
            <EmptyState
              body="Group market updates will appear here. Public markets stay silent."
              title="Nothing new"
            />
          ) : null}
          {notifications.data?.items.map((notification) => (
            <Card
              className={`notification-card ${notification.read_at ? "" : "unread"}`}
              key={notification.id}
            >
              <div>
                <div className="notification-heading">
                  <strong>{notification.title}</strong>
                  {!notification.read_at ? <span className="unread-dot" /> : null}
                </div>
                <p>{notification.body}</p>
                <small>{new Date(notification.created_at).toLocaleString()}</small>
              </div>
              <div className="notification-actions">
                {notification.bet_id ? (
                  <Link className="button compact secondary" href={`/bets/${notification.bet_id}`}>
                    Open bet
                  </Link>
                ) : null}
                {!notification.read_at ? (
                  <button
                    className="text-button"
                    onClick={() => markRead.mutate(notification.id)}
                    type="button"
                  >
                    Mark read
                  </button>
                ) : null}
              </div>
            </Card>
          ))}
          {notifications.data && notifications.data.total_pages > 1 ? (
            <div className="pagination-controls">
              <Button
                className="secondary compact"
                disabled={page === 1}
                onClick={() => setPage((current) => current - 1)}
                type="button"
              >
                Previous
              </Button>
              <span>
                Page {page} of {notifications.data.total_pages}
              </span>
              <Button
                className="secondary compact"
                disabled={page === notifications.data.total_pages}
                onClick={() => setPage((current) => current + 1)}
                type="button"
              >
                Next
              </Button>
            </div>
          ) : null}
        </section>

        <Card className="notification-preferences">
          <span className="eyebrow">Delivery</span>
          <h2>Email preferences</h2>
          <p>In-app alerts remain on. Choose which group events also reach email.</p>
          {preferences.isLoading ? <Loading label="Loading preferences…" /> : null}
          {preferences.data ? (
            <div className="preference-list">
              {preferenceLabels.map(([key, label]) => (
                <label key={key}>
                  <span>{label}</span>
                  <input
                    checked={preferences.data[key]}
                    disabled={
                      updatePreferences.isPending ||
                      (key !== "email_enabled" && !preferences.data.email_enabled)
                    }
                    onChange={(event) => changePreference(key, event.target.checked)}
                    type="checkbox"
                  />
                </label>
              ))}
            </div>
          ) : null}
          {updatePreferences.error ? (
            <ErrorNotice message={errorMessage(updatePreferences.error)} />
          ) : null}
        </Card>
      </div>
    </div>
  );
}
