import { FormEvent, useState } from "react";

import { useAuth } from "../store/auth";

export function AuthPage() {
  const { login, register, error, busy } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (mode === "login") void login(email, password);
    else void register(email, username, password);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="logo">
          Drift<span>board</span>
        </h1>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </label>
          {mode === "register" && (
            <label>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={2}
                pattern="[a-zA-Z0-9_.\-]+"
                title="Letters, numbers, dots, dashes and underscores"
              />
            </label>
          )}
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={mode === "register" ? 8 : undefined}
            />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button className="btn primary" disabled={busy}>
            {busy ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <button
          className="btn ghost"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
