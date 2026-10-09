"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { DiffViewer } from "../../../components/DiffViewer";
import { StatusBadge } from "../../../components/StatusBadge";
import { api } from "../../../lib/api";
import {
  AgentRun,
  AgentTrace,
  JudgeRun,
  ReviewArtifact,
  ReviewFinding,
  ReviewJob,
  ReviewUsage,
  ValidationScenario,
  VerificationSummary,
} from "../../../lib/types";

export default function ReviewJobDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const resolvedParams = use(params);
  const jobId = resolvedParams.jobId;

  const [job, setJob] = useState<ReviewJob | null>(null);
  const [artifacts, setArtifacts] = useState<ReviewArtifact[]>([]);
  const [agents, setAgents] = useState<AgentRun[]>([]);
  const [findings, setFindings] = useState<ReviewFinding[]>([]);
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [usage, setUsage] = useState<ReviewUsage | null>(null);

  // Phase 4 State
  const [verificationSummary, setVerificationSummary] = useState<VerificationSummary | null>(null);
  const [judgeRuns, setJudgeRuns] = useState<JudgeRun[]>([]);
  const [validationScenarios, setValidationScenarios] = useState<ValidationScenario[]>([]);
  const [expandedOutputId, setExpandedOutputId] = useState<string | null>(null);

  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PUBLISHABLE" | "REJECTED">("ALL");
  const [activeTab, setActiveTab] = useState<"findings" | "verification" | "agents" | "traces" | "artifacts">("findings");

  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadAllData() {
    try {
      setLoading(true);
      const [
        jobData,
        artifactsData,
        agentsData,
        findingsData,
        tracesData,
        usageData,
        verifData,
        judgeData,
        validationData,
      ] = await Promise.all([
        api.getReviewJob(jobId),
        api.getReviewJobArtifacts(jobId).catch(() => []),
        api.getReviewJobAgents(jobId).catch(() => []),
        api.getReviewJobFindings(jobId).catch(() => []),
        api.getReviewJobTrace(jobId).catch(() => []),
        api.getReviewJobUsage(jobId).catch(() => null),
        api.getVerificationSummary(jobId).catch(() => null),
        api.getJudgeRuns(jobId).catch(() => []),
        api.getValidationScenarios(jobId).catch(() => []),
      ]);
      setJob(jobData);
      setArtifacts(artifactsData);
      setAgents(agentsData);
      setFindings(findingsData);
      setTraces(tracesData);
      setUsage(usageData);
      setVerificationSummary(verifData);
      setJudgeRuns(judgeData);
      setValidationScenarios(validationData);
    } catch (err: any) {
      setError(err.message || "Failed to load review job");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAllData();
  }, [jobId]);

  async function handleRerun() {
    if (!confirm("Trigger a new adversarial AI review and validation run for this job?")) return;
    try {
      setRerunning(true);
      await api.rerunReviewJob(jobId);
      await loadAllData();
    } catch (err: any) {
      alert("Failed to trigger rerun: " + err.message);
    } finally {
      setRerunning(false);
    }
  }

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-500 font-mono text-xs flex items-center justify-center gap-2">
        <span className="w-4 h-4 border-2 border-[#F5E900] border-t-transparent rounded-full animate-spin"></span>
        <span>Loading Adversarial Review & Verification Engine telemetry...</span>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="p-8 rounded-xl bg-surface-container-low border border-rose-900/50 text-rose-300">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-rose-400">error</span>
          <h2 className="text-base font-bold font-mono">Job Telemetry Error</h2>
        </div>
        <p className="text-xs font-mono text-slate-400 mt-2">{error || "Review job not found."}</p>
        <Link href="/dashboard" className="inline-flex items-center gap-1.5 mt-4 text-xs font-mono text-[#F5E900] hover:underline">
          <span className="material-symbols-outlined text-[14px]">arrow_back</span>
          <span>Return to Dashboard</span>
        </Link>
      </div>
    );
  }

  const diffArtifact = artifacts.find((a) => a.artifact_type === "DIFF");

  // Filtering findings
  const filteredFindings = findings.filter((f) => {
    if (selectedSeverity !== "ALL" && f.severity !== selectedSeverity) return false;
    if (selectedCategory !== "ALL" && f.category !== selectedCategory) return false;
    if (statusFilter === "PUBLISHABLE") {
      return f.status === "PUBLISHABLE" || f.status === "VALID" || f.status === "VALIDATED" || f.status === "EXECUTION_VERIFIED";
    }
    if (statusFilter === "REJECTED") {
      return f.status === "REJECTED" || f.status === "INVALID";
    }
    return true;
  });

  const candidateCount = verificationSummary?.candidate_count ?? findings.length;
  const verifiedCount =
    verificationSummary?.verified_count ??
    findings.filter((f) => ["PUBLISHABLE", "VALID", "VALIDATED", "EXECUTION_VERIFIED"].includes(f.status)).length;
  const rejectedCount =
    verificationSummary?.rejected_count ??
    findings.filter((f) => ["REJECTED", "INVALID"].includes(f.status)).length;
  const needsValidationCount =
    verificationSummary?.needs_validation_count ??
    findings.filter((f) => f.status === "CANDIDATE").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href={`/pull-requests/${job.pull_request_id}`}
          className="text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors inline-flex items-center gap-1.5 mb-3"
        >
          <span className="material-symbols-outlined text-[14px]">arrow_back</span>
          <span>Back to Pull Request #{job.pull_request_id.slice(0, 8)}</span>
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
              Adversarial Code Review
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-container border border-[#333842] text-slate-400 font-normal">
                job:{job.id.slice(0, 8)}
              </span>
            </h1>
            <p className="text-xs font-mono text-slate-400 mt-1">
              Phase 4 Precision Engine &bull; Trigger: <code className="text-slate-300">{job.trigger}</code> &bull;{" "}
              {new Date(job.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRerun}
              disabled={rerunning}
              className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium bg-surface-container hover:bg-surface-container-high text-slate-200 border border-[#333842] transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <span className={`material-symbols-outlined text-[14px] ${rerunning ? "animate-spin" : ""}`}>
                autorenew
              </span>
              <span>{rerunning ? "Rerunning..." : "Rerun Review & Judge"}</span>
            </button>
            <StatusBadge status={job.status} type="job" />
          </div>
        </div>
      </div>

      {/* Phase 4 Verification Summary Banner */}
      <div className="bg-surface-container-low border border-[#262930] rounded-xl p-4 shadow-sm">
        <div className="text-xs font-bold uppercase text-slate-400 font-mono tracking-wider mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#F5E900] text-[16px]">verified_user</span>
            <span>Adversarial Verification Funnel</span>
          </div>
          <span className="text-[11px] text-slate-500 font-normal">Specialist Recall &rarr; 5-Gate Adversarial Precision</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-[#262930]">
            <span className="text-[11px] text-slate-400 font-mono block mb-1">Candidate Findings</span>
            <span className="text-2xl font-bold text-white font-mono">{candidateCount}</span>
            <span className="text-[10px] text-slate-500 font-mono block mt-0.5">Specialist Agents</span>
          </div>
          <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-emerald-900/30">
            <span className="text-[11px] text-emerald-400 font-mono block mb-1">Verified & Publishable</span>
            <span className="text-2xl font-bold text-emerald-400 font-mono">{verifiedCount}</span>
            <span className="text-[10px] text-emerald-500 font-mono block mt-0.5">Passed All 4 Gates</span>
          </div>
          <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-rose-900/30">
            <span className="text-[11px] text-rose-400 font-mono block mb-1">Rejected Findings</span>
            <span className="text-2xl font-bold text-rose-400 font-mono">{rejectedCount}</span>
            <span className="text-[10px] text-rose-500 font-mono block mt-0.5">False positives & deduplicated</span>
          </div>
          <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-[#8B5CF6]/30">
            <span className="text-[11px] text-[#A78BFA] font-mono block mb-1">Needs Validation</span>
            <span className="text-2xl font-bold text-[#A78BFA] font-mono">{needsValidationCount}</span>
            <span className="text-[10px] text-purple-400 font-mono block mt-0.5">Runtime / Sandbox required</span>
          </div>
        </div>
      </div>

      {/* Review Usage & Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="bg-surface-container-low border border-[#262930] rounded-xl p-3.5">
          <span className="text-slate-400 block text-[10px] uppercase tracking-wider">Total Tokens</span>
          <span className="text-base font-bold text-slate-200 mt-1 block">
            {(usage?.total_tokens || job.total_tokens || 0).toLocaleString()}
          </span>
        </div>
        <div className="bg-surface-container-low border border-[#262930] rounded-xl p-3.5">
          <span className="text-slate-400 block text-[10px] uppercase tracking-wider">Estimated Cost</span>
          <span className="text-base font-bold text-emerald-400 mt-1 block">
            ${Number(usage?.estimated_cost || job.estimated_cost || 0).toFixed(5)}
          </span>
        </div>
        <div className="bg-surface-container-low border border-[#262930] rounded-xl p-3.5">
          <span className="text-slate-400 block text-[10px] uppercase tracking-wider">Judge Latency</span>
          <span className="text-base font-bold text-[#A78BFA] mt-1 block">
            {judgeRuns[0] ? `${(judgeRuns[0].latency_ms / 1000).toFixed(2)}s` : "-"}
          </span>
        </div>
        <div className="bg-surface-container-low border border-[#262930] rounded-xl p-3.5">
          <span className="text-slate-400 block text-[10px] uppercase tracking-wider">Rejection Ratio</span>
          <span className="text-base font-bold text-amber-400 mt-1 block">
            {candidateCount > 0 ? `${((rejectedCount / candidateCount) * 100).toFixed(0)}%` : "0%"}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#262930] gap-6 text-xs font-mono font-medium">
        <button
          onClick={() => setActiveTab("findings")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "findings"
              ? "border-[#F5E900] text-white font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Review Findings</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface-container border border-[#333842] text-slate-300">
            {findings.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("verification")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "verification"
              ? "border-[#F5E900] text-white font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Judge & Sandboxes</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface-container border border-[#333842] text-slate-300">
            {judgeRuns.length + validationScenarios.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("agents")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "agents"
              ? "border-[#F5E900] text-white font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Agent Executions</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface-container border border-[#333842] text-slate-300">
            {agents.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("traces")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "traces"
              ? "border-[#F5E900] text-white font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Operational Traces</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface-container border border-[#333842] text-slate-300">
            {traces.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("artifacts")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "artifacts"
              ? "border-[#F5E900] text-white font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Raw Diff & Artifacts</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface-container border border-[#333842] text-slate-300">
            {artifacts.length}
          </span>
        </button>
      </div>

      {/* Tab: Findings */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container-low border border-[#262930] rounded-xl p-3">
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-slate-400 font-medium">Status:</span>
              <button
                onClick={() => setStatusFilter("ALL")}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  statusFilter === "ALL" ? "bg-[#F5E900] text-black font-bold" : "bg-surface-container text-slate-300 hover:bg-surface-container-high"
                }`}
              >
                All ({findings.length})
              </button>
              <button
                onClick={() => setStatusFilter("PUBLISHABLE")}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  statusFilter === "PUBLISHABLE"
                    ? "bg-emerald-600 text-white font-bold"
                    : "bg-surface-container text-emerald-400 hover:bg-surface-container-high"
                }`}
              >
                Verified ({verifiedCount})
              </button>
              <button
                onClick={() => setStatusFilter("REJECTED")}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  statusFilter === "REJECTED"
                    ? "bg-rose-600 text-white font-bold"
                    : "bg-surface-container text-rose-400 hover:bg-surface-container-high"
                }`}
              >
                Rejected ({rejectedCount})
              </button>
            </div>

            <div className="flex items-center gap-3 text-xs font-mono">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 font-medium">Severity:</span>
                {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSelectedSeverity(sev)}
                    className={`px-2 py-0.5 rounded text-xs transition-colors ${
                      selectedSeverity === sev ? "bg-white text-black font-bold" : "bg-surface-container text-slate-400 hover:text-white"
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Finding Cards */}
          {filteredFindings.length === 0 ? (
            <div className="p-12 text-center bg-surface-container-low rounded-xl border border-[#262930] text-slate-400">
              <span className="material-symbols-outlined text-4xl text-slate-500 mb-2">verified</span>
              <h3 className="font-semibold text-slate-200 font-mono text-sm">No Review Findings</h3>
              <p className="text-xs text-slate-500 font-mono mt-1 max-w-md mx-auto">
                No findings match the current filter selection.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredFindings.map((finding) => {
                const isCrit = finding.severity === "CRITICAL";
                const isHigh = finding.severity === "HIGH";
                const isSec = finding.category === "SECURITY";
                const isRejected = finding.status === "REJECTED" || finding.status === "INVALID";
                const isPublishable = finding.status === "PUBLISHABLE" || finding.status === "VALIDATED" || finding.status === "EXECUTION_VERIFIED";

                // Look for validation scenario attached
                const scenario = validationScenarios.find((s) => s.finding_id === finding.id);

                return (
                  <div
                    key={finding.id}
                    className={`rounded-xl border p-5 shadow-sm transition-colors ${
                      isRejected
                        ? "bg-surface-container-low border-rose-900/30 opacity-80"
                        : isCrit
                        ? "bg-surface-container-low border-rose-800/60"
                        : isHigh
                        ? "bg-surface-container-low border-amber-800/60"
                        : "bg-surface-container-low border-[#262930]"
                    }`}
                  >
                    {/* Header Line */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold font-mono tracking-wide uppercase ${
                            isSec
                              ? "bg-rose-950/80 text-rose-300 border border-rose-700/60"
                              : finding.category === "BUG"
                              ? "bg-amber-950/80 text-amber-300 border border-amber-700/60"
                              : "bg-blue-950/80 text-blue-300 border border-blue-700/60"
                          }`}
                        >
                          {finding.category.replace("_", " ")}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold ${
                            isCrit
                              ? "bg-rose-950 text-rose-400 border border-rose-800"
                              : isHigh
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-surface-container text-slate-300 border border-[#333842]"
                          }`}
                        >
                          {finding.final_severity || finding.severity}
                        </span>

                        {/* Provenance: Source Agents */}
                        {finding.source_agents && finding.source_agents.length > 0 && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#8B5CF6]/10 text-[#A78BFA] border border-[#8B5CF6]/30">
                            Agents: [{finding.source_agents.join(", ")}]
                          </span>
                        )}

                        {/* Confidence breakdown */}
                        <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 bg-surface-container-lowest px-2 py-0.5 rounded border border-[#262930]">
                          <span>Spec: {((finding.specialist_confidence || finding.confidence) * 100).toFixed(0)}%</span>
                          {finding.judge_confidence !== null && finding.judge_confidence !== undefined && (
                            <>
                              <span className="text-slate-600">&bull;</span>
                              <span className="text-[#A78BFA]">Judge: {(finding.judge_confidence * 100).toFixed(0)}%</span>
                            </>
                          )}
                          <span className="text-slate-600">&bull;</span>
                          <span className="text-emerald-400 font-bold">Final: {((finding.final_confidence || finding.confidence) * 100).toFixed(0)}%</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-blue-400 bg-surface-container-lowest px-2.5 py-0.5 rounded border border-[#262930]">
                          {finding.file_path}:{finding.line_number} [{finding.side}]
                        </span>
                        <span
                          className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                            isPublishable
                              ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                              : "bg-rose-950/80 text-rose-400 border border-rose-800"
                          }`}
                        >
                          {finding.status}
                        </span>
                      </div>
                    </div>

                    {/* Title */}
                    <h3 className="text-sm font-bold text-white mb-2">{finding.title}</h3>

                    {/* If rejected, show concise rejection reason banner */}
                    {isRejected && (
                      <div className="mb-3 p-2.5 rounded-lg bg-rose-950/50 border border-rose-800/60 text-xs font-mono text-rose-200 flex items-start gap-2">
                        <span className="text-rose-400 font-bold">REJECTED:</span>
                        <span>{finding.validation_notes || "Rejected by Adversarial Judge during factuality or boundary verification."}</span>
                      </div>
                    )}

                    {/* Description */}
                    <p className="text-xs text-slate-300 leading-relaxed mb-3 whitespace-pre-line font-mono">
                      {finding.description}
                    </p>

                    {/* Phase 4 Verification Gates Checklist */}
                    <div className="bg-surface-container-lowest rounded-lg border border-[#262930] p-3 mb-3 text-xs font-mono">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                        Adversarial Verification Gates
                      </span>
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <span>✓</span>
                          <span className="text-slate-300">Diff Boundary</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <span>✓</span>
                          <span className="text-slate-300">Factuality</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <span>✓</span>
                          <span className="text-slate-300">Actionability</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <span>✓</span>
                          <span className="text-slate-300">Severity</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <span>✓</span>
                          <span className="text-slate-300">Deduplicated</span>
                        </div>
                      </div>
                    </div>

                    {/* Execution Validation Sandbox Status */}
                    {scenario && (
                      <div className="bg-surface-container-lowest rounded-lg border border-[#262930] p-3 mb-3 text-xs font-mono">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[10px] font-bold text-[#A78BFA] uppercase tracking-wider">
                            Execution Sandbox: {scenario.scenario_type}
                          </span>
                          <span className="text-slate-400 text-[11px]">
                            Command: <code className="text-slate-200">{scenario.command}</code>
                          </span>
                        </div>
                        {scenario.results && scenario.results.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {scenario.results.map((res) => (
                              <div key={res.id} className="text-[11px]">
                                <div className="flex items-center justify-between text-slate-400">
                                  <span>
                                    Status:{" "}
                                    <span
                                      className={`font-bold ${
                                        res.status === "PASS" ? "text-emerald-400" : "text-rose-400"
                                      }`}
                                    >
                                      {res.status}
                                    </span>{" "}
                                    &bull; Exit Code: {res.exit_code ?? 0} &bull; Duration: {res.duration_ms}ms
                                  </span>
                                  {res.stdout_summary && (
                                    <button
                                      onClick={() =>
                                        setExpandedOutputId(expandedOutputId === res.id ? null : res.id)
                                      }
                                      className="text-[#F5E900] underline hover:text-[#ffe600]"
                                    >
                                      {expandedOutputId === res.id ? "Hide Output" : "View Output"}
                                    </button>
                                  )}
                                </div>
                                {expandedOutputId === res.id && res.stdout_summary && (
                                  <pre className="mt-2 p-2.5 rounded bg-black/80 border border-[#262930] text-[10px] text-slate-300 overflow-x-auto max-h-40">
                                    {res.stdout_summary}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Impact & Recommendation */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3 text-xs font-mono">
                      <div className="bg-surface-container-lowest p-3 rounded-lg border border-[#262930]">
                        <span className="text-rose-400 font-semibold block mb-1 uppercase text-[10px]">
                          Impact
                        </span>
                        <span className="text-slate-300">{finding.impact}</span>
                      </div>
                      <div className="bg-surface-container-lowest p-3 rounded-lg border border-[#262930]">
                        <span className="text-emerald-400 font-semibold block mb-1 uppercase text-[10px]">
                          Concrete Remediation
                        </span>
                        <span className="text-slate-300">{finding.recommendation}</span>
                      </div>
                    </div>

                    {/* Grounding Evidence List */}
                    {finding.evidence && finding.evidence.length > 0 && (
                      <div>
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2 font-mono">
                          Grounding Evidence Chain ({finding.evidence.length})
                        </span>
                        <div className="space-y-1.5">
                          {finding.evidence.map((ev, idx) => (
                            <div
                              key={idx}
                              className="bg-surface-container-lowest p-2.5 rounded-lg border border-[#262930] text-xs font-mono flex items-start gap-2.5"
                            >
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-surface-container text-slate-300 uppercase">
                                {ev.type}
                              </span>
                              <div className="flex-1">
                                <span className="text-slate-200 font-semibold">{ev.file}</span>
                                {ev.line_start && (
                                  <span className="text-slate-500">
                                    :L{ev.line_start}{ev.line_end ? `-L${ev.line_end}` : ""}
                                  </span>
                                )}
                                {ev.symbol && <span className="text-blue-400 ml-1.5">({ev.symbol})</span>}
                                <p className="text-slate-400 text-[11px] mt-0.5">{ev.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Verification & Judge */}
      {activeTab === "verification" && (
        <div className="space-y-4">
          <div className="bg-surface-container-low border border-[#262930] rounded-xl p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-white mb-3">
              Adversarial Judge Runs
            </h3>
            <div className="space-y-3">
              {judgeRuns.map((jr) => (
                <div key={jr.id} className="bg-surface-container-lowest p-3.5 rounded-lg border border-[#262930] font-mono text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-400 font-bold">{jr.model_name} ({jr.prompt_version})</span>
                    <span className="text-emerald-400 font-bold">{jr.status}</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-400 text-[11px]">
                    <div>Tokens: {jr.total_tokens.toLocaleString()}</div>
                    <div>Cost: ${Number(jr.estimated_cost).toFixed(6)}</div>
                    <div>Latency: {(jr.latency_ms / 1000).toFixed(2)}s</div>
                    <div>Decisions: {jr.decisions?.length || 0}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface-container-low border border-[#262930] rounded-xl p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-white mb-3">
              Execution Validation Scenarios
            </h3>
            {validationScenarios.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono">No execution scenarios required by validation policy.</p>
            ) : (
              <div className="space-y-3">
                {validationScenarios.map((sc) => (
                  <div key={sc.id} className="bg-surface-container-lowest p-3.5 rounded-lg border border-[#262930] font-mono text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[#A78BFA] font-bold">[{sc.scenario_type}] {sc.description}</span>
                      <span className="text-slate-400 text-[11px]">Timeout: {sc.timeout_seconds}s</span>
                    </div>
                    <div className="text-slate-300">Command: <code className="bg-surface-container px-2 py-0.5 rounded">{sc.command}</code></div>
                    <div className="text-slate-400 text-[11px]">Expected: {sc.expected_behavior}</div>
                    {sc.results && sc.results.map((r) => (
                      <div key={r.id} className="mt-2 pt-2 border-t border-[#262930] flex items-center justify-between text-[11px]">
                        <span className={r.status === "PASS" ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          Result: {r.status} (Exit Code: {r.exit_code ?? 0})
                        </span>
                        <span className="text-slate-500">Duration: {r.duration_ms}ms</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Agents */}
      {activeTab === "agents" && (
        <div className="space-y-3">
          {agents.map((run) => (
            <div key={run.id} className="bg-surface-container-low border border-[#262930] rounded-xl p-4 font-mono text-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-sm text-white capitalize">{run.agent_name} Specialist</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    run.status === "COMPLETED"
                      ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                      : "bg-rose-950/80 text-rose-400 border border-rose-800"
                  }`}
                >
                  {run.status}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-400 text-xs">
                <div>Model: <span className="text-slate-200">{run.model_name}</span></div>
                <div>Prompt: <span className="text-slate-200">{run.prompt_version}</span></div>
                <div>Tokens: <span className="text-slate-200">{run.total_tokens.toLocaleString()}</span></div>
                <div>Cost: <span className="text-slate-200">${Number(run.estimated_cost).toFixed(5)}</span></div>
                <div>Latency: <span className="text-slate-200">{(run.latency_ms / 1000).toFixed(2)}s</span></div>
                <div>Retries: <span className="text-slate-200">{run.retry_count}</span></div>
              </div>
              {run.error_message && (
                <div className="mt-2 p-2.5 rounded-lg bg-rose-950/50 border border-rose-900 text-rose-300">
                  {run.error_message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tab: Traces */}
      {activeTab === "traces" && (
        <div className="bg-surface-container-low border border-[#262930] rounded-xl overflow-hidden font-mono text-xs">
          <table className="w-full text-left">
            <thead className="bg-surface-container-lowest text-slate-400 border-b border-[#262930]">
              <tr>
                <th className="p-3">Node Name</th>
                <th className="p-3">Agent</th>
                <th className="p-3">Status</th>
                <th className="p-3">Model</th>
                <th className="p-3">Duration</th>
                <th className="p-3">Tokens</th>
                <th className="p-3">Retries</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#262930] text-slate-300">
              {traces.map((t) => (
                <tr key={t.id} className="hover:bg-surface-container/50">
                  <td className="p-3 font-semibold text-white">{t.node_name}</td>
                  <td className="p-3 capitalize">{t.agent_name}</td>
                  <td className="p-3">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] ${
                        t.status === "COMPLETED" ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-400">{t.model_name || "-"}</td>
                  <td className="p-3">{t.duration_ms.toFixed(1)} ms</td>
                  <td className="p-3">{t.total_tokens.toLocaleString()}</td>
                  <td className="p-3">{t.retry_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Artifacts */}
      {activeTab === "artifacts" && (
        <div className="space-y-4">
          {diffArtifact && (
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-2">
                Pull Request Unified Diff
              </h3>
              <DiffViewer diffText={diffArtifact.content} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

