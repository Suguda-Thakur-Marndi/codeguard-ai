import React from "react";

interface StatusBadgeProps {
  status?: string | null;
  type?: "job" | "pr" | "finding";
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = "job" }) => {
  if (!status) {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-outline">
        No Review
      </span>
    );
  }

  const s = status.toUpperCase();

  if (type === "pr") {
    if (s === "OPEN") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-tertiary-container text-on-tertiary-container font-semibold">
          <span className="w-1.5 h-1.5 rounded-full bg-tertiary-fixed-dim" />
          OPEN
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-highest text-on-surface-variant font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-outline" />
        {s}
      </span>
    );
  }

  if (type === "finding") {
    if (s === "CRITICAL") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-error-container text-on-error-container font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-error" />
          CRITICAL
        </span>
      );
    }
    if (s === "HIGH") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-highest text-surface-tint font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-surface-tint" />
          HIGH
        </span>
      );
    }
    if (s === "MEDIUM") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-amber-400 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          MEDIUM
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-on-surface-variant font-medium">
        {s}
      </span>
    );
  }

  switch (s) {
    case "COMPLETED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-tertiary-container text-on-tertiary-container font-semibold">
          <span className="material-symbols-outlined text-[12px]">check_circle</span>
          Auto-Verified Pass
        </span>
      );
    case "RUNNING":
    case "ANALYZING":
    case "PREPARING":
    case "COMPREHENDING":
    case "VALIDATING":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-highest text-secondary font-semibold">
          <span className="material-symbols-outlined text-[12px] animate-spin">refresh</span>
          Review in Progress
        </span>
      );
    case "PENDING":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-on-surface-variant">
          <span className="material-symbols-outlined text-[12px]">schedule</span>
          Awaiting Review
        </span>
      );
    case "FAILED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-error-container text-on-error-container font-semibold">
          <span className="material-symbols-outlined text-[12px]">block</span>
          Blocked / Failed
        </span>
      );
    case "PARTIAL":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-amber-400 font-semibold">
          <span className="material-symbols-outlined text-[12px]">warning</span>
          Partial Gate
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-on-surface">
          {status}
        </span>
      );
  }
};
