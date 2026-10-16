import React, { lazy, Suspense } from "react";
import { AuthProvider } from "./auth/AuthContext";
import { useAuth } from "./auth/useAuth";
import LoginPage from "./components/auth/LoginPage";
import "./styles/theme.css";
import "./index.css";

const Dashboard = lazy(() => import("./components/layout/Dashboard"));

function AppContent() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="app-loading-screen">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading Economic Indicators Dashboard...</p>
      </div>
    );
  }

  return isAuthenticated ? (
    <Suspense fallback={<div className="app-loading-screen"><div className="loading-spinner"></div><p className="loading-text">Loading dashboard…</p></div>}>
      <Dashboard />
    </Suspense>
  ) : <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
