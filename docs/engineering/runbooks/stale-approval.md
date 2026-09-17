# Operational Runbook: Commit Drift & Stale Approval Resolution

**Runbook ID**: `RB-OPS-009`  
**Classification**: Workflow Invariant Incident  
**Target Services**: Approval Service (`app/services/approval_service.py`), Publication Service

---

## 1. Description & Invariant Protection

CodeGuard AI enforces strict cryptographic binding between human approvals and pull request commit SHAs:
> *If an approval is granted for commit SHA `A`, and the author subsequent pushes commit SHA `B`, the approval is immediately invalidated (`STALE`) and review publication is blocked.*

This prevents malicious authors from obtaining approval on benign code and immediately substituting vulnerable code.

---

## 2. Diagnosis & User Experience

When commit drift occurs:
- The UI dashboard displays: `"Approval Stale: Commit drift detected (PR head commit changed)"`.
- The publication service logs: `Commit drift detected between approval head_sha (SHA-A) and current PR head_sha (SHA-B). Aborting publication.`
- Approval status in database transitions to `ApprovalStatus.STALE`.

---

## 3. Standard Operational Procedure

### Step 1: Verify Divergence in Database
```sql
SELECT a.id, a.pull_request_id, a.status, a.commit_sha AS approved_sha, pr.head_sha AS current_sha
FROM approval_requests a
JOIN pull_requests pr ON a.pull_request_id = pr.id
WHERE a.status = 'STALE' OR (a.status = 'APPROVED' AND a.commit_sha != pr.head_sha);
```

### Step 2: Trigger Fresh Review Cycle
The pull request author or continuous integration must re-trigger analysis on the new commit SHA `B`:
1. Author pushes or comments `/codeguard review` on the pull request.
2. Webhook triggers new `ReviewJob` bound to `SHA-B`.
3. Specialized agents inspect the new diff.
4. If findings are produced, a new `ApprovalRequest` is generated bound to `SHA-B`.
5. Human approver reviews and approves the new request.
