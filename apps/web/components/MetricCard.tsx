import React from "react";

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  variant?: "default" | "success" | "warning" | "danger";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  variant = "default",
}) => {
  let valueColor = "text-slate-100";
  if (variant === "success") valueColor = "text-emerald-400";
  if (variant === "warning") valueColor = "text-amber-400";
  if (variant === "danger") valueColor = "text-rose-400";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
      <div className="mt-2 flex items-baseline justify-between">
        <p className={`text-2xl font-bold font-mono ${valueColor}`}>{value}</p>
      </div>
      {subtext && <p className="mt-1 text-xs text-slate-500">{subtext}</p>}
    </div>
  );
};
