import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchCurrentUser, login as loginRequest, type CurrentUser } from "../api/auth";

const TOKEN_STORAGE_KEY = "vetclinic.accessToken";

type AuthState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "signed-in"; token: string; user: CurrentUser };

interface AuthContextValue {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!storedToken) {
      setState({ status: "signed-out" });
      return;
    }
    fetchCurrentUser(storedToken)
      .then((user) => setState({ status: "signed-in", token: storedToken, user }))
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setState({ status: "signed-out" });
      });
  }, []);

  async function login(email: string, password: string) {
    const token = await loginRequest(email, password);
    const user = await fetchCurrentUser(token.access_token);
    localStorage.setItem(TOKEN_STORAGE_KEY, token.access_token);
    setState({ status: "signed-in", token: token.access_token, user });
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setState({ status: "signed-out" });
  }

  return <AuthContext.Provider value={{ state, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/** Convenience accessor for pages rendered under ProtectedRoute, where state is always signed-in. */
export function useToken(): string {
  const { state } = useAuth();
  return state.status === "signed-in" ? state.token : "";
}
