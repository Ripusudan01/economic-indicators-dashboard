import React, { useState, useEffect } from "react";
import api from "../../api/client";

export default function Ticker() {
  const [tickerData, setTickerData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isStale, setIsStale] = useState(false);

  const fetchTicker = async () => {
    try {
      const response = await api.get("/ticker");
      if (response.data && response.data.items) {
        setTickerData(response.data.items);
        setIsStale(response.data.items.some((item) => item.is_stale));
      }
    } catch (err) {
      console.warn("Ticker fetch failed:", err);
      setIsStale(true);
    } finally {
      setLoading(false);
    }
  };

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
      <div className={`ticker-live-badge ${isStale ? "ticker-stale" : ""}`}>
        <span className="live-dot"></span>
        <span className="live-text">{isStale ? "STALE" : "LIVE"}</span>
      </div>

      <div className="ticker-marquee-wrapper">
        <div className="ticker-track">
          {/* Render twice for continuous infinite ticker flow */}
          {[...tickerData, ...tickerData].map((item, idx) => {
            const isUp = item.change_pct !== null && item.change_pct >= 0;
            const sign = item.change_pct > 0 ? "+" : "";

            return (
              <div key={`${item.symbol}-${idx}`} className="ticker-item">
                <span className="ticker-symbol">{item.display_name}</span>
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
              <span>Market data temporarily unavailable (Market closed / Fallback source active)</span>
            </div>
          )}
        </div>
      </div>

      {isStale && (
        <div className="ticker-stale-tag" title="Data retained from last observation">
          Stale
        </div>
      )}
    </div>
  );
}
