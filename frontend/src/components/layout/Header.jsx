import React from "react";
import { useAuth } from "../../auth/AuthContext";
import Icon from "../ui/Icon";

export default function Header({ onRefreshAll, isRefreshing, isFixedViewport, setIsFixedViewport }) {
  const { user, logout } = useAuth();

  return (
    <header className="dashboard-header">
      {/* Background candlestick watermark effect */}
      <div className="header-bg-glow"></div>
      
      <div className="header-content">
        <div className="header-left">
          <div className="badge-tag">INDIA MACRO & MARKET PULSE</div>
          <h1 className="header-title">ECONOMIC INDICATOR</h1>
        </div>

        <div className="header-controls">
          {/* Viewport switch for evaluation requirement */}
          <button
            id="viewport-toggle-btn"
            className={`control-btn ${isFixedViewport ? "active" : ""}`}
            onClick={() => setIsFixedViewport(!isFixedViewport)}
            title="Toggle between fixed 1214x2159 px evaluation viewport and fluid responsive mode"
          >
            <Icon name="ruler" size={16} className="control-icon" />
            <span className="btn-text">
              {isFixedViewport ? "Target: 1214 × 2159 px" : "Responsive View"}
            </span>
          </button>

          {/* Refresh all data button */}
          <button
            id="refresh-all-btn"
            className="control-btn"
            onClick={onRefreshAll}
            disabled={isRefreshing}
            title="Fetch fresh data for all indicators"
          >
            <Icon name="refresh" size={16} className={`control-icon ${isRefreshing ? "spin" : ""}`} />
            <span className="btn-text">{isRefreshing ? "Refreshing..." : "Refresh"}</span>
          </button>

          {/* User profile & evaluation account */}
          <div className="user-profile-badge">
            <span className="user-avatar">{user?.username?.[0]?.toUpperCase() || "E"}</span>
            <div className="user-details">
              <span className="user-name">{user?.username || "Evaluator"}</span>
              <span className="user-role">{user?.role || "Test Account"}</span>
            </div>
            <button
              id="logout-btn"
              className="logout-btn"
              onClick={logout}
              title="Sign out of dashboard"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
