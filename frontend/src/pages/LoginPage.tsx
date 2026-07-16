import { useState, type FormEvent } from "react";
import { fetchCurrentUser, login, type CurrentUser } from "../api/auth";

type State =
  | { status: "logged-out" }
  | { status: "logging-in" }
  | { status: "logged-in"; user: CurrentUser }
  | { status: "error"; message: string };

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<State>({ status: "logged-out" });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setState({ status: "logging-in" });
    try {
      const token = await login(email, password);
      const user = await fetchCurrentUser(token.access_token);
      setState({ status: "logged-in", user });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Login failed",
      });
    }
  }

  if (state.status === "logged-in") {
    return (
      <section>
        <h2>Signed in</h2>
        <pre>{JSON.stringify(state.user, null, 2)}</pre>
        <button type="button" onClick={() => setState({ status: "logged-out" })}>
          Log out
        </button>
      </section>
    );
  }

  return (
    <section>
      <h2>Staff login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={state.status === "logging-in"}>
          {state.status === "logging-in" ? "Signing in..." : "Sign in"}
        </button>
      </form>
      {state.status === "error" && <p style={{ color: "red" }}>{state.message}</p>}
    </section>
  );
}
