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
import { IndiaFlag, GlobeIcon } from "../ui/Icons";

export default function GdpPanel({ data, loading, error, onRetry }) {
  // Transform series into Recharts row format: [{ period: '2021', india: 8.7, world: 6.3 }, ...]
  const chartData = React.useMemo(() => {
    if (!data?.series) return [];
    const indiaSeries = data.series.find((s) => s.series_key === "india")?.data || [];
    const worldSeries = data.series.find((s) => s.series_key === "world")?.data || [];

    const periodMap = new Map();

    indiaSeries.forEach((pt) => {
      periodMap.set(pt.period, { period: pt.period, india: pt.value, world: null });
    });

    worldSeries.forEach((pt) => {
      const existing = periodMap.get(pt.period) || { period: pt.period, india: null };
      existing.world = pt.value;
      periodMap.set(pt.period, existing);
    });

    // Take last 5 years to match Figma layout (2021 to 2025)
    return Array.from(periodMap.values())
      .sort((a, b) => a.period.localeCompare(b.period))
      .slice(-5);
  }, [data]);

  // Extract metrics from summary
  const indiaSummary = data?.summary?.find((s) => s.key === "india_latest");
  const worldSummary = data?.summary?.find((s) => s.key === "world_latest");

  const metrics = [
    {
      icon: <IndiaFlag size={24} />,
      label: "India",
      value: indiaSummary?.value !== undefined && indiaSummary?.value !== null ? Number(indiaSummary.value).toFixed(2) : "—",
      unit: "%",
      change: indiaSummary?.change !== undefined && indiaSummary?.change !== null ? Number(indiaSummary.change).toFixed(2) : null,
      changeUnit: "pp",
      isIncrease: indiaSummary?.is_increase ?? true,
    },
    {
      icon: <GlobeIcon size={24} />,
      label: "World",
      value: worldSummary?.value !== undefined && worldSummary?.value !== null ? Number(worldSummary.value).toFixed(2) : "—",
      unit: "%",
      change: worldSummary?.change !== undefined && worldSummary?.change !== null ? Number(worldSummary.change).toFixed(2) : null,
      changeUnit: "pp",
      isIncrease: worldSummary?.is_increase ?? true,
    },
  ];

  return (
    <IndicatorCard
      title="GDP Growth - India vs World"
      subtitle="(YOY%)"
      source={data?.source || "World Bank API"}
      sourceUrl={data?.source_url || "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG"}
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
          <span className="chip-indicator"></span> India
        </span>
        <span className="legend-chip amber">
          <span className="chip-indicator"></span> World
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          margin={{ top: 25, right: 10, left: -20, bottom: 0 }}
          barCategoryGap="25%"
          barGap={6}
        >
          <defs>
            <linearGradient id="gdpIndiaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
            <linearGradient id="gdpWorldGrad" x1="0" y1="0" x2="0" y2="1">
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
            domain={[0, (dataMax) => Math.max(10, Math.ceil(dataMax + 2))]}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip unit="%" />} />
          <Bar
            dataKey="india"
            name="India"
            fill="url(#gdpIndiaGrad)"
            radius={[4, 4, 0, 0]}
            label={{ position: "top", fill: "#94a3b8", fontSize: 10, formatter: (v) => (v ? `${v}%` : "") }}
          />
          <Bar
            dataKey="world"
            name="World"
            fill="url(#gdpWorldGrad)"
            radius={[4, 4, 0, 0]}
            label={{ position: "top", fill: "#94a3b8", fontSize: 10, formatter: (v) => (v ? `${v}%` : "") }}
          />
        </BarChart>
      </ResponsiveContainer>
    </IndicatorCard>
  );
}
