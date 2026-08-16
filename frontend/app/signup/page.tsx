"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import { useSignup, useVerifySignup } from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api-client";

export default function SignupPage() {
  const router = useRouter();
  const signup = useSignup();
  const verifySignup = useVerifySignup();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [awaitingCode, setAwaitingCode] = useState(false);

  async function requestCode(event: FormEvent) {
    event.preventDefault();
    await signup.mutateAsync({
      email,
      display_name: displayName,
      password,
    });
    setAwaitingCode(true);
    setCode("");
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    await verifySignup.mutateAsync({ email, code });
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
        <form
          className="auth-card"
          onSubmit={awaitingCode ? verifyCode : requestCode}
        >
          <span className="eyebrow">Points only, pride included</span>
          <h2>{awaitingCode ? "Check your email" : "Create account"}</h2>
          <p>
            {awaitingCode
              ? `Enter the six-digit code sent to ${email}.`
              : "Start with 1,000 points and make the first market."}
          </p>
          <div className="form-stack">
            {awaitingCode ? (
              <div className="field">
                <label htmlFor="code">Verification code</label>
                <Input
                  autoComplete="one-time-code"
                  id="code"
                  inputMode="numeric"
                  maxLength={6}
                  minLength={6}
                  onChange={(event) =>
                    setCode(event.target.value.replace(/\D/g, ""))
                  }
                  pattern="[0-9]{6}"
                  required
                  value={code}
                />
              </div>
            ) : (
              <>
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
              </>
            )}
            {signup.error || verifySignup.error ? (
              <ErrorNotice
                message={errorMessage(signup.error ?? verifySignup.error)}
              />
            ) : null}
            <Button
              disabled={signup.isPending || verifySignup.isPending}
              type="submit"
            >
              {awaitingCode
                ? verifySignup.isPending
                  ? "Verifying…"
                  : "Verify and create account"
                : signup.isPending
                  ? "Sending code…"
                  : "Send verification code"}
            </Button>
            {awaitingCode ? (
              <button
                className="text-button"
                onClick={() => setAwaitingCode(false)}
                type="button"
              >
                Change account details
              </button>
            ) : null}
          </div>
          <p style={{ margin: "20px 0 0", textAlign: "center" }}>
            Already playing? <Link href="/login">Sign in</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
