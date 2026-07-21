import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { OwnersPage } from "./pages/OwnersPage";
import { OwnerDetailPage } from "./pages/OwnerDetailPage";
import { PetDetailPage } from "./pages/PetDetailPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { AppointmentDetailPage } from "./pages/AppointmentDetailPage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { InvoiceDetailPage } from "./pages/InvoiceDetailPage";
import { InvoicePrintPage } from "./pages/InvoicePrintPage";
import { QueuePage } from "./pages/QueuePage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { CheckQueuePage } from "./pages/CheckQueuePage";
import { SelfCheckInPage } from "./pages/SelfCheckInPage";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/check-queue" element={<CheckQueuePage />} />
          <Route path="/check-queue/:appointmentId" element={<CheckQueuePage />} />
          <Route path="/self-check-in" element={<SelfCheckInPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="invoices/:invoiceId/print" element={<InvoicePrintPage />} />
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="owners" element={<OwnersPage />} />
              <Route path="owners/:ownerId" element={<OwnerDetailPage />} />
              <Route path="pets/:petId" element={<PetDetailPage />} />
              <Route path="appointments" element={<AppointmentsPage />} />
              <Route path="appointments/:appointmentId" element={<AppointmentDetailPage />} />
              <Route path="invoices" element={<InvoicesPage />} />
              <Route path="invoices/:invoiceId" element={<InvoiceDetailPage />} />
              <Route path="queue" element={<QueuePage />} />
              <Route path="knowledge" element={<KnowledgePage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
