import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useDashboardTheme } from "../app/theme";
import { useSession } from "../app/session";

export function LoginPage() {
  const { user, login, isReady, requestPasswordReset } = useSession();
  const { theme, toggleTheme } = useDashboardTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRequestingReset, setIsRequestingReset] = useState(false);

  if (isReady && user) {
    const nextPath = user.force_password_change
      ? "/change-password"
      : ((location.state as { from?: string } | null)?.from ?? "/dashboard/kpi");
    return <Navigate to={nextPath} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    try {
      const sessionUser = await login(email, password);
      navigate(sessionUser.force_password_change ? "/change-password" : "/dashboard/kpi", { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleForgotPassword() {
    setError(null);
    setInfo(null);
    if (!email.trim()) {
      setError("Please enter your email address first.");
      return;
    }
    setIsRequestingReset(true);
    try {
      const status = await requestPasswordReset(email.trim());
      setInfo(status === "pending" ? "A reset request is already pending for this email." : "Request sent. An admin will set a temporary password.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not submit request.");
    } finally {
      setIsRequestingReset(false);
    }
  }

  return (
    <main className="page login-page">
      <section className="hero-card login-hero">
        <span className="badge">Login</span>
        <h1>Regional KPI Dashboard</h1>
        <p>Please sign in with your email address.</p>
      </section>

      <section className="section-card auth-card">
        <form className="stack-form" onSubmit={handleSubmit}>
          <div className="login-theme-toggle">
            <span className="theme-label">Theme</span>
            <button className="secondary-button" type="button" onClick={toggleTheme}>
              {theme === "light" ? "Switch to Dark" : "Switch to Light"}
            </button>
          </div>
          <label className="field-label">
            Email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
          </label>
          <label className="field-label">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <div className="meta-row">
            <button className="primary-button" type="submit" disabled={isSubmitting || !isReady}>
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
            <button className="secondary-button" type="button" onClick={handleForgotPassword} disabled={isRequestingReset}>
              {isRequestingReset ? "Sending..." : "Forgot password?"}
            </button>
          </div>
          {error ? <p className="status-panel status-error">{error}</p> : null}
          {info ? <p className="status-panel">{info}</p> : null}
          <p className="sidebar-copy">
            Check the keep-awake monitor on the{" "}
            <a href="https://k62b8n0t.status.cron-job.org/" target="_blank" rel="noreferrer">
              Status Page
            </a>
            .
          </p>
        </form>
      </section>
    </main>
  );
}
