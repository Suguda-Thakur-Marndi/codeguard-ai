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
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-highest text-primary-fixed border border-primary-fixed/30 font-semibold animate-pulse">
            PENDING APPROVAL
          </span>
        );
      case "APPROVED":
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-tertiary-container text-on-tertiary-container font-semibold">
            APPROVED
          </span>
        );
      case "REJECTED":
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-error-container text-on-error-container font-semibold">
            REJECTED
          </span>
        );
      case "EXPIRED":
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-outline">
            EXPIRED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-on-surface">
            {status}
          </span>
        );
    }
  }

  function getRiskBadge(risk: string) {
    switch (risk) {
      case "HIGH_RISK":
        return (
          <span className="px-1.5 py-0.5 rounded font-label-mono text-kbd-shortcut font-bold bg-error-container/40 text-error border border-error/30">
            HIGH RISK
          </span>
        );
      case "CONSEQUENTIAL":
        return (
          <span className="px-1.5 py-0.5 rounded font-label-mono text-kbd-shortcut font-bold bg-surface-container-highest text-surface-tint border border-surface-tint/30">
            CONSEQUENTIAL
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-outline">
            {risk}
          </span>
        );
    }
  }

  const pendingCount = approvals.filter((a) => a.status === "PENDING").length;
  const approvedCount = approvals.filter((a) => a.status === "APPROVED").length;
  const rejectedCount = approvals.filter((a) => a.status === "REJECTED").length;

  return (
    <div className="flex flex-col w-full pb-16 space-y-space-md">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#262930] pb-space-md">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">
              Human Approval &amp; Governance Gate
            </h1>
            <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-secondary border border-[#262930]">
              Zero-Trust Policy Boundary
            </span>
          </div>
          <p className="font-body-sm text-body-sm text-outline mt-1">
            Consequential and high-risk operations require explicit human reviewer sign-off before publishing.
          </p>
        </div>

        {/* Filter pills */}
        <div className="flex items-center gap-1.5 bg-surface-container p-1 rounded-lg border border-[#262930] text-xs">
          {["ALL", "PENDING", "APPROVED", "REJECTED", "EXPIRED"].map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1 rounded font-label-mono text-kbd-shortcut transition-colors ${
                filterStatus === status
                  ? "bg-surface-container-highest text-primary-fixed font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Overview stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-space-sm">
        <div className="p-space-md rounded-lg bg-surface-container-low border border-[#262930]">
          <span className="font-label-mono text-kbd-shortcut text-outline uppercase tracking-wider">Pending Gate</span>
          <div className="font-headline-md text-headline-md font-bold text-primary-fixed mt-1">
            {pendingCount}
          </div>
        </div>
        <div className="p-space-md rounded-lg bg-surface-container-low border border-[#262930]">
          <span className="font-label-mono text-kbd-shortcut text-outline uppercase tracking-wider">Approved</span>
          <div className="font-headline-md text-headline-md font-bold text-tertiary-fixed-dim mt-1">
            {approvedCount}
          </div>
        </div>
        <div className="p-space-md rounded-lg bg-surface-container-low border border-[#262930]">
          <span className="font-label-mono text-kbd-shortcut text-outline uppercase tracking-wider">Rejected</span>
          <div className="font-headline-md text-headline-md font-bold text-error mt-1">
            {rejectedCount}
          </div>
        </div>
        <div className="p-space-md rounded-lg bg-surface-container-low border border-[#262930]">
          <span className="font-label-mono text-kbd-shortcut text-outline uppercase tracking-wider">Total Evaluated</span>
          <div className="font-headline-md text-headline-md font-bold text-primary mt-1">
            {approvals.length}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-space-md rounded bg-error-container/20 border border-error text-error text-xs font-mono">
          {error}
        </div>
      )}

      {/* Main Approvals Table */}
      <div className="bg-surface-container-lowest rounded-lg border border-[#262930] overflow-hidden shadow-sm">
        <table className="w-full text-left font-body-sm text-body-sm border-collapse">
          <thead>
            <tr className="bg-surface-container text-on-surface-variant font-label-mono text-kbd-shortcut uppercase tracking-wider">
              <th className="py-2.5 px-4">Action / Scope</th>
              <th className="py-2.5 px-3">Risk Level</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Review Job / PR</th>
              <th className="py-2.5 px-3">Requested At</th>
              <th className="py-2.5 px-4 text-right">Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#262930]/40">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-outline font-label-mono">
                  Loading approval requests...
                </td>
              </tr>
            ) : approvals.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <span className="material-symbols-outlined text-[32px] text-tertiary-fixed-dim">
                      assignment_turned_in
                    </span>
                    <p className="text-on-surface font-medium">No approval requests found</p>
                    <p className="text-outline text-xs">
                      All autonomous policy gates are clear. No pending human reviews.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              approvals.map((app) => (
                <tr key={app.id} className="hover:bg-surface-container transition-colors group">
                  <td className="py-3 px-4">
                    <div className="flex flex-col">
                      <span className="font-mono text-xs font-semibold text-primary">{app.requested_action}</span>
                      <span className="text-[11px] text-outline truncate max-w-sm">
                        {app.reason || "Requires human confirmation before GitHub dispatch."}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3">{getRiskBadge(app.risk_level)}</td>
                  <td className="py-3 px-3">{getStatusBadge(app.status)}</td>
                  <td className="py-3 px-3">
                    <div className="flex flex-col font-mono text-[11px]">
                      {app.pull_request_id ? (
                        <Link
                          href={`/pull-requests/${app.pull_request_id}`}
                          className="text-primary-fixed hover:underline"
                        >
                          PR {app.pull_request_id.slice(0, 8)}...
                        </Link>
                      ) : (
                        <span className="text-outline">PR —</span>
                      )}
                      <span className="text-outline">Job: {app.review_job_id.slice(0, 8)}...</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-outline">
                    {new Date(app.created_at).toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {app.status === "PENDING" ? (
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            setActiveModal({ type: "approve", approval: app });
                            setActionInput("");
                          }}
                          className="px-2.5 py-1 rounded bg-primary-container text-on-primary-container font-label-mono text-kbd-shortcut font-semibold hover:brightness-105 transition-all shadow-sm"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setActiveModal({ type: "reject", approval: app });
                            setActionInput("");
                          }}
                          className="px-2.5 py-1 rounded bg-surface-container-high hover:bg-error-container hover:text-on-error-container text-on-surface font-label-mono text-kbd-shortcut border border-[#262930] transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className="text-[11px] font-mono text-outline">Decision Recorded</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Decision Modal */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-surface-container-low border border-[#333842] rounded-xl max-w-lg w-full p-space-md shadow-2xl space-y-space-md">
            <div className="flex items-center justify-between border-b border-[#262930] pb-2">
              <h3 className="font-headline-sm text-headline-sm text-primary">
                {activeModal.type === "approve" ? "Confirm Authorization" : "Reject Operation"}
              </h3>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="text-outline hover:text-on-surface"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <p className="text-on-surface">
                Action: <code className="text-primary-fixed font-mono">{activeModal.approval.requested_action}</code>
              </p>
              <p className="text-outline">
                {activeModal.type === "approve"
                  ? "Authorizing this request will dispatch the tool operation to the external system."
                  : "Provide a justification for blocking this execution:"}
              </p>
              <textarea
                value={actionInput}
                onChange={(e) => setActionInput(e.target.value)}
                placeholder={
                  activeModal.type === "approve"
                    ? "Optional approval comment..."
                    : "Mandatory rejection reason..."
                }
                className="w-full bg-surface-container-lowest text-on-surface border border-[#262930] rounded p-2 text-xs outline-none focus:border-primary-fixed h-24"
              />
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[#262930] pt-2">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="px-3 py-1.5 rounded bg-surface-container-high text-on-surface font-label-mono text-kbd-shortcut border border-[#262930]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmAction}
                disabled={submitting}
                className={`px-3 py-1.5 rounded font-label-mono text-kbd-shortcut font-semibold shadow-sm ${
                  activeModal.type === "approve"
                    ? "bg-primary-container text-on-primary-container hover:brightness-105"
                    : "bg-error-container text-on-error-container hover:brightness-110"
                }`}
              >
                {submitting ? "Submitting..." : activeModal.type === "approve" ? "Authorize & Publish" : "Reject Bypass"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
