import React from "react";

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  icon?: string;
  badge?: string;
  variant?: "default" | "success" | "warning" | "danger" | "purple" | "yellow";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon,
  badge,
  variant = "default",
}) => {
  let valueColor = "text-primary";
  let iconColor = "text-primary-fixed";
  if (variant === "success") {
    valueColor = "text-tertiary-fixed-dim";
    iconColor = "text-tertiary-fixed-dim";
  } else if (variant === "warning") {
    valueColor = "text-surface-tint";
    iconColor = "text-surface-tint";
  } else if (variant === "danger") {
    valueColor = "text-error";
    iconColor = "text-error";
  } else if (variant === "purple") {
    valueColor = "text-secondary";
    iconColor = "text-secondary";
  } else if (variant === "yellow") {
    valueColor = "text-primary-fixed";
    iconColor = "text-primary-fixed";
  }

  return (
    <div className="bg-surface-container-lowest p-space-md rounded-lg border border-[#262930] shadow-sm flex flex-col justify-between group hover:bg-surface-container-low transition-colors">
      <div className="flex items-start justify-between mb-space-sm">
        <div className="flex items-center gap-2">
          {icon && (
            <span className={`material-symbols-outlined text-[18px] ${iconColor}`}>
              {icon}
            </span>
          )}
          <span className="font-label-mono text-label-mono text-on-surface-variant uppercase tracking-wider">
            {label}
          </span>
        </div>
        {badge && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-on-surface">
            {badge}
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-2 mb-1">
        <span className={`font-headline-xl text-headline-xl font-bold tracking-tight ${valueColor}`}>
          {value}
        </span>
      </div>
      {subtext && (
        <div className="font-label-mono text-kbd-shortcut text-outline pt-1">
          {subtext}
        </div>
      )}
    </div>
  );
};
