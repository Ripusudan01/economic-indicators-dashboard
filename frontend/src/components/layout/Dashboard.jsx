import React, { lazy, Suspense, useState, useEffect, useCallback } from "react";
import api from "../../api/client";
import Header from "./Header";
import Ticker from "./Ticker";
import Icon from "../ui/Icon";

const GdpPanel = lazy(() => import("../panels/GdpPanel"));
const DebtPanel = lazy(() => import("../panels/DebtPanel"));
const TradePanel = lazy(() => import("../panels/TradePanel"));
const GstPanel = lazy(() => import("../panels/GstPanel"));
const InflationPanel = lazy(() => import("../panels/InflationPanel"));
const ExpenditurePanel = lazy(() => import("../panels/ExpenditurePanel"));

export default function Dashboard() {
  const [isFixedViewport, setIsFixedViewport] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [systemHealth, setSystemHealth] = useState(null);
  const [healthState, setHealthState] = useState("loading");

  // States for each of the 6 indicators
  const [gdp, setGdp] = useState({ data: null, loading: true, error: null });
  const [debt, setDebt] = useState({ data: null, loading: true, error: null });
  const [trade, setTrade] = useState({ data: null, loading: true, error: null });
  const [gst, setGst] = useState({ data: null, loading: true, error: null });
  const [inflation, setInflation] = useState({ data: null, loading: true, error: null });
  const [expenditure, setExpenditure] = useState({ data: null, loading: true, error: null });

  const fetchIndicator = useCallback(async (endpoint, setter) => {
    setter((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await api.get(endpoint);
      setter({ data: res.data, loading: false, error: null });
    } catch (err) {
      console.error(`Error fetching ${endpoint}:`, err);
      setter((prev) => ({
        ...prev,
        loading: false,
        error: err.response?.data?.detail || "Network request failed. Upstream unavailable.",
      }));
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // Check health
      setHealthState("loading");
      api.get("/health").then((res) => {
        setSystemHealth(res.data);
        setHealthState(res.data?.status === "ok" && res.data?.db === "ok" ? "healthy" : "unavailable");
      }).catch(() => {
        setSystemHealth(null);
        setHealthState("unavailable");
      });

      // Concurrent fetch for all 6 panels
      await Promise.allSettled([
        fetchIndicator("/indicators/gdp-growth", setGdp),
        fetchIndicator("/indicators/debt-gdp", setDebt),
        fetchIndicator("/indicators/trade", setTrade),
        fetchIndicator("/indicators/gst", setGst),
        fetchIndicator("/indicators/inflation", setInflation),
        fetchIndicator("/indicators/govt-expenditure", setExpenditure),
      ]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchIndicator]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return (
    <div className={`dashboard-wrapper ${isFixedViewport ? "viewport-fixed" : "viewport-fluid"}`}>
      {/* 1214x2159 Viewport Indicator Banner */}
      {/* {isFixedViewport && (
        <div className="viewport-ruler-bar">
          <span><Icon name="ruler" size={14} /> Required Evaluation Viewport: <strong>1214 × 2159 CSS pixels</strong> (Standard View Active)</span>
        </div>
      )} */}

      <div className="dashboard-container">
        {/* Header */}
        <Header
          onRefreshAll={fetchAll}
          isRefreshing={isRefreshing}
          isFixedViewport={isFixedViewport}
          setIsFixedViewport={setIsFixedViewport}
        />

        {/* Yahoo Finance market data; quote delay varies */}
        <Ticker />

        {/* 6 Indicators 2-Column Grid */}
        <Suspense fallback={<main className="indicators-grid" aria-busy="true"><div className="indicator-card skeleton-card">Loading indicator panels…</div></main>}>
        <main className="indicators-grid">
          <GdpPanel
            data={gdp.data}
            loading={gdp.loading}
            error={gdp.error}
            onRetry={() => fetchIndicator("/indicators/gdp-growth", setGdp)}
          />

          <DebtPanel
            data={debt.data}
            loading={debt.loading}
            error={debt.error}
            onRetry={() => fetchIndicator("/indicators/debt-gdp", setDebt)}
          />

          <TradePanel
            data={trade.data}
            loading={trade.loading}
            error={trade.error}
            onRetry={() => fetchIndicator("/indicators/trade", setTrade)}
          />

          <GstPanel
            data={gst.data}
            loading={gst.loading}
            error={gst.error}
            onRetry={() => fetchIndicator("/indicators/gst", setGst)}
          />

          <InflationPanel
            data={inflation.data}
            loading={inflation.loading}
            error={inflation.error}
            onRetry={() => fetchIndicator("/indicators/inflation", setInflation)}
          />

          <ExpenditurePanel
            data={expenditure.data}
            loading={expenditure.loading}
            error={expenditure.error}
            onRetry={() => fetchIndicator("/indicators/govt-expenditure", setExpenditure)}
          />
        </main>
        </Suspense>

        {/* Dashboard Footer & System Health */}
        <footer className="dashboard-footer">
          <div className="footer-left">
            <span className="footer-brand">Economic Indicators Dashboard</span>
          </div>

          <div className="footer-right">
            <div className="health-status-badge">
              <span className={`status-dot ${healthState === "healthy" ? "green" : "yellow"}`}></span>
              <span>
                API: {healthState === "loading" ? "checking" : healthState === "healthy" ? "healthy" : "unavailable"}
                {" • "}
                DB: {healthState === "loading" ? "checking" : systemHealth?.db === "ok" ? "healthy" : "unavailable"}
              </span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
