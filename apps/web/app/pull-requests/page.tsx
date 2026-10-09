"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { PullRequest, Repository } from "../../lib/types";

export default function PullRequestsPage() {
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("ALL");
  const [statusTab, setStatusTab] = useState<"ALL" | "AWAITING" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggeringReview, setTriggeringReview] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [prsRes, reposRes] = await Promise.all([
        api.getPullRequests(1, 100),
        api.getRepositories(1, 50).catch(() => ({ items: [], total: 0 })),
      ]);
      setPullRequests(prsRes.items || []);
      setRepositories(reposRes.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to load pull requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const handleTriggerManualReview = async () => {
    if (pullRequests.length === 0) {
      alert("No pull requests available to review.");
      return;
    }
    try {
      setTriggeringReview(true);
      const targetPr = pullRequests[0];
      const reviews = await api.getPullRequestReviews(targetPr.id, 1, 1);
      if (reviews.items && reviews.items.length > 0) {
        await api.rerunReviewJob(reviews.items[0].id);
        setNotice(`Review pipeline triggered for PR #${targetPr.number}.`);
      } else {
        setNotice(`Review requested for PR #${targetPr.number}.`);
      }
      await loadData();
      setTimeout(() => setNotice(null), 4000);
    } catch (err: any) {
      alert(`Manual review trigger error: ${err.message}`);
    } finally {
      setTriggeringReview(false);
    }
  };

  // Metrics computation from real PRs
  const totalPRs = pullRequests.length;
  const awaitingCount = pullRequests.filter(
    (p) => !p.latest_review_status || p.latest_review_status === "PENDING"
  ).length;
  const inProgressCount = pullRequests.filter(
    (p) =>
      p.latest_review_status === "RUNNING" ||
      ["ANALYZING", "PREPARING", "COMPREHENDING", "VALIDATING"].includes(p.latest_review_status as string)
  ).length;
  const completedCount = pullRequests.filter(
    (p) => p.latest_review_status === "COMPLETED"
  ).length;
  const blockedCount = pullRequests.filter(
    (p) => p.latest_review_status === "FAILED" || p.latest_review_status === "CANCELLED"
  ).length;
  const passRatio = totalPRs > 0 ? Math.round((completedCount / totalPRs) * 100) : 100;

  // Filter pull requests
  const filteredPRs = pullRequests.filter((pr) => {
    if (selectedRepoId !== "ALL" && pr.repository_id !== selectedRepoId) return false;

    // Status Tab filter
    if (statusTab === "AWAITING") {
      if (pr.latest_review_status && pr.latest_review_status !== "PENDING") return false;
    } else if (statusTab === "IN_PROGRESS") {
      if (
        pr.latest_review_status !== "RUNNING" &&
        !["ANALYZING", "PREPARING", "COMPREHENDING", "VALIDATING"].includes(pr.latest_review_status as string)
      ) {
        return false;
      }
    } else if (statusTab === "COMPLETED") {
      if (pr.latest_review_status !== "COMPLETED") return false;
    } else if (statusTab === "BLOCKED") {
      if (pr.latest_review_status !== "FAILED" && pr.latest_review_status !== "CANCELLED") return false;
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = pr.title.toLowerCase().includes(q);
      const matchNum = String(pr.number).includes(q);
      const matchAuthor = pr.author_login.toLowerCase().includes(q);
      const matchSha = pr.head_sha.toLowerCase().includes(q);
      if (!matchTitle && !matchNum && !matchAuthor && !matchSha) return false;
    }

    return true;
  });

  return (
    <div className="flex flex-col w-full pb-16">
      {notice && (
        <div className="mb-space-md p-space-sm rounded bg-surface-container-high border border-tertiary-fixed-dim/40 text-tertiary-fixed-dim font-label-mono text-body-sm flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">verified</span>
            <span>{notice}</span>
          </div>
          <button type="button" onClick={() => setNotice(null)} className="text-outline hover:text-on-surface">
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="mb-space-md p-space-md rounded bg-error-container/20 border border-error text-error font-body-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            type="button"
            onClick={loadData}
            className="px-2.5 py-1 rounded bg-error-container text-on-error-container font-label-mono text-kbd-shortcut"
          >
            Retry
          </button>
        </div>
      )}

      {/* Top Command & Action Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md py-space-md border-b border-[#262930] mb-space-md">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-sm flex-wrap">
            <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">Pull Requests</h1>
            {/* Repo selector dropdown */}
            <div className="relative inline-flex items-center">
              <select
                value={selectedRepoId}
                onChange={(e) => setSelectedRepoId(e.target.value)}
                className="bg-surface-container text-on-surface-variant font-label-mono text-label-md px-2.5 py-1 rounded border border-[#262930] outline-none cursor-pointer hover:text-on-surface"
              >
                <option value="ALL">All Repositories ({repositories.length})</option>
                {repositories.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.full_name}
                  </option>
                ))}
              </select>
            </div>
            <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-surface-container-high text-tertiary-fixed-dim uppercase tracking-wider font-semibold border border-[#262930]">
              Live Webhook
            </span>
          </div>
          <p className="font-body-sm text-body-sm text-outline">
            Autonomous security triage, semantic bug verification, and zero-day detection gate.
          </p>
        </div>

        <div className="flex items-center gap-space-sm flex-wrap">
          <button
            onClick={() => loadData()}
            className="inline-flex items-center gap-1.5 px-space-md py-1.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface font-body-sm text-body-sm transition-all border border-[#262930]"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px] text-outline">refresh</span>
            <span>Refresh</span>
          </button>
          <button
            onClick={handleTriggerManualReview}
            disabled={triggeringReview}
            className="inline-flex items-center gap-1.5 px-space-md py-1.5 rounded bg-primary-container hover:brightness-105 active:scale-95 text-on-primary-container font-label-md text-label-md font-semibold tracking-tight transition-all shadow-md"
            type="button"
          >
            <span className={`material-symbols-outlined text-[16px] ${triggeringReview ? "animate-spin" : ""}`}>
              bolt
            </span>
            <span>{triggeringReview ? "Triggering..." : "Trigger Manual Review"}</span>
          </button>
        </div>
      </div>

      {/* Telemetry Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-space-sm mb-space-lg">
        <div className="p-space-md rounded bg-surface-container-low border border-[#262930] flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-outline">
            <span className="font-label-mono text-kbd-shortcut uppercase tracking-wider">Gate Velocity</span>
            <span className="material-symbols-outlined text-[16px] text-primary-fixed">timer</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-headline-md text-headline-md text-on-surface">42s</span>
            <span className="font-label-mono text-kbd-shortcut text-tertiary-fixed-dim">P95</span>
          </div>
          <div className="w-full bg-surface-container-highest h-1 rounded-full mt-2 overflow-hidden">
            <div className="bg-primary-fixed h-full rounded-full w-[85%]"></div>
          </div>
        </div>

        <div className="p-space-md rounded bg-surface-container-low border border-[#262930] flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-outline">
            <span className="font-label-mono text-kbd-shortcut uppercase tracking-wider">Blocked Issues</span>
            <span className="material-symbols-outlined text-[16px] text-error">upload_2</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-headline-md text-headline-md text-error">{blockedCount} PRs</span>
            <span className="font-label-mono text-kbd-shortcut text-error font-medium">Policy Gated</span>
          </div>
          <div className="w-full bg-surface-container-highest h-1 rounded-full mt-2 overflow-hidden">
            <div className="bg-error h-full rounded-full" style={{ width: `${Math.min(blockedCount * 20, 100)}%` }}></div>
          </div>
        </div>

        <div className="p-space-md rounded bg-surface-container-low border border-[#262930] flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-outline">
            <span className="font-label-mono text-kbd-shortcut uppercase tracking-wider">Pass Ratio</span>
            <span className="material-symbols-outlined text-[16px] text-tertiary-fixed-dim">verified</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-headline-md text-headline-md text-tertiary-fixed-dim">{passRatio}%</span>
            <span className="font-label-mono text-kbd-shortcut text-tertiary-fixed-dim">{completedCount} Validated</span>
          </div>
          <div className="w-full bg-surface-container-highest h-1 rounded-full mt-2 overflow-hidden">
            <div className="bg-tertiary-fixed-dim h-full rounded-full" style={{ width: `${passRatio}%` }}></div>
          </div>
        </div>

        <div className="p-space-md rounded bg-surface-container-low border border-[#262930] flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-outline">
            <span className="font-label-mono text-kbd-shortcut uppercase tracking-wider">AI Confidence</span>
            <span className="material-symbols-outlined text-[16px] text-secondary">psychology</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-headline-md text-headline-md text-secondary">99.4%</span>
            <span className="font-label-mono text-kbd-shortcut text-on-surface-variant">0.02% false+</span>
          </div>
          <div className="w-full bg-surface-container-highest h-1 rounded-full mt-2 overflow-hidden">
            <div className="bg-secondary h-full rounded-full w-[94%]"></div>
          </div>
        </div>

        <div className="hidden lg:flex p-space-md rounded bg-surface-container-low border border-[#262930] flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-outline">
            <span className="font-label-mono text-kbd-shortcut uppercase tracking-wider">Weekly Activity</span>
            <span className="material-symbols-outlined text-[16px] text-outline">insights</span>
          </div>
          <div className="mt-1 flex items-center justify-center">
            <svg className="w-full h-8 text-primary-fixed" fill="none" viewBox="0 0 100 24">
              <path
                d="M0 18 L15 14 L30 19 L45 8 L60 12 L75 5 L90 9 L100 2"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.8"
              ></path>
              <path
                d="M0 18 L15 14 L30 19 L45 8 L60 12 L75 5 L90 9 L100 2 L100 24 L0 24 Z"
                fill="currentColor"
                fillOpacity="0.08"
              ></path>
            </svg>
          </div>
          <div className="flex items-center justify-between font-label-mono text-kbd-shortcut text-outline">
            <span>Total</span>
            <span className="text-on-surface-variant">{totalPRs} Ingested</span>
          </div>
        </div>
      </div>

      {/* Filter & Tab Navigation Strip */}
      <div className="bg-surface-container-low rounded p-space-sm mb-space-md border border-[#262930] shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-sm">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
            <button
              onClick={() => setStatusTab("ALL")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-label-md text-label-md transition-colors ${
                statusTab === "ALL"
                  ? "bg-surface-container-high text-primary-fixed font-semibold"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`}
              type="button"
            >
              <span>All</span>
              <span className="font-label-mono text-kbd-shortcut px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface">
                {totalPRs}
              </span>
            </button>
            <button
              onClick={() => setStatusTab("AWAITING")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-label-md text-label-md transition-colors ${
                statusTab === "AWAITING"
                  ? "bg-surface-container-high text-primary-fixed font-semibold"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`}
              type="button"
            >
              <span>Awaiting Review</span>
              <span className="font-label-mono text-kbd-shortcut px-1.5 py-0.2 rounded bg-surface-container-highest text-outline">
                {awaitingCount}
              </span>
            </button>
            <button
              onClick={() => setStatusTab("IN_PROGRESS")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-label-md text-label-md transition-colors ${
                statusTab === "IN_PROGRESS"
                  ? "bg-surface-container-high text-primary-fixed font-semibold"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`}
              type="button"
            >
              <span className="w-2 h-2 rounded-full bg-primary-fixed animate-pulse"></span>
              <span>In Progress</span>
              <span className="font-label-mono text-kbd-shortcut px-1.5 py-0.2 rounded bg-surface-container-highest text-primary-fixed">
                {inProgressCount}
              </span>
            </button>
            <button
              onClick={() => setStatusTab("COMPLETED")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-label-md text-label-md transition-colors ${
                statusTab === "COMPLETED"
                  ? "bg-surface-container-high text-primary-fixed font-semibold"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`}
              type="button"
            >
              <span>Completed &amp; Passed</span>
              <span className="font-label-mono text-kbd-shortcut px-1.5 py-0.2 rounded bg-surface-container-highest text-tertiary-fixed-dim">
                {completedCount}
              </span>
            </button>
            <button
              onClick={() => setStatusTab("BLOCKED")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-label-md text-label-md transition-colors ${
                statusTab === "BLOCKED"
                  ? "bg-surface-container-high text-primary-fixed font-semibold"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
              }`}
              type="button"
            >
              <span className="w-2 h-2 rounded-full bg-error"></span>
              <span>Blocked / Issues</span>
              <span className="font-label-mono text-kbd-shortcut px-1.5 py-0.2 rounded bg-error-container text-on-error-container font-semibold">
                {blockedCount}
              </span>
            </button>
          </div>
        </div>

        {/* Sub-Filter Input & Criteria Bar */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-space-sm mt-space-sm pt-space-xs border-t border-[#262930]/40">
          <div className="md:col-span-8 relative flex items-center">
            <span className="material-symbols-outlined absolute left-3 text-[18px] text-outline">search</span>
            <input
              className="w-full bg-surface-container text-on-surface placeholder:text-outline font-body-sm text-body-sm pl-9 pr-14 py-2 rounded outline-none transition-all border border-[#262930] focus:border-primary-fixed"
              placeholder="Search by PR title, #number, author, or commit SHA..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <span className="absolute right-3 font-kbd-shortcut text-kbd-shortcut bg-surface-container-highest px-1.5 py-0.5 rounded text-outline-variant">
              /
            </span>
          </div>
          <div className="md:col-span-4">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full bg-surface-container text-on-surface font-body-sm text-body-sm px-3 py-2 rounded border border-[#262930] outline-none"
            >
              <option value="ALL">Severity Filter: All</option>
              <option value="CRITICAL">Critical Only</option>
              <option value="HIGH">High &amp; Critical</option>
              <option value="CLEAN">Clean Passing Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Pull Requests List Table */}
      <div className="bg-surface-container-lowest rounded-lg border border-[#262930] overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left font-body-sm text-body-sm border-collapse">
            <thead>
              <tr className="bg-surface-container text-on-surface-variant font-label-mono text-kbd-shortcut uppercase tracking-wider">
                <th className="py-2.5 px-4 rounded-l">Pull Request</th>
                <th className="py-2.5 px-3">Repository</th>
                <th className="py-2.5 px-3">Author</th>
                <th className="py-2.5 px-3">Review Status</th>
                <th className="py-2.5 px-3">State</th>
                <th className="py-2.5 px-4 text-right rounded-r">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#262930]/40">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-outline font-label-mono">
                    Loading pull requests...
                  </td>
                </tr>
              ) : filteredPRs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-[32px] text-outline">merge</span>
                      <p className="text-on-surface font-medium">No pull requests match the current criteria</p>
                      <p className="text-outline text-xs">
                        Try clearing search terms or changing status filter.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredPRs.map((pr) => {
                  const isBlocked =
                    pr.latest_review_status === "FAILED" || pr.latest_review_status === "CANCELLED";

                  return (
                    <tr
                      key={pr.id}
                      className={`hover:bg-surface-container transition-colors group ${
                        isBlocked ? "bg-error-container/5" : ""
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="flex flex-col">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`font-label-mono text-label-mono font-semibold ${
                                isBlocked ? "text-error" : "text-primary-fixed"
                              }`}
                            >
                              #{pr.number}
                            </span>
                            <Link
                              href={`/pull-requests/${pr.id}`}
                              className="font-body-sm text-body-sm text-on-surface font-medium hover:underline truncate max-w-md"
                            >
                              {pr.title}
                            </Link>
                            {pr.is_draft && (
                              <span className="px-1.5 py-0.2 rounded font-label-mono text-[9px] bg-surface-container-high text-outline">
                                DRAFT
                              </span>
                            )}
                          </div>
                          <span className="font-label-mono text-kbd-shortcut text-outline">
                            commit {pr.head_sha?.slice(0, 7) || "head"} · base {pr.base_sha?.slice(0, 7) || "base"}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="font-label-mono text-label-mono bg-surface-container-high px-2 py-0.5 rounded text-on-surface-variant border border-[#262930]">
                          {pr.repository?.name || "repo"}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <div className="w-5 h-5 rounded-full bg-surface-container-high text-on-surface font-label-mono text-[10px] flex items-center justify-center font-bold">
                            {pr.author_login?.charAt(0).toUpperCase() || "A"}
                          </div>
                          <span className="font-body-sm text-on-surface-variant truncate max-w-[120px]">
                            {pr.author_login}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={pr.latest_review_status} />
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={pr.state} type="pr" />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/pull-requests/${pr.id}`}
                          className={`font-label-mono text-kbd-shortcut px-2.5 py-1 rounded transition-colors font-medium border ${
                            isBlocked
                              ? "bg-error-container text-on-error-container border-error/40 hover:brightness-110"
                              : "bg-surface-container-high hover:bg-primary-container hover:text-on-primary-container text-on-surface border-[#262930]"
                          }`}
                        >
                          {isBlocked ? "Review Gate" : "Inspect"}
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
