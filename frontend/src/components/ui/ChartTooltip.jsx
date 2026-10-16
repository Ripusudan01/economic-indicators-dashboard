import React from "react";

export default function ChartTooltip({ active, payload, label, unit = "", units = {} }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="custom-tooltip">
      <p className="tooltip-title">{label}</p>
      {payload.some((entry) => entry.payload?.classification === "projection") && (
        <p className="tooltip-item">IMF projection</p>
      )}
      {payload.map((entry, index) => (
        <p key={`${entry.dataKey}-${index}`} style={{ color: entry.fill || entry.color }} className="tooltip-item">
          <span className="tooltip-bullet">■</span> {entry.name}: {" "}
          <strong>{entry.value !== null && entry.value !== undefined ? `${entry.value}${units[entry.dataKey] ?? unit}` : "—"}</strong>
        </p>
      ))}
    </div>
  );
}
