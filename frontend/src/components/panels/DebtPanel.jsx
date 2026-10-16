import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import IndicatorCard from "../ui/IndicatorCard";
import ChartTooltip from "../ui/ChartTooltip";
import { IndiaFlag, USFlag } from "../ui/Icons";

export default function DebtPanel({ data, loading, error, onRetry }) {
  const chartData = React.useMemo(() => {
    if (!data?.series) return [];
    const indiaSeries = data.series.find((s) => s.series_key === "india")?.data || [];
    return indiaSeries.slice(-7).map((pt) => ({
      period: pt.period,
      value: pt.value,
      label: pt.value !== null && pt.value !== undefined ? `${pt.value}%` : null,
    }));
  }, [data]);

  const indiaSummary = data?.summary?.find((s) => s.key === "india_latest");
  const usSummary = data?.summary?.find((s) => s.key === "us_latest");

  const metrics = [
    {
      icon: <IndiaFlag size={24} />,
      label: "India (latest period)",
      value: indiaSummary?.value !== undefined && indiaSummary?.value !== null ? `${indiaSummary.value}` : "—",
      unit: "%",
      change: indiaSummary?.change !== undefined ? indiaSummary.change : null,
      changeUnit: "pp",
      isIncrease: indiaSummary?.is_increase,
    },
    {
      icon: <USFlag size={24} />,
      label: "Ind vs US",
      value: usSummary?.value !== undefined && usSummary?.value !== null ? `${usSummary.value}` : "—",
      unit: "%",
      change: usSummary?.change !== undefined ? usSummary.change : null,
      changeUnit: "pp",
      isIncrease: usSummary?.is_increase,
    },
  ];

  return (
    <IndicatorCard
      title="Debt to GDP Ratio"
      subtitle="(IND)"
      source={data?.source || "IMF WEO / RBI"}
      sourceUrl={data?.source_url || "https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP/IND"}
      asOf={data?.as_of}
      fetchedAt={data?.fetched_at}
      isStale={data?.is_stale}
      note={data?.note}
      loading={loading}
      error={error}
      onRetry={onRetry}
      metrics={metrics}
    >
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart
          data={chartData}
          margin={{ top: 25, right: 15, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="debtAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#0284c7" stopOpacity={0.02} />
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
            domain={[50, 100]}
            ticks={[50, 60, 70, 80, 90, 100]}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip unit="%" />} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#38bdf8"
            strokeWidth={2.5}
            fill="url(#debtAreaGrad)"
            dot={{ r: 4, fill: "#38bdf8" }}
            activeDot={{ r: 6, fill: "#38bdf8", stroke: "#ffffff", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </IndicatorCard>
  );
}
