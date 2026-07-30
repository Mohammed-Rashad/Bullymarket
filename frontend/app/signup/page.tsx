"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import { useSignup } from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api-client";

export default function SignupPage() {
  const router = useRouter();
  const signup = useSignup();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await signup.mutateAsync({
      email,
      display_name: displayName,
      password,
    });
    router.push("/groups");
  }

  return (
    <main className="auth-page">
      <section className="auth-art">
        <Link className="brand" href="/">
          <span className="brand-mark">B</span>
          <strong>BullyMarket</strong>
        </Link>
        <h1>Your friends talk big. Give the claims a price.</h1>
      </section>
      <section className="auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <span className="eyebrow">Points only, pride included</span>
          <h2>Create account</h2>
          <p>Start with 1,000 points and make the first market.</p>
          <div className="form-stack">
            <div className="field">
              <label htmlFor="name">Display name</label>
              <Input
                id="name"
                maxLength={80}
                onChange={(event) => setDisplayName(event.target.value)}
                required
                value={displayName}
              />
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <Input
                autoComplete="email"
                id="email"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <Input
                autoComplete="new-password"
                id="password"
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </div>
            {signup.error ? (
              <ErrorNotice message={errorMessage(signup.error)} />
            ) : null}
            <Button disabled={signup.isPending} type="submit">
              {signup.isPending ? "Creating account…" : "Create account"}
            </Button>
          </div>
          <p style={{ margin: "20px 0 0", textAlign: "center" }}>
            Already playing? <Link href="/login">Sign in</Link>
          </p>
        </form>
      </section>
    </main>
  );
}

