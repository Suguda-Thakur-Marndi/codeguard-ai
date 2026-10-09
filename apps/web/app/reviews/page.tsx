"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { PullRequest, ReviewJob } from "../../lib/types";

export default function ReviewsListPage() {
  const [reviewJobs, setReviewJobs] = useState<{ job: ReviewJob; pr: PullRequest }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadReviews() {
      try {
        setLoading(true);
        const prsRes = await api.getPullRequests(1, 20);
        const prs = prsRes.items || [];
        const jobsList: { job: ReviewJob; pr: PullRequest }[] = [];

        await Promise.allSettled(
          prs.map(async (pr) => {
            const revRes = await api.getPullRequestReviews(pr.id, 1, 5);
            if (revRes.items) {
              revRes.items.forEach((job) => jobsList.push({ job, pr }));
            }
          })
        );

        setReviewJobs(jobsList);
      } catch (err) {
        console.error("Error loading reviews:", err);
      } finally {
        setLoading(false);
      }
    }
    loadReviews();
  }, []);

  return (
    <div className="flex flex-col w-full pb-16 space-y-space-md">
      <div className="flex items-center justify-between pb-space-md border-b border-[#262930]">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Autonomous Review Runs</h1>
          <p className="font-body-sm text-body-sm text-outline mt-0.5">
            Audit history of multi-agent review executions, token utilization, and consensus gates.
          </p>
        </div>
        <span className="font-label-mono text-kbd-shortcut px-2 py-1 rounded bg-surface-container-high text-on-surface border border-[#262930]">
          Total Jobs: {reviewJobs.length}
        </span>
      </div>

      <div className="bg-surface-container-lowest rounded-lg border border-[#262930] overflow-hidden shadow-sm">
        <table className="w-full text-left font-body-sm text-body-sm border-collapse">
          <thead>
            <tr className="bg-surface-container text-on-surface-variant font-label-mono text-kbd-shortcut uppercase tracking-wider">
              <th className="py-2.5 px-4">Review Job ID</th>
              <th className="py-2.5 px-3">Pull Request</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Tokens / Cost</th>
              <th className="py-2.5 px-3">Started</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#262930]/40">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-outline font-label-mono">
                  Loading review runs...
                </td>
              </tr>
            ) : reviewJobs.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <span className="material-symbols-outlined text-[32px] text-outline">rate_review</span>
                    <p className="text-on-surface font-medium">No review jobs executed yet</p>
                    <p className="text-outline text-xs">
                      Trigger a review on any pull request or open a new PR via webhook.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              reviewJobs.map(({ job, pr }) => (
                <tr key={job.id} className="hover:bg-surface-container transition-colors group">
                  <td className="py-3 px-4">
                    <span className="font-code-inline text-code-block text-primary font-medium">
                      {job.id.slice(0, 12)}...
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <Link href={`/pull-requests/${pr.id}`} className="hover:underline text-on-surface">
                      <span className="font-label-mono text-primary-fixed">#{pr.number}</span> {pr.title}
                    </Link>
                  </td>
                  <td className="py-3 px-3">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="py-3 px-3 font-label-mono text-kbd-shortcut text-outline">
                    {job.total_tokens ? `${job.total_tokens.toLocaleString()} tok` : "—"} ·{" "}
                    {job.estimated_cost ? `$${job.estimated_cost.toFixed(4)}` : "—"}
                  </td>
                  <td className="py-3 px-3 font-label-mono text-kbd-shortcut text-outline">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      href={`/reviews/${job.id}`}
                      className="font-label-mono text-kbd-shortcut px-2.5 py-1 rounded bg-surface-container-high hover:bg-primary-container hover:text-on-primary-container text-on-surface transition-colors border border-[#262930]"
                    >
                      Inspector &rarr;
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
