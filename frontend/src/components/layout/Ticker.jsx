import React, { useState, useEffect } from "react";
import api from "../../api/client";

export default function Ticker() {
  const [tickerData, setTickerData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("loading");

  const fetchTicker = async () => {
    try {
      const response = await api.get("/ticker");
      if (response.data && response.data.items) {
        setTickerData(response.data.items);
        const statuses = response.data.items.map((item) => item.status);
        setStatus(statuses.includes("stale") ? "stale" : statuses.includes("delayed") ? "delayed" : "unavailable");
      }
    } catch {
      console.warn("Ticker request failed.");
      setStatus((current) => current === "loading" ? "unavailable" : "stale");
    } finally {
      setLoading(false);
    }
  };

  const statusLabel = loading && tickerData.length === 0
    ? "LOADING"
    : status === "fresh" ? "FRESH"
      : status === "delayed" ? "DELAYED"
        : status === "stale" ? "STALE" : "UNAVAILABLE";

  useEffect(() => {
    fetchTicker();
    // Poll every 30 seconds as specified in assignment
    const interval = setInterval(fetchTicker, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatNumber = (val) => {
    if (val === null || val === undefined) return "—";
    return Number(val).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  return (
    <div className="ticker-bar-container">
      <div className={`ticker-live-badge ticker-status-${status}`}>
        <span className="live-dot"></span>
        <span className="live-text">{statusLabel}</span>
      </div>

      <div className="ticker-marquee-wrapper">
        <div className="ticker-track">
          {/* Render twice for continuous infinite ticker flow */}
          {[...tickerData, ...tickerData].map((item, idx) => {
            const isUp = item.change_pct !== null && item.change_pct >= 0;
            const sign = item.change_pct > 0 ? "+" : "";

            return (
              <div key={`${item.symbol}-${idx}`} className="ticker-item">
                <span className="ticker-symbol" title={item.observation_date ? `Yahoo daily observation: ${item.observation_date}; backend fetched: ${item.fetched_at}` : `Yahoo observation date unavailable; backend fetched: ${item.fetched_at}`}>
                  {item.display_name}
                </span>
                <span className="ticker-value">{formatNumber(item.value)}</span>
                <span
                  className={`ticker-change ${
                    isUp ? "positive" : "negative"
                  }`}
                >
                  ({sign}
                  {item.change_pct !== null ? `${item.change_pct}%` : "—"})
                </span>
                <span className="ticker-divider">|</span>
              </div>
            );
          })}

          {tickerData.length === 0 && !loading && (
            <div className="ticker-item fallback">
              <span>{loading ? "Loading market data…" : "Market data unavailable"}</span>
            </div>
          )}
        </div>
      </div>

      {(status === "stale" || status === "delayed") && (
        <div className="ticker-stale-tag" title={status === "delayed" ? "Yahoo Finance daily bars can be delayed; this is not real-time data" : "The provider observation is old or has no usable observation date; the last quote is retained"}>
          {status === "delayed" ? "Yahoo delayed" : "Stale / date unknown"}
        </div>
      )}
    </div>
  );
}
