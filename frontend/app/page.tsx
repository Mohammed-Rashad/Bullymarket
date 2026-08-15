"use client";

import Link from "next/link";

import { useAuthToken, useMe } from "@/features/auth/hooks";

export default function HomePage() {
  const token = useAuthToken();
  const me = useMe();

  return (
    <section className="hero">
      <div className="hero-copy">
        <span className="eyebrow">The group chat has odds now</span>
        <h1>Put points behind your boldest calls.</h1>
        <p>
          Create a market for the debates your friends never settle. Prices move
          as the room picks a side, and every trade and final result stays auditable.
        </p>
        <div className="hero-actions">
          <Link className="button" href={token ? "/groups" : "/signup"}>
            {token ? "Open my groups" : "Start a market"}
          </Link>
          <Link className="button secondary" href="/public">
            Browse public calls
          </Link>
        </div>
      </div>
      <aside className="hero-aside">
        <div>
          <span className="eyebrow">Live signal</span>
          <h2>
            {me.data
              ? `Welcome back, ${me.data.display_name}.`
              : "A tiny prediction desk for your favorite people."}
          </h2>
          <p className="muted">
            No real money. No order-book drama. Just points, moving odds, and a
            permanent answer to “who called it?”
          </p>
        </div>
        <div className="signal-card" aria-label="Example market odds">
          <p className="muted">Will everyone arrive on time?</p>
          <div className="signal-row">
            <strong>Yes · 64%</strong>
            <div className="signal-bar">
              <span style={{ width: "64%" }} />
            </div>
          </div>
          <div className="signal-row">
            <strong>No · 36%</strong>
            <div className="signal-bar">
              <span style={{ width: "36%", background: "var(--coral)" }} />
            </div>
          </div>
        </div>
      </aside>
    </section>
  );
}
