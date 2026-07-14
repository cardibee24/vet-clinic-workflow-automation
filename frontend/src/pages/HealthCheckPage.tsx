import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "../api/health";

type State =
  | { status: "loading" }
  | { status: "success"; data: HealthResponse }
  | { status: "error"; message: string };

export function HealthCheckPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    fetchHealth()
      .then((data) => setState({ status: "success", data }))
      .catch((error: unknown) =>
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        }),
      );
  }, []);

  return (
    <main>
      <h1>Vet Clinic Workflow Automation</h1>
      <h2>Backend health check</h2>
      {state.status === "loading" && <p>Checking backend...</p>}
      {state.status === "success" && (
        <pre>{JSON.stringify(state.data, null, 2)}</pre>
      )}
      {state.status === "error" && (
        <p style={{ color: "red" }}>Error: {state.message}</p>
      )}
    </main>
  );
}
