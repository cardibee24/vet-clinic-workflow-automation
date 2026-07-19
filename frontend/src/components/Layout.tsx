import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { state, logout } = useAuth();
  const user = state.status === "signed-in" ? state.user : null;

  return (
    <>
      <nav className="app-nav">
        <NavLink to="/dashboard" className="brand">
          <span className="brand-mark">🐾</span> VetFlow
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : undefined)}>
          Dashboard
        </NavLink>
        <NavLink to="/owners" className={({ isActive }) => (isActive ? "active" : undefined)}>
          Owners
        </NavLink>
        <NavLink to="/appointments" className={({ isActive }) => (isActive ? "active" : undefined)}>
          Appointments
        </NavLink>
        <NavLink to="/invoices" className={({ isActive }) => (isActive ? "active" : undefined)}>
          Invoices
        </NavLink>
        <NavLink to="/queue" className={({ isActive }) => (isActive ? "active" : undefined)}>
          Queue
        </NavLink>
        <span className="spacer" />
        {user && <span className="muted">{user.full_name}</span>}
        <button type="button" className="secondary" onClick={logout}>
          Log out
        </button>
      </nav>
      <main className="page">
        <Outlet />
      </main>
    </>
  );
}
