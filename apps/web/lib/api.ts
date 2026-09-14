import {
  HealthStatus,
  Organization,
  PaginatedResponse,
  PullRequest,
  ReadinessStatus,
  Repository,
  ReviewArtifact,
  ReviewJob,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Dev-Token": "codeguard-dev-token",
        ...(options?.headers || {}),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(
        errorData?.error?.message || errorData?.detail || `API error (${res.status})`
      );
    }

    return res.json();
  } catch (err: any) {
    console.error(`API request error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  getHealth: () => request<HealthStatus>("/health"),
  getReadiness: () => request<ReadinessStatus>("/ready"),

  getOrganizations: (page = 1, pageSize = 20) =>
    request<PaginatedResponse<Organization>>(`/organizations?page=${page}&page_size=${pageSize}`),

  getRepositories: (page = 1, pageSize = 20, organizationId?: string) => {
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (organizationId) query.append("organization_id", organizationId);
    return request<PaginatedResponse<Repository>>(`/repositories?${query.toString()}`);
  },

  getRepository: (id: string) => request<Repository>(`/repositories/${id}`),

  getPullRequests: (page = 1, pageSize = 20, repositoryId?: string, state?: string) => {
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (repositoryId) query.append("repository_id", repositoryId);
    if (state) query.append("state", state);
    return request<PaginatedResponse<PullRequest>>(`/pull-requests?${query.toString()}`);
  },

  getPullRequest: (id: string) => request<PullRequest>(`/pull-requests/${id}`),

  getPullRequestReviews: (prId: string, page = 1, pageSize = 20) =>
    request<PaginatedResponse<ReviewJob>>(
      `/pull-requests/${prId}/reviews?page=${page}&page_size=${pageSize}`
    ),

  getReviewJob: (jobId: string) => request<ReviewJob>(`/review-jobs/${jobId}`),

  getReviewJobArtifacts: (jobId: string) =>
    request<ReviewArtifact[]>(`/review-jobs/${jobId}/artifacts`),

  // Code Intelligence API
  getRepositoryIndex: (repoId: string) =>
    request<import("./types").RepositoryIndex>(`/repositories/${repoId}/index`),

  triggerRepositoryIndex: (repoId: string, commitSha?: string) =>
    request<import("./types").RepositoryIndex>(`/repositories/${repoId}/index`, {
      method: "POST",
      body: JSON.stringify({ commit_sha: commitSha }),
    }),

  getRepositorySymbols: (
    repoId: string,
    page = 1,
    pageSize = 50,
    kind?: string,
    filePath?: string
  ) => {
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (kind) query.append("kind", kind);
    if (filePath) query.append("file_path", filePath);
    return request<PaginatedResponse<import("./types").CodeSymbol>>(
      `/repositories/${repoId}/symbols?${query.toString()}`
    );
  },

  getFileDependencies: (repoId: string, filePath: string) =>
    request<import("./types").FileDependency[]>(
      `/repositories/${repoId}/files/${encodeURIComponent(filePath)}/dependencies`
    ),

  getRepositoryContext: (
    repoId: string,
    changedFile: string,
    commitSha?: string,
    changedSymbol?: string
  ) => {
    const query = new URLSearchParams({ changed_file: changedFile });
    if (commitSha) query.append("commit_sha", commitSha);
    if (changedSymbol) query.append("changed_symbol", changedSymbol);
    return request<import("./types").RelevantContext>(
      `/repositories/${repoId}/context?${query.toString()}`
    );
  },

  getReviewJobDiff: (jobId: string) =>
    request<import("./types").DiffFile[]>(`/review-jobs/${jobId}/diff`),

  getReviewJobChunks: (jobId: string) =>
    request<import("./types").ASTChunk[]>(`/review-jobs/${jobId}/chunks`),

  getReviewJobChangedLines: (jobId: string) =>
    request<import("./types").ChangedLineIndexData>(`/review-jobs/${jobId}/changed-lines`),

  getReviewJobAgents: (jobId: string) =>
    request<import("./types").AgentRun[]>(`/review-jobs/${jobId}/agents`),

  getReviewJobFindings: (
    jobId: string,
    filters?: { severity?: string; category?: string; status?: string }
  ) => {
    const query = new URLSearchParams();
    if (filters?.severity) query.append("severity", filters.severity);
    if (filters?.category) query.append("category", filters.category);
    if (filters?.status) query.append("status_filter", filters.status);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request<import("./types").ReviewFinding[]>(`/review-jobs/${jobId}/findings${qs}`);
  },

  getReviewJobFinding: (jobId: string, findingId: string) =>
    request<import("./types").ReviewFinding>(`/review-jobs/${jobId}/findings/${findingId}`),

  getReviewJobTrace: (jobId: string) =>
    request<import("./types").AgentTrace[]>(`/review-jobs/${jobId}/trace`),

  getReviewJobUsage: (jobId: string) =>
    request<import("./types").ReviewUsage>(`/review-jobs/${jobId}/usage`),

  rerunReviewJob: (jobId: string) =>
    request<import("./types").ReviewJob>(`/review-jobs/${jobId}/rerun`, { method: "POST" }),

  // Phase 4: Adversarial Verification & Validation APIs
  getVerificationSummary: (jobId: string) =>
    request<import("./types").VerificationSummary>(`/review-jobs/${jobId}/verification`),

  getJudgeRuns: (jobId: string) =>
    request<import("./types").JudgeRun[]>(`/review-jobs/${jobId}/judge`),

  getValidationScenarios: (jobId: string) =>
    request<import("./types").ValidationScenario[]>(`/review-jobs/${jobId}/validation`),

  getFinding: (findingId: string) =>
    request<import("./types").ReviewFinding>(`/findings/${findingId}`),

  getFindingEvidence: (findingId: string) =>
    request<import("./types").FindingEvidence[]>(`/findings/${findingId}/evidence`),

  getFindingHistory: (findingId: string) =>
    request<import("./types").VerificationEvent[]>(`/findings/${findingId}/history`),

  verifyFinding: (findingId: string) =>
    request<import("./types").ReviewFinding>(`/findings/${findingId}/verify`, { method: "POST" }),

  rerunValidation: (findingId: string) =>
    request<import("./types").ReviewFinding>(`/findings/${findingId}/rerun-validation`, { method: "POST" }),

  // Phase 5: Governance, Approvals, Publishing, & Audit APIs
  getApprovals: (page = 1, pageSize = 20, organizationId?: string, repositoryId?: string, status?: string) => {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (organizationId) query.append("organization_id", organizationId);
    if (repositoryId) query.append("repository_id", repositoryId);
    if (status) query.append("status", status);
    return request<import("./types").PaginatedResponse<import("./types").ApprovalRequest>>(`/approvals?${query.toString()}`);
  },

  getApproval: (approvalId: string) =>
    request<import("./types").ApprovalRequest>(`/approvals/${approvalId}`),

  approveApproval: (approvalId: string, comment?: string) =>
    request<import("./types").ApprovalRequest>(`/approvals/${approvalId}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment: comment || "Approved by reviewer" }),
    }),

  rejectApproval: (approvalId: string, reason: string) =>
    request<import("./types").ApprovalRequest>(`/approvals/${approvalId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || "Rejected by reviewer" }),
    }),

  getReviewJobPublication: (jobId: string) =>
    request<import("./types").GitHubReviewPublication>(`/review-jobs/${jobId}/publication`),

  requestJobApproval: (jobId: string, findingId?: string, action: string = "COMMENT") =>
    request<{ approval_id: string; status: string }>(`/review-jobs/${jobId}/publication/request-approval`, {
      method: "POST",
      body: JSON.stringify({ finding_id: findingId, action }),
    }),

  publishReviewJob: (jobId: string, action: string = "COMMENT") =>
    request<import("./types").GitHubReviewPublication>(`/review-jobs/${jobId}/publication/publish`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),

  getReviewJobAudit: (jobId: string) =>
    request<import("./types").ToolExecutionAudit[]>(`/review-jobs/${jobId}/audit`),

  getAuditLogs: (page = 1, pageSize = 50, organizationId?: string, repositoryId?: string, toolName?: string) => {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (organizationId) query.append("organization_id", organizationId);
    if (repositoryId) query.append("repository_id", repositoryId);
    if (toolName) query.append("tool_name", toolName);
    return request<import("./types").PaginatedResponse<import("./types").ToolExecutionAudit>>(`/audit?${query.toString()}`);
  },

  getOrganizationPolicies: (orgId: string) =>
    request<import("./types").OrganizationReviewPolicy>(`/organizations/${orgId}/policies`),

  updateOrganizationPolicies: (orgId: string, update: Partial<import("./types").OrganizationReviewPolicy>) =>
    request<import("./types").OrganizationReviewPolicy>(`/organizations/${orgId}/policies`, {
      method: "PATCH",
      body: JSON.stringify(update),
    }),
};

