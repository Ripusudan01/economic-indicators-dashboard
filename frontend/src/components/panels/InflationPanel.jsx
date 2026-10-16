import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import IndicatorCard from "../ui/IndicatorCard";
import ChartTooltip from "../ui/ChartTooltip";
import { CoinsGraphic, BankGraphic } from "../ui/Icons";

export default function InflationPanel({ data, loading, error, onRetry }) {
  const chartData = React.useMemo(() => {
    if (!data?.series) return [];
    const cpiSeries = data.series.find((s) => s.series_key === "india")?.data || [];
    const targetSeries = data.series.find((s) => s.series_key === "rbi_target")?.data || [];

    const periodMap = new Map();

    cpiSeries.forEach((pt) => {
      periodMap.set(pt.period, {
        period: pt.period,
        cpi: pt.value !== null ? Number(Number(pt.value).toFixed(2)) : null,
        target: 4.0,
      });
    });

    targetSeries.forEach((pt) => {
      const existing = periodMap.get(pt.period) || { period: pt.period, cpi: null };
      existing.target = pt.value ?? 4.0;
      periodMap.set(pt.period, existing);
    });

    return Array.from(periodMap.values())
      .sort((a, b) => a.period.localeCompare(b.period))
      .slice(-5);
  }, [data]);

  const cpiSummary = data?.summary?.find((s) => s.key === "inflation_rate");
  const targetSummary = data?.summary?.find((s) => s.key === "rbi_target");

  const metrics = [
    {
      label: "Inflation Rate",
      value: cpiSummary?.value !== undefined && cpiSummary?.value !== null ? Number(cpiSummary.value).toFixed(2) : "—",
      unit: "%",
      change: cpiSummary?.change !== undefined && cpiSummary?.change !== null ? Number(cpiSummary.change).toFixed(2) : null,
      changeUnit: "pp",
      isIncrease: cpiSummary?.is_increase ?? true,
      graphic: <CoinsGraphic size={48} />,
    },
    {
      label: "RBI Target",
      value: targetSummary?.value !== undefined ? `${targetSummary.value}` : "4.0",
      unit: "%",
      change: null,
      changeUnit: "pp",
      isIncrease: null,
      graphic: <BankGraphic size={48} />,
    },
  ];

  return (
    <IndicatorCard
      title="Inflation"
      subtitle="(IND)"
      source={data?.source || "World Bank / MOSPI"}
      sourceUrl={data?.source_url || "https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG"}
      asOf={data?.as_of}
      fetchedAt={data?.fetched_at}
      isStale={data?.is_stale}
      note={data?.note}
      loading={loading}
      error={error}
      onRetry={onRetry}
      metrics={metrics}
      hasData={Boolean(data?.series?.some((series) => series.data?.some((point) => point.value !== null)))}
    >
      <div className="chart-legend-row">
        <span className="legend-chip cyan">
          <span className="chip-indicator line"></span> CPI Inflation (India)
        </span>
        <span className="legend-chip red-dashed">
          <span className="chip-indicator line-dashed"></span> RBI Target (4% ± 2%)
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart
          data={chartData}
          margin={{ top: 25, right: 15, left: -20, bottom: 0 }}
        >
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
            domain={[0, 10]}
            ticks={[0, 2, 4, 6, 8, 10]}
            tickFormatter={(v) => `${v}%`}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip unit="%" />} />
          <ReferenceLine
            y={4}
            stroke="#f43f5e"
            strokeDasharray="4 4"
            strokeWidth={1.5}
            label={{ value: "RBI 4% Target", position: "insideTopRight", fill: "#f43f5e", fontSize: 10 }}
          />
          <Line
            type="monotone"
            dataKey="cpi"
            name="CPI Inflation"
            stroke="#38bdf8"
            strokeWidth={3}
            dot={{ r: 4, fill: "#38bdf8", stroke: "#ffffff", strokeWidth: 1.5 }}
            activeDot={{ r: 6, fill: "#38bdf8", stroke: "#ffffff", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </IndicatorCard>
  );
}
