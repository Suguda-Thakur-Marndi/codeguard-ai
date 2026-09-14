"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Repository, RepositoryIndex } from "../../lib/types";

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [indices, setIndices] = useState<Record<string, RepositoryIndex | null>>({});
  const [loading, setLoading] = useState(true);
  const [indexingState, setIndexingState] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRepos();
  }, []);

  async function loadRepos() {
    try {
      setLoading(true);
      const res = await api.getRepositories(1, 100);
      setRepositories(res.items);

      // Fetch index status for all repositories in parallel
      const indexResults = await Promise.allSettled(
        res.items.map(async (repo) => {
          try {
            const idx = await api.getRepositoryIndex(repo.id);
            return { repoId: repo.id, index: idx };
          } catch {
            return { repoId: repo.id, index: null };
          }
        })
      );

      const indexMap: Record<string, RepositoryIndex | null> = {};
      indexResults.forEach((result) => {
        if (result.status === "fulfilled" && result.value) {
          indexMap[result.value.repoId] = result.value.index;
        }
      });
      setIndices(indexMap);
    } catch (err: any) {
      setError(err.message || "Failed to load repositories");
    } finally {
      setLoading(false);
    }
  }

  async function handleIndexRepository(repoId: string) {
    try {
      setIndexingState((prev) => ({ ...prev, [repoId]: true }));
      const newIdx = await api.triggerRepositoryIndex(repoId);
      setIndices((prev) => ({ ...prev, [repoId]: newIdx }));
    } catch (err: any) {
      alert(`Indexing failed: ${err.message || "Unknown error"}`);
    } finally {
      setIndexingState((prev) => ({ ...prev, [repoId]: false }));
    }
  }

  function getStatusBadge(status?: string | null) {
    switch (status) {
      case "READY":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />
            READY
          </span>
        );
      case "INDEXING":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-950/80 text-sky-400 border border-sky-800">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 mr-1.5 animate-ping" />
            INDEXING
          </span>
        );
      case "PARTIAL":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-800">
            PARTIAL
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-400 border border-rose-800">
            FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            NOT_INDEXED
          </span>
        );
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Connected Repositories</h1>
        <p className="text-sm text-slate-400 mt-1">
          Repositories indexed with Tree-sitter Code Intelligence and repository dependency graphs.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Repository Code Intelligence ({repositories.length})</h2>
          <button
            onClick={loadRepos}
            className="text-xs px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 transition"
          >
            Refresh Status
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm">Loading repository indices...</div>
        ) : repositories.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-sm">No repositories connected yet.</p>
            <p className="text-xs text-slate-600 mt-1">
              Install CodeGuard AI GitHub App or trigger a review job.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-semibold uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Repository</th>
                  <th className="px-6 py-3">Index Status</th>
                  <th className="px-6 py-3">Indexed Commit</th>
                  <th className="px-6 py-3">Files Indexed</th>
                  <th className="px-6 py-3">Symbols / Refs</th>
                  <th className="px-6 py-3">Last Index Time</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {repositories.map((repo) => {
                  const idx = indices[repo.id];
                  const isBusy = indexingState[repo.id];

                  return (
                    <tr key={repo.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-4 font-sans">
                        <div className="font-semibold text-slate-200">{repo.full_name}</div>
                        <div className="text-xs text-slate-400 font-mono">@{repo.owner} • {repo.default_branch}</div>
                      </td>
                      <td className="px-6 py-4">
                        {getStatusBadge(idx?.status)}
                      </td>
                      <td className="px-6 py-4 font-mono text-slate-400">
                        {idx?.commit_sha ? (
                          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-indigo-300">
                            {idx.commit_sha.slice(0, 7)}
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-slate-300">
                        {idx ? (
                          <div>
                            <span className="text-emerald-400">{idx.files_processed}</span> processed
                            {idx.files_failed > 0 && (
                              <span className="text-rose-400 ml-1">({idx.files_failed} failed)</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-slate-400">
                        {idx ? (
                          <span>
                            <span className="text-sky-400">{idx.total_symbols ?? 0}</span> syms /{" "}
                            <span className="text-purple-400">{idx.total_references ?? 0}</span> refs
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                        {idx?.index_completed_at
                          ? new Date(idx.index_completed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                          : idx?.index_started_at
                          ? "In progress..."
                          : "Never"}
                      </td>
                      <td className="px-6 py-4 text-right font-sans">
                        <button
                          onClick={() => handleIndexRepository(repo.id)}
                          disabled={isBusy || idx?.status === "INDEXING"}
                          className="px-3 py-1.5 rounded text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white transition shadow-sm"
                        >
                          {isBusy || idx?.status === "INDEXING" ? "Indexing..." : "Index Repository"}
                        </button>
                      </td>
                    </tr>
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
