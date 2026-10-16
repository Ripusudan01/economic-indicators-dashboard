import React, { useState } from "react";
import Icon from "./Icon";

export default function IndicatorCard({
  title,
  subtitle,
  source,
  sourceUrl,
  asOf,
  isStale,
  note,
  loading,
  error,
  onRetry,
  metrics = [],
  children,
}) {
  const [showNote, setShowNote] = useState(false);

  // Loading Skeleton State
  if (loading) {
    return (
      <div className="indicator-card skeleton-card">
        <div className="card-header">
          <div className="skeleton-title skeleton"></div>
          <div className="skeleton-badge skeleton"></div>
        </div>
        <div className="metric-pills-row">
          <div className="metric-pill skeleton-pill skeleton"></div>
          <div className="metric-pill skeleton-pill skeleton"></div>
        </div>
        <div className="chart-skeleton skeleton"></div>
        <div className="card-footer">
          <div className="skeleton-footer skeleton"></div>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="indicator-card error-card">
        <div className="card-header">
          <h2 className="card-title">{title}</h2>
          <span className="status-badge error">Failed</span>
        </div>
        <div className="error-body">
          <Icon name="alert" size={32} className="error-icon" />
          <p className="error-message">Unable to load indicator data from server.</p>
          <p className="error-detail">{error}</p>
          <button className="retry-btn" onClick={onRetry}>
            <Icon name="refresh" size={14} /> Retry Request
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`indicator-card ${isStale ? "stale-card" : ""}`}>
      {/* Top Header */}
      <div className="card-header">
        <div className="title-group">
          <h2 className="card-title">
            {title}
            {subtitle && <span className="title-accent"> {subtitle}</span>}
          </h2>
        </div>

        <div className="header-meta">
          {isStale && (
            <span className="badge-stale" title="Upstream failed; showing last retained observation">
              <><Icon name="alert" size={12} /> STALE DATA</>
            </span>
          )}
          {onRetry && (
            <button
              className="card-refresh-icon"
              onClick={onRetry}
              title="Refresh this panel"
            >
              <Icon name="refresh" size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Top Metric Pills */}
      {metrics && metrics.length > 0 && (
        <div className="metric-pills-row">
          {metrics.map((m, idx) => (
            <div key={idx} className="metric-pill">
              <div className="pill-left">
                <div className="pill-header">
                  {m.icon && <span className="pill-icon">{m.icon}</span>}
                  <span className="pill-label">{m.label}</span>
                </div>
                <div className="pill-value">
                  {m.value !== null && m.value !== undefined
                    ? `${m.value}${m.unit || ""}`
                    : "—"}
                </div>
                {m.change !== null && m.change !== undefined && (
                  <div
                    className={`pill-change ${
                      m.isIncrease ? "positive" : "negative"
                    }`}
                  >
                    <span className="change-arrow">
                      {m.isIncrease ? "▲" : "▼"}
                    </span>
                    <span className="change-value">
                      {m.change > 0 ? `+${m.change}` : m.change}
                      {m.changeUnit || "pp"}
                    </span>
                  </div>
                )}
              </div>
              {m.graphic && <div className="pill-graphic">{m.graphic}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Chart Visualization Area */}
      <div className="chart-container">{children}</div>

      {/* Card Metadata Footer */}
      <div className="card-footer">
        <div className="footer-meta-left">
          <span className="source-label">
            Source:{" "}
            {sourceUrl ? (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="source-link"
              >
                {source || "Public API"}
              </a>
            ) : (
              source || "Official Source"
            )}
          </span>
          <span className="meta-separator">•</span>
          <span className="as-of-date">As of: {asOf || "Latest"}</span>
        </div>

        <div className="footer-meta-right">
          {note && (
            <button
              className="note-toggle-btn"
              onClick={() => setShowNote(!showNote)}
              title="View data methodology & limitations"
            >
              <><Icon name="info" size={13} /> {showNote ? "Hide Notes" : "Methodology"}</>
            </button>
          )}
        </div>
      </div>

      {/* Collapsible Methodology / Limitation Notes */}
      {showNote && note && (
        <div className="card-note-box">
          <p className="note-text">
            <strong>Methodology & Attribution:</strong> {note}
          </p>
        </div>
      )}
    </div>
  );
}
