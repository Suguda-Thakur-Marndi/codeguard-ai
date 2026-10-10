"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Organization, OrganizationReviewPolicy } from "../../lib/types";

export default function PoliciesPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [policy, setPolicy] = useState<OrganizationReviewPolicy | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Load organizations first
  useEffect(() => {
    api
      .getOrganizations(1, 20)
      .then((res) => {
        setOrgs(res.items || []);
        if (res.items && res.items.length > 0) {
          setSelectedOrgId(res.items[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setMessage({ type: "error", text: err.message || "Failed to load organizations" });
        setLoading(false);
      });
  }, []);

  // Load policy whenever org changes
  useEffect(() => {
    if (!selectedOrgId) return;
    setLoading(true);
    setMessage(null);
    api
      .getOrganizationPolicies(selectedOrgId)
      .then((pol) => {
        setPolicy(pol);
      })
      .catch((err) => {
        setMessage({ type: "error", text: err.message || "Failed to load policies" });
      })
      .finally(() => setLoading(false));
  }, [selectedOrgId]);

  async function handleSave() {
    if (!selectedOrgId || !policy) return;
    try {
      setSaving(true);
      setMessage(null);
      const updated = await api.updateOrganizationPolicies(selectedOrgId, {
        auto_publish_advisory: policy.auto_publish_advisory,
        auto_publish_low: policy.auto_publish_low,
        require_approval_for_high: policy.require_approval_for_high,
        require_approval_for_critical: policy.require_approval_for_critical,
        allow_request_changes: policy.allow_request_changes,
        allow_ai_github_comments: policy.allow_ai_github_comments,
        approval_expiry_minutes: policy.approval_expiry_minutes,
      });
      setPolicy(updated);
      setMessage({ type: "success", text: "Organization policies successfully synchronized and enforced." });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to save policies" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="border-b border-[#262930] pb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-headline-lg text-headline-lg tracking-tight text-primary font-bold">Organization Review Policy</h1>
            <span className="px-2 py-0.5 rounded font-label-mono text-kbd-shortcut bg-secondary-container text-on-secondary-container border border-secondary/30 uppercase tracking-wider font-semibold">
              Admin Restricted
            </span>
          </div>
          <p className="font-body-sm text-body-sm text-outline mt-1">
            Configure automated GitHub publishing thresholds and deterministic zero-trust approval gates.
          </p>
        </div>

        {orgs.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="font-label-mono text-kbd-shortcut text-outline">Target:</span>
            <select
              value={selectedOrgId}
              onChange={(e) => setSelectedOrgId(e.target.value)}
              className="bg-surface-container-low border border-[#262930] text-on-surface rounded px-3 py-1.5 font-label-mono text-kbd-shortcut focus:outline-none focus:border-primary-fixed"
            >
              {orgs.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.github_account_login}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {message && (
        <div
          className={`p-3.5 rounded-lg text-xs font-mono border flex items-center gap-2.5 ${
            message.type === "success"
              ? "bg-tertiary-container/20 text-tertiary-fixed-dim border-tertiary-fixed-dim/40"
              : "bg-error-container/20 text-error border-error/40"
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">
            {message.type === "success" ? "check_circle" : "error"}
          </span>
          <span>{message.text}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-outline font-label-mono text-xs flex items-center justify-center gap-2">
          <span className="w-3.5 h-3.5 border-2 border-primary-fixed border-t-transparent rounded-full animate-spin"></span>
          <span>Loading organization policies...</span>
        </div>
      ) : !policy ? (
        <div className="p-10 text-center bg-surface-container-low border border-[#262930] rounded-xl text-outline font-label-mono text-xs">
          No policy configuration found for the selected organization.
        </div>
      ) : (
        <div className="space-y-6 bg-surface-container-lowest border border-[#262930] rounded-xl p-6 shadow-xl">
          {/* Section: Auto-Publishing Gates */}
          <div>
            <div className="flex items-center gap-2 border-b border-[#262930] pb-2.5">
              <span className="material-symbols-outlined text-outline text-[18px]">publish</span>
              <h3 className="font-headline-sm text-headline-sm text-primary uppercase tracking-wider font-mono">
                Automated Publishing Gates
              </h3>
            </div>
            <p className="font-body-sm text-body-sm text-outline mt-1.5">
              Control which severity tiers can be automatically published without mandatory human sign-off.
            </p>

            <div className="divide-y divide-[#262930]/80 mt-4">
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-on-surface">Advisory Findings</div>
                  <div className="text-[11px] text-outline">Informational style, hygiene, or maintenance suggestions</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy.auto_publish_advisory}
                    onChange={(e) =>
                      setPolicy({ ...policy, auto_publish_advisory: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-container-high border border-[#333842] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary"></div>
                </label>
              </div>

              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-on-surface">Low Severity Findings</div>
                  <div className="text-[11px] text-outline">Minor security caveats or bugs with limited blast radius</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy.auto_publish_low}
                    onChange={(e) => setPolicy({ ...policy, auto_publish_low: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-container-high border border-[#333842] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Section: Mandatory Human Approval */}
          <div>
            <div className="flex items-center gap-2 border-b border-[#262930] pb-2.5">
              <span className="material-symbols-outlined text-primary-fixed text-[18px]">verified_user</span>
              <h3 className="font-headline-sm text-headline-sm text-primary uppercase tracking-wider font-mono">
                Mandatory Human Sign-off Gates
              </h3>
            </div>
            <p className="font-body-sm text-body-sm text-outline mt-1.5">
              Zero-trust enforcement halts publication of critical or high-risk findings until authorized by a security reviewer.
            </p>

            <div className="divide-y divide-[#262930]/80 mt-4">
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-on-surface">
                    Require Approval for High Severity
                  </div>
                  <div className="text-[11px] text-outline">Severe logic flaws, authorization boundaries, and vulnerable calls</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy.require_approval_for_high}
                    onChange={(e) =>
                      setPolicy({ ...policy, require_approval_for_high: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-container-high border border-[#333842] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-black after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container peer-checked:after:bg-black"></div>
                </label>
              </div>

              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-on-surface">
                    Require Approval for Critical Severity
                  </div>
                  <div className="text-[11px] text-outline">
                    Direct RCE, authentication bypasses, secret leaks, data loss vectors
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy.require_approval_for_critical}
                    onChange={(e) =>
                      setPolicy({ ...policy, require_approval_for_critical: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-container-high border border-[#333842] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-black after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container peer-checked:after:bg-black"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Section: Action Permissions & TTL */}
          <div>
            <div className="flex items-center gap-2 border-b border-[#262930] pb-2.5">
              <span className="material-symbols-outlined text-outline text-[18px]">timer</span>
              <h3 className="font-headline-sm text-headline-sm text-primary uppercase tracking-wider font-mono">
                Privilege Boundaries &amp; Expiration
              </h3>
            </div>

            <div className="divide-y divide-[#262930]/80 mt-4">
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-on-surface">
                    Allow AI REQUEST_CHANGES Action
                  </div>
                  <div className="text-[11px] text-outline">
                    Permits CodeGuard to issue a blocking REQUEST_CHANGES review event on GitHub
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy.allow_request_changes}
                    onChange={(e) =>
                      setPolicy({ ...policy, allow_request_changes: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-surface-container-high border border-[#333842] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-secondary"></div>
                </label>
              </div>

              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-on-surface">
                    Approval Window TTL (Minutes)
                  </div>
                  <div className="text-[11px] text-outline">
                    Pending approvals automatically expire if not published within this window
                  </div>
                </div>
                <div className="w-28">
                  <input
                    type="number"
                    min={5}
                    max={1440}
                    value={policy.approval_expiry_minutes}
                    onChange={(e) =>
                      setPolicy({
                        ...policy,
                        approval_expiry_minutes: parseInt(e.target.value) || 30,
                      })
                    }
                    className="w-full bg-surface-container-lowest border border-[#262930] rounded-lg px-3 py-1.5 font-label-mono text-kbd-shortcut text-on-surface text-right focus:outline-none focus:border-primary-fixed"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-[#262930]">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 rounded-lg font-headline-sm text-body-sm font-semibold bg-primary-container text-on-primary-container hover:brightness-105 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
            >
              {saving ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin"></span>
                  <span>Enforcing Policy...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[16px]">save</span>
                  <span>Save Policy Configuration</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

