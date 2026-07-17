import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function ProtectedRoute() {
  const { state } = useAuth();

  if (state.status === "loading") {
    return <p style={{ padding: 24 }}>Loading...</p>;
  }
  if (state.status === "signed-out") {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
