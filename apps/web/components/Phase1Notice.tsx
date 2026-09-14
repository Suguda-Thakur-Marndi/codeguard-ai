import React from "react";

export const Phase1Notice: React.FC = () => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 mb-6 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-emerald-900/40 border border-emerald-700/50 flex items-center justify-center text-emerald-400 font-bold text-xs">
            AI
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-200">
              CodeGuard AI Autonomous Review Platform Active
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic code intelligence, multi-agent AI review, adversarial verification, and zero-trust MCP governance are active.{" "}
              <span className="text-emerald-400/90 font-medium">
                End-to-end review automation enabled.
              </span>
            </p>
          </div>
        </div>
        <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
          v1.0.0-production
        </span>
      </div>
    </div>
  );
};
