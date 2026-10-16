import React, { useState } from "react";
import { useAuth } from "../../auth/useAuth";
import Icon from "../ui/Icon";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
    } catch (err) {
      console.error("Login failed:", err);
      setError(
        err.response?.data?.detail || "Invalid credentials. Please verify username and password."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-glow-bg"></div>

      <div className="login-card">
        <div className="login-header">
          <div className="badge-tag">AUTHENTICATION GATEWAY</div>
          <h1 className="login-title">ECONOMIC INDICATOR</h1>
          <p className="login-subtitle">
            Sign in to view scheduled economic indicators and potentially delayed market quotes.
          </p>
        </div>

        {error && (
          <div className="login-error-banner">
            <Icon name="alert" size={18} className="error-icon" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          <button
            id="login-submit-btn"
            type="submit"
            className="login-submit-btn"
            disabled={loading}
          >
            {loading ? "Authenticating..." : "Sign In to Dashboard"}
          </button>
        </form>

        <div className="login-footer-info">
          <span>JWT Bearer Authentication • HS256 Token Rotation • SQLite Private DB</span>
        </div>
      </div>
    </div>
  );
}
