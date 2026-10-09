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
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut font-semibold bg-tertiary-container text-on-tertiary-container">
            ALLOW
          </span>
        );
      case "DENY":
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut font-semibold bg-error-container text-on-error-container">
            DENY
          </span>
        );
      case "REQUIRE_APPROVAL":
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut font-semibold bg-surface-container-highest text-primary-fixed border border-primary-fixed/40">
            REQUIRE_APPROVAL
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-on-surface">
            {decision}
          </span>
        );
    }
  }

  function getRiskBadge(risk: string) {
    switch (risk) {
      case "READ_ONLY":
        return <span className="font-label-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-outline">READ_ONLY</span>;
      case "LOW_RISK":
        return <span className="font-label-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-secondary">LOW_RISK</span>;
      case "CONSEQUENTIAL":
        return <span className="font-label-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-highest text-surface-tint font-bold">CONSEQUENTIAL</span>;
      case "HIGH_RISK":
        return <span className="font-label-mono text-[10px] px-2 py-0.5 rounded bg-error-container/40 text-error font-bold border border-error/30">HIGH_RISK</span>;
      default:
        return <span className="font-label-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-outline">{risk}</span>;
    }
  }

  return (
    <div className="flex flex-col w-full pb-16 space-y-space-md">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#262930] pb-space-md">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">
              Tool &amp; Action Execution Audit Trail
            </h1>
            <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-tertiary-container/20 text-tertiary-fixed-dim border border-[#262930]">
              Immutable &amp; Append-Only
            </span>
          </div>
          <p className="font-body-sm text-body-sm text-outline mt-1">
            Every agent tool call, policy authorization decision, and external execution is verifiably recorded.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={selectedTool}
            onChange={(e) => setSelectedTool(e.target.value)}
            className="bg-surface-container-low border border-[#262930] text-on-surface rounded px-3 py-1.5 font-label-mono text-kbd-shortcut outline-none"
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
            className="bg-surface-container-low border border-[#262930] text-on-surface rounded px-3 py-1.5 font-label-mono text-kbd-shortcut outline-none"
          >
            <option value="ALL">All Decisions</option>
            <option value="ALLOW">ALLOW</option>
            <option value="DENY">DENY</option>
            <option value="REQUIRE_APPROVAL">REQUIRE_APPROVAL</option>
          </select>

          <button
            type="button"
            onClick={loadAuditLogs}
            className="p-1.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface border border-[#262930]"
            title="Refresh logs"
          >
            <span className={`material-symbols-outlined text-[16px] ${loading ? "animate-spin" : ""}`}>sync</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-space-md rounded bg-error-container/20 border border-error text-error text-xs font-mono">
          {error}
        </div>
      )}

      {/* Main Table */}
      <div className="bg-surface-container-lowest rounded-lg border border-[#262930] overflow-hidden shadow-sm">
        <table className="w-full text-left font-body-sm text-body-sm border-collapse">
          <thead>
            <tr className="bg-surface-container text-on-surface-variant font-label-mono text-kbd-shortcut uppercase tracking-wider">
              <th className="py-2.5 px-4">Tool / Operation</th>
              <th className="py-2.5 px-3">Decision</th>
              <th className="py-2.5 px-3">Risk Level</th>
              <th className="py-2.5 px-3">Agent / Caller</th>
              <th className="py-2.5 px-3">Executed At</th>
              <th className="py-2.5 px-4 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#262930]/40">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-outline font-label-mono">
                  Loading immutable audit events...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <span className="material-symbols-outlined text-[32px] text-outline">history</span>
                    <p className="text-on-surface font-medium">No audit entries found</p>
                    <p className="text-outline text-xs">No tool executions matching active filter.</p>
                  </div>
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const isExpanded = expandedLogId === log.id;
                return (
                  <React.Fragment key={log.id}>
                    <tr className="hover:bg-surface-container transition-colors group">
                      <td className="py-3 px-4">
                        <div className="flex flex-col">
                          <span className="font-mono text-xs font-semibold text-primary">{log.tool_name}</span>
                          <span className="text-[10px] font-mono text-outline">ID: {log.id.slice(0, 10)}...</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">{getDecisionBadge(log.authorization_decision)}</td>
                      <td className="py-3 px-3">{getRiskBadge(log.risk_level)}</td>
                      <td className="py-3 px-3">
                        <span className="font-mono text-xs text-on-surface">
                          {log.metadata_json?.agent_name || log.principal_id || "CodeGuard Engine"}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-outline">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          className="font-label-mono text-kbd-shortcut px-2 py-1 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface transition-colors border border-[#262930]"
                        >
                          {isExpanded ? "Collapse" : "Inspect Payload"}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-surface-container-low/60">
                        <td colSpan={6} className="p-4 border-t border-[#262930]">
                          <div className="space-y-2">
                            <span className="font-label-mono text-kbd-shortcut uppercase text-outline">
                              Execution Arguments &amp; Policy Reason
                            </span>
                            <div className="p-3 bg-surface-container-lowest rounded border border-[#262930] font-code-block text-code-block text-on-surface overflow-x-auto">
                              <pre className="whitespace-pre-wrap">
                                {JSON.stringify(
                                  log.metadata_json || {
                                    tool_name: log.tool_name,
                                    resource_type: log.resource_type,
                                    resource_id: log.resource_id,
                                    risk_level: log.risk_level,
                                    execution_status: log.execution_status,
                                    error_code: log.error_code,
                                  },
                                  null,
                                  2
                                )}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
