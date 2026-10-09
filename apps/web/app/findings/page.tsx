"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { PullRequest, ReviewFinding } from "../../lib/types";

export default function FindingsPage() {
  const [findings, setFindings] = useState<{ finding: ReviewFinding; pr: PullRequest }[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [searchFilter, setSearchFilter] = useState("");

  useEffect(() => {
    async function loadFindings() {
      try {
        setLoading(true);
        const prsRes = await api.getPullRequests(1, 20);
        const prs = prsRes.items || [];
        const aggregated: { finding: ReviewFinding; pr: PullRequest }[] = [];

        await Promise.allSettled(
          prs.map(async (pr) => {
            const revRes = await api.getPullRequestReviews(pr.id, 1, 1);
            if (revRes.items && revRes.items.length > 0) {
              const fList = await api.getReviewJobFindings(revRes.items[0].id);
              fList.forEach((f) => aggregated.push({ finding: f, pr }));
            }
          })
        );

        setFindings(aggregated);
      } catch (err) {
        console.error("Error loading findings:", err);
      } finally {
        setLoading(false);
      }
    }
    loadFindings();
  }, []);

  const filtered = findings.filter(({ finding }) => {
    if (severityFilter !== "ALL" && finding.severity !== severityFilter) return false;
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      const matchTitle = finding.title.toLowerCase().includes(q);
      const matchDesc = finding.description.toLowerCase().includes(q);
      const matchRule = ((finding.rule_id as string) || finding.affected_symbol || "").toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchRule) return false;
    }
    return true;
  });

  const criticalCount = findings.filter((f) => f.finding.severity === "CRITICAL").length;
  const highCount = findings.filter((f) => f.finding.severity === "HIGH").length;

  return (
    <div className="flex flex-col w-full pb-16 space-y-space-md">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-space-md border-b border-[#262930]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Security Findings &amp; Triage</h1>
            <span className="font-label-mono text-kbd-shortcut px-2 py-0.5 rounded bg-error-container text-on-error-container font-semibold">
              {criticalCount} Critical
            </span>
          </div>
          <p className="font-body-sm text-body-sm text-outline mt-0.5">
            Cross-repository security vulnerabilities, semantic bug detections, and compliance flags.
          </p>
        </div>

        {/* Severity Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1 rounded font-label-mono text-kbd-shortcut uppercase transition-colors border ${
                severityFilter === sev
                  ? "bg-surface-container-high text-primary-fixed border-primary-fixed/40 font-semibold"
                  : "bg-surface-container text-on-surface-variant border-[#262930] hover:text-on-surface"
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="relative">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-outline">
          search
        </span>
        <input
          type="text"
          placeholder="Filter by vulnerability title, CWE ID, or description..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          className="w-full bg-surface-container-lowest text-on-surface placeholder:text-outline font-body-sm text-body-sm pl-10 pr-4 py-2 rounded border border-[#262930] focus:border-primary-fixed outline-none"
        />
      </div>

      {/* Findings Table */}
      <div className="bg-surface-container-lowest rounded-lg border border-[#262930] overflow-hidden shadow-sm">
        <table className="w-full text-left font-body-sm text-body-sm border-collapse">
          <thead>
            <tr className="bg-surface-container text-on-surface-variant font-label-mono text-kbd-shortcut uppercase tracking-wider">
              <th className="py-2.5 px-4">Severity</th>
              <th className="py-2.5 px-3">Vulnerability / Rule</th>
              <th className="py-2.5 px-3">File &amp; Line</th>
              <th className="py-2.5 px-3">Pull Request</th>
              <th className="py-2.5 px-3">Consensus Status</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#262930]/40">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-outline font-label-mono">
                  Loading security findings...
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <span className="material-symbols-outlined text-[32px] text-tertiary-fixed-dim">check_circle</span>
                    <p className="text-on-surface font-medium">No findings matching active filter</p>
                    <p className="text-outline text-xs">
                      Zero unresolved vulnerabilities detected across monitored codebases.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map(({ finding, pr }) => (
                <tr key={finding.id} className="hover:bg-surface-container transition-colors group">
                  <td className="py-3 px-4">
                    <StatusBadge status={finding.severity} type="finding" />
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-col max-w-md">
                      <span className="font-semibold text-on-surface group-hover:text-primary transition-colors">
                        {finding.title}
                      </span>
                      <span className="font-label-mono text-kbd-shortcut text-outline">
                        {(finding.rule_id as string) || finding.affected_symbol || "CWE-347"} · {finding.category}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-code-inline text-code-block text-outline-variant">
                      {finding.file_path}:{finding.line_number || 1}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-label-mono text-kbd-shortcut text-primary-fixed">
                      PR #{pr.number} ({pr.repository?.name || "repo"})
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1 font-label-mono text-kbd-shortcut text-tertiary-fixed-dim">
                      <span className="material-symbols-outlined text-[13px]">verified</span>
                      Judge Validated
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      href={`/pull-requests/${pr.id}`}
                      className="font-label-mono text-kbd-shortcut px-2.5 py-1 rounded bg-surface-container-high hover:bg-primary-container hover:text-on-primary-container text-on-surface transition-colors border border-[#262930]"
                    >
                      Audit Diff
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
