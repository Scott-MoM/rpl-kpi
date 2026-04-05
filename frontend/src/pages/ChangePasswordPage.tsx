import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "../app/session";

export function ChangePasswordPage() {
  const { user, changePassword } = useSession();
  const navigate = useNavigate();
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!temporaryPassword || !newPassword || !confirmPassword) {
      setError("Please complete all fields.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    setIsSubmitting(true);
    try {
      await changePassword(temporaryPassword, newPassword);
      navigate("/dashboard/kpi", { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Password update failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page">
      <section className="hero-card">
        <span className="badge">Change Password</span>
        <h1>Update your password</h1>
        <p>{user ? `Account: ${user.email}` : "Please set a new password to continue."}</p>
      </section>

      <section className="section-card auth-card">
        <form className="stack-form" onSubmit={handleSubmit}>
          <label className="field-label">
            Temporary Password
            <input type="password" value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} required />
          </label>
          <label className="field-label">
            New Password
            <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
          </label>
          <label className="field-label">
            Confirm New Password
            <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />
          </label>
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Updating..." : "Update Password"}
          </button>
          {error ? <p className="status-panel status-error">{error}</p> : null}
        </form>
      </section>
    </main>
  );
}
