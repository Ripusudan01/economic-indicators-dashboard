import React from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Dashboard from "./components/layout/Dashboard";
import LoginPage from "./components/auth/LoginPage";
import "./styles/theme.css";
import "./index.css";

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

  return isAuthenticated ? <Dashboard /> : <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
