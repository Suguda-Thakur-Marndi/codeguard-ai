"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Phase1Notice } from "../../components/Phase1Notice";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { PullRequest } from "../../lib/types";

export default function PullRequestsPage() {
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [filterState, setFilterState] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPRs() {
      try {
        setLoading(true);
        const stateParam = filterState === "all" ? undefined : filterState;
        const res = await api.getPullRequests(1, 100, undefined, stateParam);
        setPullRequests(res.items);
      } catch (err: any) {
        setError(err.message || "Failed to load pull requests");
      } finally {
        setLoading(false);
      }
    }
    loadPRs();
  }, [filterState]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Pull Requests</h1>
          <p className="text-sm text-slate-400 mt-1">
            Pull requests synchronized through GitHub webhooks.
          </p>
        </div>

        {/* State Filters */}
        <div className="flex items-center space-x-2 bg-slate-900 p-1 rounded-lg border border-slate-800">
          {["all", "open", "closed"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterState(s)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors ${
                filterState === s
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <Phase1Notice />

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Pull Requests ({pullRequests.length})</h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm">Loading PRs...</div>
        ) : pullRequests.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-sm">No pull requests match filter &ldquo;{filterState}&rdquo;.</p>
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
                  <th className="px-6 py-3">State</th>
                  <th className="px-6 py-3">Review Status</th>
                  <th className="px-6 py-3 text-right">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {pullRequests.map((pr) => (
                  <tr key={pr.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 font-sans font-medium text-slate-200">
                      {pr.repository?.full_name || "Repository"}
                    </td>
                    <td className="px-6 py-4 text-blue-400 font-semibold">#{pr.number}</td>
                    <td className="px-6 py-4 font-sans text-slate-300 max-w-sm truncate">
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
                      {new Date(pr.created_at).toLocaleDateString()}
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
