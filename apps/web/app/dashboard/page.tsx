"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { MetricCard } from "../../components/MetricCard";
import { Phase1Notice } from "../../components/Phase1Notice";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { PullRequest, Repository } from "../../lib/types";

export default function DashboardPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const [reposRes, prsRes] = await Promise.all([
          api.getRepositories(1, 50).catch(() => ({ items: [], total: 0 })),
          api.getPullRequests(1, 50).catch(() => ({ items: [], total: 0 })),
        ]);
        setRepositories(reposRes.items);
        setPullRequests(prsRes.items);
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Compute metrics from real data
  const totalRepos = repositories.length;
  const totalPRs = pullRequests.length;
  const runningReviews = pullRequests.filter((p) => p.latest_review_status === "RUNNING").length;
  const completedReviews = pullRequests.filter((p) => p.latest_review_status === "COMPLETED").length;
  const failedReviews = pullRequests.filter((p) => p.latest_review_status === "FAILED").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">System Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time status of GitHub App repositories, pull requests, and review jobs.
          </p>
        </div>
      </div>

      <Phase1Notice />

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-sm">
          <strong>Error connecting to API:</strong> {error}. Ensure backend is running at{" "}
          <code className="text-rose-200">http://localhost:8000</code>.
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard label="Repositories" value={loading ? "..." : totalRepos} subtext="Connected repos" />
        <MetricCard label="Total PRs" value={loading ? "..." : totalPRs} subtext="Ingested from webhooks" />
        <MetricCard
          label="Reviews Running"
          value={loading ? "..." : runningReviews}
          variant="default"
          subtext="Active in background"
        />
        <MetricCard
          label="Completed"
          value={loading ? "..." : completedReviews}
          variant="success"
          subtext="Diff & metadata saved"
        />
        <MetricCard
          label="Failed"
          value={loading ? "..." : failedReviews}
          variant="danger"
          subtext="Errors logged"
        />
      </div>

      {/* Recent Pull Requests */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Recent Pull Requests</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Live pull request events received via GitHub webhooks.
            </p>
          </div>
          <Link
            href="/pull-requests"
            className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all ({totalPRs}) &rarr;
          </Link>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm">Loading recent PRs...</div>
        ) : pullRequests.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-sm">No pull requests received yet.</p>
            <p className="text-xs text-slate-600 mt-1">
              Send a GitHub webhook to <code className="text-slate-400">/api/v1/webhooks/github</code> to
              ingest a Pull Request.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-semibold uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Repository</th>
                  <th className="px-6 py-3">PR</th>
                  <th className="px-6 py-3">Title</th>
                  <th className="px-6 py-3">Author</th>
                  <th className="px-6 py-3">PR State</th>
                  <th className="px-6 py-3">Review Job</th>
                  <th className="px-6 py-3 text-right">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {pullRequests.slice(0, 10).map((pr) => (
                  <tr key={pr.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 font-sans font-medium text-slate-200">
                      {pr.repository?.full_name || "Repository"}
                    </td>
                    <td className="px-6 py-4 text-blue-400 font-semibold">#{pr.number}</td>
                    <td className="px-6 py-4 font-sans text-slate-300 max-w-xs truncate">
                      <Link
                        href={`/pull-requests/${pr.id}`}
                        className="hover:text-blue-400 transition-colors hover:underline"
                      >
                        {pr.title}
                      </Link>
                      {pr.is_draft && (
                        <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                          Draft
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-400">@{pr.author_login}</td>
                    <td className="px-6 py-4">
                      <StatusBadge status={pr.state} type="pr" />
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={pr.latest_review_status} type="job" />
                    </td>
                    <td className="px-6 py-4 text-right text-slate-500">
                      {new Date(pr.updated_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
