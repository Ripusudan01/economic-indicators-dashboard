import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import IndicatorCard from "../ui/IndicatorCard";
import ChartTooltip from "../ui/ChartTooltip";
import { ExportGraphic, CapitalGraphic } from "../ui/Icons";

export default function ExpenditurePanel({ data, loading, error, onRetry }) {
  const chartData = React.useMemo(() => {
    if (!data?.series) return [];
    const totalSeries = data.series.find((s) => s.series_key === "total")?.data || [];
    const revenueSeries = data.series.find((s) => s.series_key === "revenue")?.data || [];
    const capitalSeries = data.series.find((s) => s.series_key === "capital")?.data || [];

    const periodMap = new Map();

    totalSeries.forEach((pt) => {
      periodMap.set(pt.period, { period: pt.period, total: pt.value, revenue: null, capital: null });
    });

    revenueSeries.forEach((pt) => {
      const existing = periodMap.get(pt.period) || { period: pt.period };
      existing.revenue = pt.value;
      periodMap.set(pt.period, existing);
    });

    capitalSeries.forEach((pt) => {
      const existing = periodMap.get(pt.period) || { period: pt.period };
      existing.capital = pt.value;
      periodMap.set(pt.period, existing);
    });

    return Array.from(periodMap.values())
      .sort((a, b) => a.period.localeCompare(b.period))
      .slice(-5);
  }, [data]);

  const totalSummary = data?.summary?.find((s) => s.key === "total_latest");
  const capitalSummary = data?.summary?.find((s) => s.key === "capital_latest");

  const metrics = [
    {
      label: "Total Expenditure",
      value: totalSummary?.value !== undefined && totalSummary?.value !== null ? `${Number(totalSummary.value).toFixed(2)}%` : "—",
      unit: "",
      change: totalSummary?.change !== undefined && totalSummary?.change !== null ? Number(totalSummary.change).toFixed(2) : null,
      changeUnit: "pp",
      isIncrease: totalSummary?.is_increase ?? false,
      graphic: <ExportGraphic size={48} />,
    },
    {
      label: "Capital Expenditure",
      value: capitalSummary?.value !== undefined && capitalSummary?.value !== null ? `${Number(capitalSummary.value).toFixed(2)}%` : "—",
      unit: "",
      change: capitalSummary?.change !== undefined && capitalSummary?.change !== null ? Number(capitalSummary.change).toFixed(2) : null,
      changeUnit: "pp",
      isIncrease: capitalSummary?.is_increase ?? true,
      graphic: <CapitalGraphic size={48} />,
    },
  ];

  return (
    <IndicatorCard
      title="Government Expenditure"
      source={data?.source || "World Bank API"}
      sourceUrl={data?.source_url || "https://data.worldbank.org/indicator/GC.XPN.TOTL.GD.ZS"}
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
        <span className="legend-chip blue">
          <span className="chip-indicator"></span> Revenue Expenditure
        </span>
        <span className="legend-chip amber">
          <span className="chip-indicator"></span> Capital Expenditure
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          margin={{ top: 25, right: 10, left: -20, bottom: 0 }}
          barCategoryGap="40%"
        >
          <defs>
            <linearGradient id="expRevGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
            <linearGradient id="expCapGrad" x1="0" y1="0" x2="0" y2="1">
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
            tickFormatter={(v) => `${v}%`}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip unit="% of GDP" />} />
          {/* Stacked Bars: Capital on bottom, Revenue on top */}
          <Bar
            dataKey="capital"
            name="Capital Expenditure"
            stackId="expenditure"
            fill="url(#expCapGrad)"
            radius={[0, 0, 0, 0]}
          />
          <Bar
            dataKey="revenue"
            name="Revenue Expenditure"
            stackId="expenditure"
            fill="url(#expRevGrad)"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </IndicatorCard>
  );
}
