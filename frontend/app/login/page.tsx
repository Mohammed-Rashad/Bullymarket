"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import { useLogin } from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await login.mutateAsync({ email, password });
    router.push("/groups");
  }

  return (
    <main className="auth-page">
      <section className="auth-art">
        <Link className="brand" href="/">
          <Image alt="" className="brand-logo" height={44} priority src="/logo.png" width={43} />
          <strong>BullyMarket</strong>
        </Link>
        <h1>Back your take. Then live with the receipts.</h1>
      </section>
      <section className="auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <span className="eyebrow">Welcome back</span>
          <h2>Sign in</h2>
          <p>Your groups, open positions, and points are waiting.</p>
          <div className="form-stack">
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
              <div className="field-label-row">
                <label htmlFor="password">Password</label>
                <Link href="/forgot-password">Forgot password?</Link>
              </div>
              <Input
                autoComplete="current-password"
                id="password"
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </div>
            {login.error ? (
              <ErrorNotice message={errorMessage(login.error)} />
            ) : null}
            <Button disabled={login.isPending} type="submit">
              {login.isPending ? "Signing in…" : "Sign in"}
            </Button>
          </div>
          <p style={{ margin: "20px 0 0", textAlign: "center" }}>
            New here? <Link href="/signup">Create an account</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
