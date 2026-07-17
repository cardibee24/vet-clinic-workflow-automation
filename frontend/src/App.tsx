import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { OwnersPage } from "./pages/OwnersPage";
import { OwnerDetailPage } from "./pages/OwnerDetailPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { RemindersPage } from "./pages/RemindersPage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { InvoiceDetailPage } from "./pages/InvoiceDetailPage";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/owners" replace />} />
              <Route path="owners" element={<OwnersPage />} />
              <Route path="owners/:ownerId" element={<OwnerDetailPage />} />
              <Route path="appointments" element={<AppointmentsPage />} />
              <Route path="reminders" element={<RemindersPage />} />
              <Route path="invoices" element={<InvoicesPage />} />
              <Route path="invoices/:invoiceId" element={<InvoiceDetailPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
