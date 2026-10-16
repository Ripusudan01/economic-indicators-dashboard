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
import { TruckGraphic, ReceiptGraphic } from "../ui/Icons";

export default function GstPanel({ data, loading, error, onRetry }) {
  const chartData = React.useMemo(() => {
    if (!data?.series) return [];
    const totalSeries = data.series.find((s) => s.series_key === "total")?.data || [];
    return totalSeries.slice(-5).map((pt) => {
      // Annual total divided by 12 is an average, not an actual monthly trend.
      const monthlyRate = pt.value !== null && pt.value !== undefined ? Number((pt.value / 12).toFixed(2)) : null;
      return {
        period: pt.period, // FY21, FY22, FY23, FY24, FY25
        collection: pt.value,
        trend: monthlyRate,
      };
    });
  }, [data]);

  const totalSummary = data?.summary?.find((s) => s.key === "gst_collections_latest");
  const avgSummary = data?.summary?.find((s) => s.key === "monthly_average");

  const metrics = [
    {
      label: "GST Collections",
      value: totalSummary?.value !== undefined ? `₹${Number(totalSummary.value).toFixed(2)} L Cr` : "—",
      change: totalSummary?.change !== undefined ? Number(totalSummary.change).toFixed(2) : null,
      changeUnit: "%",
      isIncrease: totalSummary?.is_increase ?? true,
      graphic: <TruckGraphic size={48} />,
    },
    {
      label: "Monthly Average",
      value: avgSummary?.value !== undefined ? `₹${Number(avgSummary.value).toFixed(2)} L Cr` : "—",
      change: avgSummary?.change !== undefined ? Number(avgSummary.change).toFixed(2) : null,
      changeUnit: "pp",
      isIncrease: true,
      graphic: <ReceiptGraphic size={48} />,
    },
  ];

  return (
    <IndicatorCard
      title="GST Tax Collection"
      subtitle="(YOY%)"
      source={data?.source || "Ministry of Finance / RBI DBIE"}
      sourceUrl={data?.source_url || "https://pib.gov.in"}
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
          <span className="chip-indicator"></span> Annual Collection
        </span>
        <span className="legend-chip gold">
          <span className="chip-indicator line"></span> Annual Monthly Average
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart
          data={chartData}
          margin={{ top: 25, right: 10, left: -20, bottom: 0 }}
          barCategoryGap="30%"
        >
          <defs>
            <linearGradient id="gstBlueGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
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
            tickFormatter={(v) => `${v}`}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip unit="" units={{ collection: " L Cr", trend: " L Cr/mo" }} />} />
          <Bar
            dataKey="collection"
            name="Collections"
            fill="url(#gstBlueGrad)"
            radius={[4, 4, 0, 0]}
            label={{ position: "top", fill: "#94a3b8", fontSize: 10 }}
          />
          <Line
            type="monotone"
            dataKey="trend"
            name="Annual Monthly Average"
            stroke="#fbbf24"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#fbbf24", stroke: "#ffffff", strokeWidth: 1.5 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </IndicatorCard>
  );
}
