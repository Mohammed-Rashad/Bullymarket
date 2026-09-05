"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import {
  useForgotPassword,
  useResetPassword,
} from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api-client";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const forgot = useForgotPassword();
  const reset = useResetPassword();
  const [email, setEmail] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!codeSent) {
      await forgot.mutateAsync({ email });
      setCodeSent(true);
      return;
    }
    await reset.mutateAsync({ email, code, new_password: password });
    router.push("/groups");
  }

  return (
    <main className="auth-page">
      <section className="auth-art">
        <Link className="brand" href="/">
          <Image alt="" className="brand-logo" height={44} priority src="/logo.png" width={43} />
          <strong>BullyMarket</strong>
        </Link>
        <h1>Lose the password. Keep the receipts.</h1>
      </section>
      <section className="auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <span className="eyebrow">Account recovery</span>
          <h2>{codeSent ? "Set a new password" : "Reset password"}</h2>
          <p>
            {codeSent
              ? `If an account exists, a six-digit code was sent to ${email}.`
              : "We’ll email you a short-lived verification code."}
          </p>
          <div className="form-stack">
            <div className="field">
              <label htmlFor="email">Email</label>
              <Input
                autoComplete="email"
                disabled={codeSent}
                id="email"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </div>
            {codeSent ? (
              <>
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
                <div className="field">
                  <label htmlFor="new-password">New password</label>
                  <Input
                    autoComplete="new-password"
                    id="new-password"
                    minLength={8}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    type="password"
                    value={password}
                  />
                </div>
              </>
            ) : null}
            {forgot.error || reset.error ? (
              <ErrorNotice message={errorMessage(forgot.error ?? reset.error)} />
            ) : null}
            <Button disabled={forgot.isPending || reset.isPending} type="submit">
              {codeSent
                ? reset.isPending
                  ? "Resetting…"
                  : "Reset password"
                : forgot.isPending
                  ? "Sending…"
                  : "Send reset code"}
            </Button>
          </div>
          <p style={{ margin: "20px 0 0", textAlign: "center" }}>
            Remembered it? <Link href="/login">Sign in</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
