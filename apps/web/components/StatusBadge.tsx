import React from "react";

interface StatusBadgeProps {
  status?: string | null;
  type?: "job" | "pr";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = "job" }) => {
  if (!status) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-400 border border-gray-700">
        No Review
      </span>
    );
  }

  const s = status.toUpperCase();

  if (type === "pr") {
    if (s === "OPEN") {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-400" />
          Open
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950/80 text-purple-400 border border-purple-800">
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-purple-400" />
        Closed
      </span>
    );
  }

  switch (s) {
    case "COMPLETED":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-700/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-400" />
          Completed
        </span>
      );
    case "RUNNING":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-950/60 text-blue-400 border border-blue-700/60 animate-pulse">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-blue-400" />
          Running
        </span>
      );
    case "PENDING":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/60 text-amber-400 border border-amber-700/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-400" />
          Pending
        </span>
      );
    case "PREPARING":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-950/60 text-cyan-400 border border-cyan-700/60 animate-pulse">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-cyan-400" />
          Preparing Code
        </span>
      );
    case "COMPREHENDING":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-950/60 text-indigo-400 border border-indigo-700/60 animate-pulse">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-indigo-400" />
          Comprehending PR
        </span>
      );
    case "ANALYZING":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-950/60 text-purple-400 border border-purple-700/60 animate-pulse">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-purple-400" />
          AI Specialists Analyzing
        </span>
      );
    case "VALIDATING":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-950/60 text-teal-400 border border-teal-700/60 animate-pulse">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-teal-400" />
          Validating Findings
        </span>
      );
    case "PARTIAL":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-600/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-400" />
          Partial Review
        </span>
      );
    case "FAILED":
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950/60 text-rose-400 border border-rose-700/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-rose-400" />
          Failed
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300 border border-gray-700">
          {status}
        </span>
      );
  }
};
