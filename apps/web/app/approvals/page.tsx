"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";
import { ApprovalRequest } from "../../lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");

  // Action modals / inputs
  const [activeModal, setActiveModal] = useState<{
    type: "approve" | "reject";
    approval: ApprovalRequest;
  } | null>(null);
  const [actionInput, setActionInput] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);

  async function loadApprovals() {
    try {
      setLoading(true);
      setError(null);
      const statusParam = filterStatus === "ALL" ? undefined : filterStatus;
      const res = await api.getApprovals(1, 50, undefined, undefined, statusParam);
      setApprovals(res.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to load approval requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadApprovals();
  }, [filterStatus]);

  async function handleConfirmAction() {
    if (!activeModal) return;
    try {
      setSubmitting(true);
      if (activeModal.type === "approve") {
        await api.approveApproval(activeModal.approval.id, actionInput || "Approved by Reviewer");
      } else {
        if (!actionInput.trim()) {
          alert("A reason is required to reject an approval request.");
          setSubmitting(false);
          return;
        }
        await api.rejectApproval(activeModal.approval.id, actionInput);
      }
      setActiveModal(null);
      setActionInput("");
      await loadApprovals();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case "PENDING":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">PENDING APPROVAL</span>;
      case "APPROVED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">APPROVED</span>;
      case "REJECTED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">REJECTED</span>;
      case "EXPIRED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">EXPIRED</span>;
      case "CANCELLED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">CANCELLED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">{status}</span>;
    }
  }

  function getRiskBadge(risk: string) {
    switch (risk) {
      case "HIGH_RISK":
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">HIGH RISK</span>;
      case "CONSEQUENTIAL":
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">CONSEQUENTIAL</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">{risk}</span>;
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Human Approval Gate</h1>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Zero-Trust Tool Boundary
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Consequential and high-risk GitHub operations require explicit human reviewer authorization.
          </p>
        </div>

        {/* Filter pills */}
        <div className="flex items-center gap-1.5 bg-slate-900/80 p-1 rounded-lg border border-slate-800 text-xs">
          {["ALL", "PENDING", "APPROVED", "REJECTED", "EXPIRED"].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                filterStatus === status
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/50"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Overview stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
          <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">Pending Gate</span>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {approvals.filter((a) => a.status === "PENDING").length}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
          <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">Approved</span>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {approvals.filter((a) => a.status === "APPROVED").length}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
          <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">Rejected</span>
          <div className="text-2xl font-bold text-rose-400 mt-1">
            {approvals.filter((a) => a.status === "REJECTED").length}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
          <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">Total Requests</span>
          <div className="text-2xl font-bold text-slate-200 mt-1">{approvals.length}</div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="rounded-xl bg-slate-900/40 border border-slate-800 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm animate-pulse">
            Loading approval requests...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-rose-400 bg-rose-500/10 border border-rose-500/20 text-sm">
            {error}
          </div>
        ) : approvals.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <div className="w-12 h-12 rounded-full bg-slate-800 mx-auto flex items-center justify-center text-slate-400">
              ✓
            </div>
            <p className="text-sm font-medium text-slate-300">No approval requests found</p>
            <p className="text-xs text-slate-500">
              {filterStatus === "ALL" ? "All operations authorized or no pending reviews require human sign-off." : `No requests match status "${filterStatus}".`}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-mono text-slate-400 uppercase border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Repository & PR</th>
                  <th className="px-6 py-3">Action & Risk</th>
                  <th className="px-6 py-3">Finding Target</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Timing & Expiration</th>
                  <th className="px-6 py-3 text-right">Gate Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {approvals.map((req) => {
                  const isPending = req.status === "PENDING";
                  return (
                    <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-6 py-4 font-sans">
                        <div className="font-semibold text-white">
                          {req.repository_name || req.repository_id.slice(0, 8)}
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          PR #{req.pull_request_number || "—"}{" "}
                          <span className="text-slate-600">|</span> Commit:{" "}
                          <span className="font-mono text-slate-300">
                            {req.head_sha ? req.head_sha.slice(0, 7) : "—"}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-sans space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-indigo-300">{req.requested_action}</span>
                          {getRiskBadge(req.risk_level)}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          By: <span className="font-mono text-slate-400">{req.requested_by}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-sans max-w-xs">
                        <div className="font-medium text-slate-200 truncate">
                          {req.finding_title || `Finding ${req.finding_id.slice(0, 8)}`}
                        </div>
                        {req.finding_severity && (
                          <div className="text-xs text-rose-400 mt-0.5">
                            Severity: {req.finding_severity}
                          </div>
                        )}
                        {req.reason && (
                          <div className="text-xs text-slate-400 mt-1 italic line-clamp-1">
                            &ldquo;{req.reason}&rdquo;
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 font-sans">{getStatusBadge(req.status)}</td>
                      <td className="px-6 py-4 text-xs text-slate-400 font-mono">
                        <div>Created: {new Date(req.created_at).toLocaleTimeString()}</div>
                        <div className="text-slate-500">
                          Expires: {new Date(req.expires_at).toLocaleTimeString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right font-sans">
                        {isPending ? (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                setActiveModal({ type: "approve", approval: req });
                                setActionInput("");
                              }}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow transition-colors"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => {
                                setActiveModal({ type: "reject", approval: req });
                                setActionInput("");
                              }}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-500/30 transition-colors"
                            >
                              Reject
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500">
                            {req.approved_by ? `Resolved by ${req.approved_by}` : "Closed"}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Interactive Modal */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white">
                {activeModal.type === "approve" ? "Authorize GitHub Action" : "Reject Approval Request"}
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="text-slate-500 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 text-xs space-y-1 font-mono">
              <div className="text-slate-400">
                Action: <span className="text-white font-bold">{activeModal.approval.requested_action}</span>
              </div>
              <div className="text-slate-400">
                Head SHA: <span className="text-indigo-400">{activeModal.approval.head_sha || "—"}</span>
              </div>
              <div className="text-slate-400">
                Target Finding: <span className="text-slate-300">{activeModal.approval.finding_id}</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                {activeModal.type === "approve"
                  ? "Optional Approval Note"
                  : "Rejection Reason (Required)"}
              </label>
              <textarea
                rows={3}
                value={actionInput}
                onChange={(e) => setActionInput(e.target.value)}
                placeholder={
                  activeModal.type === "approve"
                    ? "Add human reviewer authorization rationale..."
                    : "Specify why this finding should not be published to GitHub..."
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={handleConfirmAction}
                className={`px-4 py-2 rounded-lg text-xs font-semibold text-white shadow ${
                  activeModal.type === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : "bg-rose-600 hover:bg-rose-500"
                } disabled:opacity-50`}
              >
                {submitting ? "Processing..." : activeModal.type === "approve" ? "Confirm Approval" : "Reject Request"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
