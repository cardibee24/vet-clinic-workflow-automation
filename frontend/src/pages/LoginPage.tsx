import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { HealthCheckPage } from "./HealthCheckPage";

export function LoginPage() {
  const { state, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (state.status === "loading") {
    return <p style={{ padding: 24 }}>Loading...</p>;
  }
  if (state.status === "signed-in") {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <HealthCheckPage />
      <section style={{ maxWidth: 360, margin: "0 auto", padding: 24, textAlign: "left" }}>
        <h2>Staff login</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="field" style={{ marginTop: 12 }}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={submitting} style={{ marginTop: 16 }}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {error && <p className="error-text">{error}</p>}
      </section>
    </>
  );
}
