import React from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import IndicatorCard from "../ui/IndicatorCard";
import ChartTooltip from "../ui/ChartTooltip";
import { ExportGraphic, ShipGraphic } from "../ui/Icons";

export default function TradePanel({ data, loading, error, onRetry }) {
  const chartData = React.useMemo(() => {
    if (!data?.series) return [];
    const exportsSeries = data.series.find((s) => s.series_key === "exports")?.data || [];
    const importsSeries = data.series.find((s) => s.series_key === "imports")?.data || [];
    const balanceSeries = data.series.find((s) => s.series_key === "trade_balance")?.data || [];

    const periodMap = new Map();

    importsSeries.forEach((pt) => {
      periodMap.set(pt.period, { period: pt.period, imports: pt.value, exports: null, balance: null });
    });

    exportsSeries.forEach((pt) => {
      const existing = periodMap.get(pt.period) || { period: pt.period, imports: null };
      existing.exports = pt.value;
      periodMap.set(pt.period, existing);
    });

    balanceSeries.forEach((pt) => {
      const existing = periodMap.get(pt.period) || { period: pt.period };
      existing.balance = pt.value;
      periodMap.set(pt.period, existing);
    });

    return Array.from(periodMap.values())
      .sort((a, b) => a.period.localeCompare(b.period))
      .slice(-5);
  }, [data]);

  const exportsSummary = data?.summary?.find((s) => s.key === "exports_latest");
  const importsSummary = data?.summary?.find((s) => s.key === "imports_latest");

  const metrics = [
    {
      label: "Exports",
      value: exportsSummary?.value !== undefined ? `$${Number(exportsSummary.value).toFixed(1)} B` : "—",
      change: exportsSummary?.change !== undefined ? Number(exportsSummary.change).toFixed(2) : null,
      changeUnit: "B",
      isIncrease: exportsSummary?.is_increase ?? true,
      graphic: <ExportGraphic size={48} />,
    },
    {
      label: "Imports",
      value: importsSummary?.value !== undefined ? `$${Number(importsSummary.value).toFixed(1)} B` : "—",
      change: importsSummary?.change !== undefined ? Number(importsSummary.change).toFixed(2) : null,
      changeUnit: "B",
      isIncrease: importsSummary?.is_increase ?? false,
      graphic: <ShipGraphic size={48} />,
    },
  ];

  return (
    <IndicatorCard
      title="Imports, Exports & Trade Balance"
      source={data?.source || "World Bank / RBI"}
      sourceUrl={data?.source_url || "https://data.worldbank.org/indicator/NE.EXP.GNFS.CD"}
      asOf={data?.as_of}
      fetchedAt={data?.fetched_at}
      isStale={data?.is_stale}
      note={data?.note}
      loading={loading}
      error={error}
      onRetry={onRetry}
      metrics={metrics}
    >
      <div className="chart-legend-row">
        <span className="legend-chip blue">
          <span className="chip-indicator"></span> Imports
        </span>
        <span className="legend-chip amber">
          <span className="chip-indicator"></span> Exports
        </span>
        <span className="legend-chip green">
          <span className="chip-indicator line"></span> Trade Balance
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart
          data={chartData}
          margin={{ top: 25, right: 10, left: -20, bottom: 0 }}
          barCategoryGap="25%"
          barGap={6}
        >
          <defs>
            <linearGradient id="tradeImportsGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
            <linearGradient id="tradeExportsGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#d97706" />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
          <XAxis
            dataKey="period"
            stroke="#94a3b8"
            fontSize={12}
            tickLine={false}
            axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          />
          <YAxis
            stroke="#94a3b8"
            fontSize={11}
            domain={[0, (dataMax) => Math.ceil(dataMax * 1.15)]}
            tickFormatter={(v) => `${v}B`}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip unit=" B" />} />
          <Bar
            dataKey="imports"
            name="Imports"
            fill="url(#tradeImportsGrad)"
            radius={[4, 4, 0, 0]}
            label={{ position: "top", fill: "#94a3b8", fontSize: 10 }}
          />
          <Bar
            dataKey="exports"
            name="Exports"
            fill="url(#tradeExportsGrad)"
            radius={[4, 4, 0, 0]}
            label={{ position: "top", fill: "#94a3b8", fontSize: 10 }}
          />
          <Line
            type="monotone"
            dataKey="balance"
            name="Trade Balance"
            stroke="#10b981"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#10b981", stroke: "#ffffff", strokeWidth: 1.5 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </IndicatorCard>
  );
}
