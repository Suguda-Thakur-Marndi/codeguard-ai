"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { DiffViewer } from "../../../components/DiffViewer";
import { StatusBadge } from "../../../components/StatusBadge";
import { api } from "../../../lib/api";
import {
  ASTChunk,
  ApprovalRequest,
  ChangedLineIndexData,
  DiffFile,
  GitHubReviewPublication,
  PullRequest,
  RelevantContext,
  ReviewArtifact,
  ReviewFinding,
  ReviewJob,
  VerificationSummary,
} from "../../../lib/types";

export default function PullRequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const prId = resolvedParams.id;

  const [pr, setPr] = useState<PullRequest | null>(null);
  const [reviewJobs, setReviewJobs] = useState<ReviewJob[]>([]);
  const [artifacts, setArtifacts] = useState<ReviewArtifact[]>([]);
  const [parsedDiffFiles, setParsedDiffFiles] = useState<DiffFile[]>([]);
  const [astChunks, setAstChunks] = useState<ASTChunk[]>([]);
  const [changedLineIndex, setChangedLineIndex] = useState<ChangedLineIndexData | null>(null);
  const [contextMap, setContextMap] = useState<Record<string, RelevantContext>>({});
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);

  // Phase 5 Governance & Publishing State
  const [publication, setPublication] = useState<GitHubReviewPublication | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [findings, setFindings] = useState<ReviewFinding[]>([]);
  const [verificationSummary, setVerificationSummary] = useState<VerificationSummary | null>(null);
  const [expandedEvidenceId, setExpandedEvidenceId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"findings_governance" | "intelligence" | "diff" | "metadata">("findings_governance");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadPRDetails() {
    try {
      setLoading(true);
      const [prData, reviewsData] = await Promise.all([
        api.getPullRequest(prId),
        api.getPullRequestReviews(prId, 1, 20),
      ]);
      setPr(prData);
      setReviewJobs(reviewsData.items);

      if (reviewsData.items.length > 0) {
        const latestJob = reviewsData.items[0];

        // Fetch Phase 4 & Phase 5 details in parallel
        const [arts, pubData, appsData, findingsData, verifData] = await Promise.all([
          api.getReviewJobArtifacts(latestJob.id).catch(() => []),
          api.getReviewJobPublication(latestJob.id).catch(() => null),
          api.getApprovals(1, 20, undefined, undefined).catch(() => ({ items: [] })),
          api.getReviewJobFindings(latestJob.id).catch(() => []),
          api.getVerificationSummary(latestJob.id).catch(() => null),
        ]);

        setArtifacts(arts);
        setPublication(pubData);
        setApprovals((appsData.items || []).filter((a) => a.pull_request_id === prId || a.review_job_id === latestJob.id));
        setFindings(findingsData);
        setVerificationSummary(verifData);

        const parsedDiffArt = arts.find((a) => a.artifact_type === "PARSED_DIFF");
        if (parsedDiffArt) {
          try {
            const files: DiffFile[] = JSON.parse(parsedDiffArt.content);
            setParsedDiffFiles(files);
            if (files.length > 0) setSelectedFile(files[0].file_path);
          } catch (e) {
            console.error("Error parsing PARSED_DIFF:", e);
          }
        }

        const chunksArt = arts.find((a) => a.artifact_type === "AST_CHUNKS");
        if (chunksArt) {
          try {
            const chunks: ASTChunk[] = JSON.parse(chunksArt.content);
            setAstChunks(chunks);
            if (chunks.length > 0) setSelectedChunkId(chunks[0].id);
          } catch (e) {
            console.error("Error parsing AST_CHUNKS:", e);
          }
        }

        const lineIdxArt = arts.find((a) => a.artifact_type === "CHANGED_LINE_INDEX");
        if (lineIdxArt) {
          try {
            setChangedLineIndex({ index: JSON.parse(lineIdxArt.content) });
          } catch (e) {
            console.error("Error parsing CHANGED_LINE_INDEX:", e);
          }
        }

        const ctxArt = arts.find((a) => a.artifact_type === "CONTEXT_MAP");
        if (ctxArt) {
          try {
            setContextMap(JSON.parse(ctxArt.content));
          } catch (e) {
            console.error("Error parsing CONTEXT_MAP:", e);
          }
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load pull request details");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPRDetails();
  }, [prId]);

  const latestJob = reviewJobs[0];

  async function handleRequestApproval(findingId?: string, action: string = "COMMENT") {
    if (!latestJob) return;
    try {
      setActionLoading("request_approval");
      await api.requestJobApproval(latestJob.id, findingId, action);
      await loadPRDetails();
    } catch (err: any) {
      alert(`Approval request failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  }

  async function handlePublish(action: string = "COMMENT") {
    if (!latestJob) return;
    try {
      setActionLoading("publishing");
      await api.publishReviewJob(latestJob.id, action);
      await loadPRDetails();
    } catch (err: any) {
      alert(`Publishing failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-500 font-mono text-sm animate-pulse">
        Loading Pull Request, Verification & Governance State...
      </div>
    );
  }

  if (error || !pr) {
    return (
      <div className="p-8 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300">
        <h2 className="text-lg font-bold">Error</h2>
        <p className="text-sm mt-1">{error || "Pull request not found."}</p>
        <Link href="/pull-requests" className="inline-block mt-4 text-xs text-blue-400 underline">
          &larr; Back to Pull Requests
        </Link>
      </div>
    );
  }

  // 4-Stage Stepper Calculation
  const hasAnalysis = Boolean(latestJob && ["COMPLETED", "PARTIAL"].includes(latestJob.status));
  const hasVerification = Boolean(verificationSummary && verificationSummary.verified_count > 0);
  const pendingApprovals = approvals.filter((a) => a.status === "PENDING");
  const approvedApprovals = approvals.filter((a) => a.status === "APPROVED");
  const isApprovalRequired = publication?.status === "APPROVAL_REQUIRED" || pendingApprovals.length > 0;
  const isApproved = approvedApprovals.length > 0 || (hasVerification && !isApprovalRequired);
  const isPublished = publication?.status === "PUBLISHED";
  const isPublishing = publication?.status === "PUBLISHING";
  const isStale = publication?.status === "STALE";

  const diffArtifact = artifacts.find((a) => a.artifact_type === "DIFF");
  const metaArtifact = artifacts.find((a) => a.artifact_type === "PR_METADATA");

  const fileChunks = astChunks.filter((c) => !selectedFile || c.file_path === selectedFile);
  const selectedChunk = astChunks.find((c) => c.id === selectedChunkId) || fileChunks[0];
  const chunkContext = selectedChunk ? contextMap[selectedChunk.symbol_name] : null;

  const publishableFindings = findings.filter(
    (f) =>
      f.status === "PUBLISHABLE" ||
      f.status === "VALIDATED" ||
      f.status === "EXECUTION_VERIFIED" ||
      f.status === "PUBLISHED"
  );
  const criticalCount = publishableFindings.filter((f) => f.severity === "CRITICAL").length;
  const highCount = publishableFindings.filter((f) => f.severity === "HIGH").length;
  const medCount = publishableFindings.filter((f) => f.severity === "MEDIUM").length;
  const secCount = publishableFindings.filter((f) => f.category === "SECURITY").length;
  const bugCount = publishableFindings.filter((f) => f.category === "BUG").length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div>
        <Link
          href="/pull-requests"
          className="text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors inline-flex items-center mb-3"
        >
          &larr; Back to Pull Requests
        </Link>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="text-2xl font-bold text-white tracking-tight">{pr.title}</span>
              <span className="text-xl font-bold text-slate-500 font-mono">#{pr.number}</span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Opened by <span className="text-slate-200 font-medium">@{pr.author_login}</span> in{" "}
              <span className="text-slate-200 font-medium">{pr.repository?.full_name}</span>
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <StatusBadge status={pr.state} type="pr" />
            {pr.is_draft && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                Draft
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 4-Stage Governance Stepper */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-4 flex items-center justify-between">
          <span>End-to-End Governance Pipeline</span>
          <span className="text-indigo-400 font-semibold">Zero-Trust MCP Control</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {/* Stage 1: AI Analysis */}
          <div className={`p-3 rounded-lg border ${hasAnalysis ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase font-mono">1. AI Analysis</span>
              <span className="text-sm font-bold">{hasAnalysis ? "✓" : "○"}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {hasAnalysis ? "Multi-agent LangGraph executed" : "Pending review analysis"}
            </div>
          </div>

          {/* Stage 2: Verification */}
          <div className={`p-3 rounded-lg border ${hasVerification ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase font-mono">2. Verification</span>
              <span className="text-sm font-bold">{hasVerification ? "✓" : "○"}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {hasVerification ? `${publishableFindings.length} findings verified publishable` : "Adversarial judge validation"}
            </div>
          </div>

          {/* Stage 3: Human Approval */}
          <div className={`p-3 rounded-lg border ${isApproved ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : isApprovalRequired ? "bg-amber-500/10 border-amber-500/30 text-amber-300 animate-pulse" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase font-mono">3. Human Approval</span>
              <span className="text-sm font-bold">{isApproved ? "✓" : isApprovalRequired ? "⏳" : "—"}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {isApproved ? "Authorized by Reviewer" : isApprovalRequired ? "Awaiting Human Sign-off" : "Not Required"}
            </div>
          </div>

          {/* Stage 4: GitHub Publication */}
          <div className={`p-3 rounded-lg border ${isPublished ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-300" : isPublishing ? "bg-blue-500/10 border-blue-500/30 text-blue-300 animate-pulse" : isStale ? "bg-rose-500/10 border-rose-500/30 text-rose-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase font-mono">4. GitHub Publication</span>
              <span className="text-sm font-bold">{isPublished ? "✓" : isPublishing ? "..." : isStale ? "✕" : "○"}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {isPublished ? `Atomic review #${publication?.github_review_id}` : isPublishing ? "Submitting review..." : isStale ? "Stale HEAD SHA detected" : "Ready to publish"}
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex space-x-6">
            <button
              onClick={() => setActiveTab("findings_governance")}
              className={`text-sm font-medium pb-2 -mb-3 transition-colors border-b-2 flex items-center space-x-2 ${
                activeTab === "findings_governance"
                  ? "border-indigo-500 text-indigo-400 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>Verified Findings & Publishing</span>
              {publishableFindings.length > 0 && (
                <span className="px-1.5 py-0.2 bg-emerald-950 text-emerald-300 border border-emerald-800 rounded-full text-[10px]">
                  {publishableFindings.length} publishable
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("intelligence")}
              className={`text-sm font-medium pb-2 -mb-3 transition-colors border-b-2 flex items-center space-x-2 ${
                activeTab === "intelligence"
                  ? "border-indigo-500 text-indigo-400 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>Code Intelligence</span>
              {astChunks.length > 0 && (
                <span className="px-1.5 py-0.2 bg-indigo-950 text-indigo-300 border border-indigo-800 rounded-full text-[10px]">
                  {astChunks.length} chunks
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("diff")}
              className={`text-sm font-medium pb-2 -mb-3 transition-colors border-b-2 ${
                activeTab === "diff"
                  ? "border-indigo-500 text-indigo-400 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Unified Diff ({diffArtifact ? "Available" : "None"})
            </button>
            <button
              onClick={() => setActiveTab("metadata")}
              className={`text-sm font-medium pb-2 -mb-3 transition-colors border-b-2 ${
                activeTab === "metadata"
                  ? "border-indigo-500 text-indigo-400 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              PR Metadata
            </button>
          </div>
        </div>

        <div className="p-6">
          {activeTab === "findings_governance" ? (
            <div className="space-y-6">
              {/* Publication Status & Action Bar */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">GitHub Publication State:</span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        isPublished
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : isPublishing
                          ? "bg-blue-500/10 text-blue-400 border border-blue-500/30 animate-pulse"
                          : isApprovalRequired
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                          : isStale
                          ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {publication?.status || "UNPUBLISHED"}
                    </span>
                  </div>

                  {publication?.github_review_id && (
                    <div className="text-xs text-slate-400 font-mono">
                      GitHub Review ID: <span className="text-white font-bold">{publication.github_review_id}</span> | Comments:{" "}
                      <span className="text-indigo-400 font-bold">{publication.comment_count}</span> | Published:{" "}
                      <span className="text-slate-300">
                        {publication.published_at ? new Date(publication.published_at).toLocaleString() : "—"}
                      </span>
                    </div>
                  )}

                  {isApprovalRequired && (
                    <div className="text-xs text-amber-400">
                      High or critical findings require reviewer sign-off before publishing.
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {isApprovalRequired && (
                    <Link
                      href="/approvals"
                      className="px-4 py-2 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white shadow transition-colors"
                    >
                      Awaiting Human Approval &rarr;
                    </Link>
                  )}

                  {publishableFindings.length > 0 && !isPublished && !isApprovalRequired && (
                    <>
                      <button
                        onClick={() => handleRequestApproval(undefined, "REQUEST_CHANGES")}
                        disabled={actionLoading !== null}
                        className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
                      >
                        Request Changes Gate
                      </button>
                      <button
                        onClick={() => handlePublish("COMMENT")}
                        disabled={actionLoading !== null}
                        className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition-colors disabled:opacity-50"
                      >
                        {actionLoading === "publishing" ? "Publishing..." : "Publish to GitHub"}
                      </button>
                    </>
                  )}

                  {isPublished && (
                    <span className="px-3 py-1.5 rounded-lg text-xs font-mono bg-emerald-950 border border-emerald-800 text-emerald-300">
                      Published to GitHub ✓
                    </span>
                  )}
                </div>
              </div>

              {/* Verified Findings Summary Box */}
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
                  CodeGuard AI Review Summary
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs font-mono">
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                    <span className="text-rose-400 block font-bold">Critical: {criticalCount}</span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                    <span className="text-amber-400 block font-bold">High: {highCount}</span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                    <span className="text-yellow-400 block font-bold">Medium: {medCount}</span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                    <span className="text-indigo-400 block font-bold">Security: {secCount}</span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                    <span className="text-sky-400 block font-bold">Functional: {bugCount}</span>
                  </div>
                </div>
              </div>

              {/* Publishable Findings List */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Verified Publishable Findings ({publishableFindings.length})
                </h3>

                {publishableFindings.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 font-mono text-xs bg-slate-950/40 rounded-xl border border-slate-800">
                    No verified publishable findings. All candidates were filtered or rejected by the adversarial judge.
                  </div>
                ) : (
                  publishableFindings.map((finding) => {
                    const isExpanded = expandedEvidenceId === finding.id;
                    return (
                      <div
                        key={finding.id}
                        className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3 hover:border-slate-700 transition-colors"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                                  finding.severity === "CRITICAL"
                                    ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                                    : finding.severity === "HIGH"
                                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                    : "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                                }`}
                              >
                                {finding.severity}
                              </span>
                              <span className="font-semibold text-white text-sm">{finding.title}</span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                PUBLISHABLE
                              </span>
                            </div>
                            <div className="text-xs text-slate-400 font-mono">
                              {finding.file_path}:{finding.start_line}{" "}
                              <span className="text-slate-600">|</span> Category:{" "}
                              <span className="text-slate-300">{finding.category}</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setExpandedEvidenceId(isExpanded ? null : finding.id)}
                              className="px-3 py-1 rounded text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800"
                            >
                              {isExpanded ? "Hide Evidence" : "View Evidence"}
                            </button>
                            {!isPublished && (
                              <button
                                onClick={() => handleRequestApproval(finding.id, "COMMENT")}
                                className="px-3 py-1 rounded text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 border border-indigo-500/30"
                              >
                                Request Approval
                              </button>
                            )}
                          </div>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed font-sans">{finding.description}</p>

                        {finding.recommendation && (
                          <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 text-xs font-mono space-y-1">
                            <span className="text-emerald-400 font-bold block">Recommendation:</span>
                            <span className="text-slate-300 whitespace-pre-wrap">{finding.recommendation}</span>
                          </div>
                        )}

                        {isExpanded && (
                          <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs font-mono space-y-2">
                            <span className="text-indigo-400 font-bold block">Adversarial Verification Data:</span>
                            <div className="text-slate-300">Confidence: {finding.confidence}</div>
                            <div className="text-slate-300">Finding UUID: {finding.id}</div>
                            <div className="text-slate-400">Agent: {finding.agent_name}</div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : activeTab === "intelligence" ? (
            parsedDiffFiles.length === 0 ? (
              <div className="p-12 text-center text-slate-500 text-xs font-mono">
                No code intelligence artifacts generated yet for this PR. Run review worker to process diff.
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3">
                    Changed Files ({parsedDiffFiles.length})
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {parsedDiffFiles.map((file) => {
                      const isSelected = selectedFile === file.file_path;
                      return (
                        <button
                          key={file.file_path}
                          onClick={() => {
                            setSelectedFile(file.file_path);
                            const firstMatch = astChunks.find((c) => c.file_path === file.file_path);
                            if (firstMatch) setSelectedChunkId(firstMatch.id);
                          }}
                          className={`p-3 rounded-lg text-left transition-all border font-mono text-xs ${
                            isSelected
                              ? "bg-slate-800 border-indigo-500 shadow-md shadow-indigo-950/30"
                              : "bg-slate-950 border-slate-800 hover:border-slate-700"
                          }`}
                        >
                          <div className="font-semibold text-white truncate">{file.file_path}</div>
                          <div className="flex items-center space-x-3 mt-2 text-[11px]">
                            <span className="text-indigo-400 font-mono font-bold">{file.change_type}</span>
                            <span className="text-slate-500 font-mono">{file.hunks?.length || 0} hunks</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="border-t border-slate-800 pt-6">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="space-y-3">
                      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Semantic Chunks ({fileChunks.length})
                      </div>
                      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                        {fileChunks.map((chunk) => {
                          const isSelected = selectedChunk?.id === chunk.id;
                          return (
                            <button
                              key={chunk.id}
                              onClick={() => setSelectedChunkId(chunk.id)}
                              className={`w-full p-2.5 rounded text-left border text-xs font-mono transition-colors ${
                                isSelected
                                  ? "bg-indigo-950/60 border-indigo-600 text-indigo-200"
                                  : "bg-slate-950 border-slate-800 hover:bg-slate-900 text-slate-400"
                              }`}
                            >
                              <div className="font-bold truncate">{chunk.symbol_name}</div>
                              <div className="text-[10px] text-slate-500 mt-1">
                                {chunk.node_type} (L{chunk.start_line}-{chunk.end_line})
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="lg:col-span-2 space-y-4">
                      {selectedChunk ? (
                        <>
                          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-sm font-bold text-white">
                                {selectedChunk.symbol_name}
                              </span>
                              <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-indigo-400 font-mono border border-slate-700">
                                {selectedChunk.node_type}
                              </span>
                            </div>
                            <div className="text-xs font-mono text-slate-400">
                              Lines {selectedChunk.start_line} to {selectedChunk.end_line} in {selectedChunk.file_path}
                            </div>
                          </div>

                          {chunkContext && chunkContext.ranked_items.length > 0 && (
                            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
                              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                Ranked Architectural Context
                              </div>
                              <div className="space-y-2">
                                {chunkContext.ranked_items.map((item, idx) => (
                                  <div
                                    key={idx}
                                    className="p-2.5 rounded bg-slate-900 border border-slate-800 flex items-center justify-between text-xs font-mono"
                                  >
                                    <div>
                                      <span className="text-slate-200 font-semibold mr-2">{item.name}</span>
                                      <span className="text-slate-500 text-[11px]">({item.file_path})</span>
                                    </div>
                                    <span className="px-2 py-0.5 rounded bg-indigo-950 border border-indigo-800 text-indigo-300 font-bold">
                                      {(item.relevance_score * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          <div>
                            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                              Semantic AST Source
                            </div>
                            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 max-h-48 overflow-y-auto font-mono text-xs text-slate-300 whitespace-pre">
                              {selectedChunk.source_code}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="text-center text-slate-500 text-xs font-mono py-12">
                          Select a semantic chunk to inspect.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          ) : activeTab === "diff" ? (
            diffArtifact ? (
              <DiffViewer diffText={diffArtifact.content} />
            ) : (
              <div className="p-12 text-center text-slate-500 text-xs font-mono">
                No diff artifact recorded yet.
              </div>
            )
          ) : metaArtifact ? (
            <div className="space-y-4">
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-xs">
                <pre className="text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(metaArtifact.metadata_json, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500 text-xs font-mono">
              No metadata artifact recorded.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
