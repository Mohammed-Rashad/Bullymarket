"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { useAuthToken, useLogout, useMe } from "@/features/auth/hooks";
import { useUnreadNotifications } from "@/features/notifications/hooks";
import { AUTH_FAILURE_EVENT } from "@/lib/api-client";

const links = [
  { href: "/groups", label: "My groups" },
  { href: "/public", label: "Public markets" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/how-it-works", label: "How it works" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const token = useAuthToken();
  const logout = useLogout();
  const me = useMe();
  const unread = useUnreadNotifications(Boolean(token));
  const isAuthPage =
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/forgot-password";

  useEffect(() => {
    const handleAuthenticationFailure = () => {
      queryClient.clear();
      if (!isAuthPage) router.replace("/login");
    };
    window.addEventListener(AUTH_FAILURE_EVENT, handleAuthenticationFailure);
    return () =>
      window.removeEventListener(AUTH_FAILURE_EVENT, handleAuthenticationFailure);
  }, [isAuthPage, queryClient, router]);

  if (isAuthPage) return <>{children}</>;

  return (
    <div className="app-frame">
      <header className="topbar">
        <Link className="brand" href="/">
          <Image
            alt=""
            aria-hidden="true"
            className="brand-logo"
            height={44}
            priority
            src="/logo.png"
            width={43}
          />
          <span>
            <strong>BullyMarket</strong>
            <small>friendly stakes, sharp calls</small>
          </span>
        </Link>
        <nav className="nav-links" aria-label="Primary navigation">
          {links.map((link) => (
            <Link
              className={pathname.startsWith(link.href) ? "active" : ""}
              href={link.href}
              key={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="account-strip">
          {token ? (
            <>
              <Link
                aria-label={`${unread.data?.unread_count ?? 0} unread notifications`}
                className={`notification-link ${
                  pathname.startsWith("/notifications") ? "active" : ""
                }`}
                href="/notifications"
              >
                <span aria-hidden="true">●</span>
                <span>Alerts</span>
                {unread.data?.unread_count ? (
                  <strong>{Math.min(unread.data.unread_count, 99)}</strong>
                ) : null}
              </Link>
              <span className="balance-pill">
                <small>Balance</small>
                <strong>{Number(me.data?.balance ?? 0).toFixed(2)} pts</strong>
              </span>
              <button
                className="text-button"
                onClick={() => {
                  logout();
                  router.push("/login");
                }}
                type="button"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link className="button compact" href="/login">
              Sign in
            </Link>
          )}
        </div>
      </header>
      <main className="page-shell">{children}</main>
    </div>
  );
}
