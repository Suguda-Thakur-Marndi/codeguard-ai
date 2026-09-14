"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { ToolExecutionAudit } from "../../lib/types";

export default function AuditLogPage() {
  const [logs, setLogs] = useState<ToolExecutionAudit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<string>("ALL");
  const [selectedDecision, setSelectedDecision] = useState<string>("ALL");
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  async function loadAuditLogs() {
    try {
      setLoading(true);
      setError(null);
      const toolParam = selectedTool === "ALL" ? undefined : selectedTool;
      const res = await api.getAuditLogs(1, 100, undefined, undefined, toolParam);
      let items = res.items || [];
      if (selectedDecision !== "ALL") {
        items = items.filter((i) => i.authorization_decision === selectedDecision);
      }
      setLogs(items);
    } catch (err: any) {
      setError(err.message || "Failed to load audit trail");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAuditLogs();
  }, [selectedTool, selectedDecision]);

  function getDecisionBadge(decision: string) {
    switch (decision) {
      case "ALLOW":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">ALLOW</span>;
      case "DENY":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">DENY</span>;
      case "REQUIRE_APPROVAL":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">REQUIRE_APPROVAL</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300">{decision}</span>;
    }
  }

  function getRiskBadge(risk: string) {
    switch (risk) {
      case "READ_ONLY":
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">READ_ONLY</span>;
      case "LOW_RISK":
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">LOW_RISK</span>;
      case "CONSEQUENTIAL":
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">CONSEQUENTIAL</span>;
      case "HIGH_RISK":
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold">HIGH_RISK</span>;
      default:
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">{risk}</span>;
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">MCP Tool Execution Audit</h1>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Immutable & Append-Only
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Every agent tool call, policy authorization decision, and external execution is verifiably recorded.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={selectedTool}
            onChange={(e) => setSelectedTool(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Tools</option>
            <option value="submit_review">submit_review</option>
            <option value="run_validation">run_validation</option>
            <option value="get_pull_request">get_pull_request</option>
            <option value="get_pull_request_diff">get_pull_request_diff</option>
            <option value="get_review_findings">get_review_findings</option>
          </select>

          <select
            value={selectedDecision}
            onChange={(e) => setSelectedDecision(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Decisions</option>
            <option value="ALLOW">ALLOW</option>
            <option value="DENY">DENY</option>
            <option value="REQUIRE_APPROVAL">REQUIRE_APPROVAL</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="rounded-xl bg-slate-900/40 border border-slate-800 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm animate-pulse">
            Querying audit trail...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-rose-400 bg-rose-500/10 border border-rose-500/20 text-sm">
            {error}
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No audit records found matching the filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-mono text-slate-400 uppercase border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">Principal / Actor</th>
                  <th className="px-6 py-3">Tool</th>
                  <th className="px-6 py-3">Resource Target</th>
                  <th className="px-6 py-3">Risk</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {logs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  return (
                    <React.Fragment key={log.id}>
                      <tr className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-6 py-3 text-slate-400">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                        <td className="px-6 py-3 text-indigo-300 font-semibold truncate max-w-[140px]">
                          {log.principal_id}
                        </td>
                        <td className="px-6 py-3 text-white font-bold">{log.tool_name}</td>
                        <td className="px-6 py-3 text-slate-400 truncate max-w-[180px]">
                          <span className="text-[10px] text-slate-500">{log.resource_type}:</span>{" "}
                          {log.resource_id.slice(0, 12)}
                        </td>
                        <td className="px-6 py-3">{getRiskBadge(log.risk_level)}</td>
                        <td className="px-6 py-3">{getDecisionBadge(log.authorization_decision)}</td>
                        <td className="px-6 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] ${
                              log.execution_status === "SUCCESS"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : log.execution_status === "FAILED"
                                ? "bg-rose-500/10 text-rose-400"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {log.execution_status}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-right">
                          <button
                            onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                            className="text-xs text-indigo-400 hover:text-indigo-300 font-sans"
                          >
                            {isExpanded ? "Hide" : "Inspect"}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="bg-slate-950/80">
                          <td colSpan={8} className="px-6 py-4">
                            <div className="space-y-2 font-mono text-xs">
                              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                                <span>Audit ID: {log.id}</span>
                                <span>Approval ID: {log.approval_id || "None"}</span>
                                <span>Error Code: {log.error_code || "None"}</span>
                              </div>
                              <div className="text-slate-300 pt-1">Sanitized Metadata & Parameters:</div>
                              <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 overflow-x-auto text-[11px] text-slate-300">
                                {JSON.stringify(log.metadata_json, null, 2)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
