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
      setMessage({ type: "success", text: "Organization policies successfully updated." });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to save policies" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Header */}
      <div className="border-b border-slate-800 pb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Organization Review Policy</h1>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
              Admin Restricted
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Configure automated GitHub publishing thresholds and mandatory human approval gates.
          </p>
        </div>

        {orgs.length > 0 && (
          <div>
            <select
              value={selectedOrgId}
              onChange={(e) => setSelectedOrgId(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 rounded-lg px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-indigo-500"
            >
              {orgs.map((org) => (
                <option key={org.id} value={org.id}>
                  Org: {org.github_account_login}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {message && (
        <div
          className={`p-4 rounded-xl text-xs font-mono border ${
            message.type === "success"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
          }`}
        >
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-500 font-mono text-sm animate-pulse">
          Loading organization policies...
        </div>
      ) : !policy ? (
        <div className="p-8 text-center text-slate-500 text-sm">
          No policy found for the selected organization.
        </div>
      ) : (
        <div className="space-y-6 bg-slate-900/40 border border-slate-800 rounded-2xl p-6 shadow-xl">
          {/* Section: Auto-Publishing Gates */}
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono border-b border-slate-800 pb-2">
              Automated Publishing Gates
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Control which severity tiers can be automatically published without human sign-off.
            </p>

            <div className="divide-y divide-slate-800/60 mt-4">
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-200">Advisory Findings</div>
                  <div className="text-xs text-slate-400">Informational style or hygiene suggestions</div>
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
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>

              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-200">Low Severity Findings</div>
                  <div className="text-xs text-slate-400">Minor issues with low blast radius</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy.auto_publish_low}
                    onChange={(e) => setPolicy({ ...policy, auto_publish_low: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Section: Mandatory Human Approval */}
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono border-b border-slate-800 pb-2">
              Mandatory Human Sign-off
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Zero-trust enforcement prevents unreviewed publication of critical findings.
            </p>

            <div className="divide-y divide-slate-800/60 mt-4">
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-200">
                    Require Approval for High Severity
                  </div>
                  <div className="text-xs text-slate-400">Severe logic errors and vulnerabilities</div>
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
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>

              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-200">
                    Require Approval for Critical Severity
                  </div>
                  <div className="text-xs text-slate-400">
                    Critical exploits, authentication bypasses, data loss
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
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Section: Action Permissions & TTL */}
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono border-b border-slate-800 pb-2">
              Privilege Limits & Expiration
            </h3>

            <div className="divide-y divide-slate-800/60 mt-4">
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-200">
                    Allow AI REQUEST_CHANGES Action
                  </div>
                  <div className="text-xs text-slate-400">
                    Allows submitting reviews with blocking REQUEST_CHANGES event (requires human approval)
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
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>

              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-200">
                    Approval Window TTL (Minutes)
                  </div>
                  <div className="text-xs text-slate-400">
                    Approvals automatically expire if not published within this timeframe
                  </div>
                </div>
                <div className="w-32">
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
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm font-mono text-white text-right focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-800">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition-colors disabled:opacity-50"
            >
              {saving ? "Saving Policy..." : "Save Policy Configuration"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
