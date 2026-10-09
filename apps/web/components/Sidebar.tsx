"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "../lib/api";
import { Repository } from "../lib/types";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const pathname = usePathname();
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [prCount, setPrCount] = useState<number>(0);
  const [pendingApprovalCount, setPendingApprovalCount] = useState<number>(0);
  const [githubConnected, setGithubConnected] = useState<boolean>(false);
  const [engineStatus, setEngineStatus] = useState<string>("Online");
  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);

  useEffect(() => {
    // Fetch live summary counts for navigation badges
    Promise.allSettled([
      api.getRepositories(1, 20),
      api.getPullRequests(1, 1),
      api.getApprovals(1, 1, undefined, undefined, "PENDING"),
      api.getGitHubInstallations(),
      api.getReadiness(),
    ]).then(([reposRes, prsRes, appsRes, instRes, readyRes]) => {
      if (reposRes.status === "fulfilled" && reposRes.value?.items) {
        setRepositories(reposRes.value.items);
        if (reposRes.value.items.length > 0) {
          setSelectedRepo(reposRes.value.items[0]);
        }
      }
      if (prsRes.status === "fulfilled" && prsRes.value) {
        setPrCount(prsRes.value.total || prsRes.value.items?.length || 0);
      }
      if (appsRes.status === "fulfilled" && appsRes.value) {
        setPendingApprovalCount(appsRes.value.total || appsRes.value.items?.length || 0);
      }
      if (instRes.status === "fulfilled" && Array.isArray(instRes.value)) {
        setGithubConnected(instRes.value.length > 0);
      }
      if (readyRes.status === "fulfilled" && readyRes.value) {
        setEngineStatus(readyRes.value.status === "ready" ? "Operational" : "Degraded");
      }
    });
  }, []);

  const navLinks = [
    {
      href: "/dashboard",
      label: "Overview",
      icon: "grid_view",
      activeMatch: (p: string) => p === "/" || p === "/dashboard",
    },
    {
      href: "/repositories",
      label: "Repositories",
      icon: "source_environment",
      badge: repositories.length > 0 ? String(repositories.length) : undefined,
      activeMatch: (p: string) => p.startsWith("/repositories"),
    },
    {
      href: "/pull-requests",
      label: "Pull Requests",
      icon: "merge",
      badge: prCount > 0 ? String(prCount) : undefined,
      activeMatch: (p: string) => p.startsWith("/pull-requests"),
    },
    {
      href: "/reviews",
      label: "Reviews",
      icon: "rate_review",
      activeMatch: (p: string) => p.startsWith("/reviews"),
    },
    {
      href: "/diff-review",
      label: "Code Diff",
      icon: "difference",
      activeMatch: (p: string) => p.startsWith("/diff-review"),
    },
    {
      href: "/findings",
      label: "Findings",
      icon: "upload_2",
      activeMatch: (p: string) => p.startsWith("/findings"),
    },
    {
      href: "/benchmarks",
      label: "Benchmarks",
      icon: "speed",
      activeMatch: (p: string) => p.startsWith("/benchmarks"),
    },
    {
      href: "/policies",
      label: "Policies",
      icon: "verified_user",
      activeMatch: (p: string) => p.startsWith("/policies"),
    },
    {
      href: "/approvals",
      label: "Approvals",
      icon: "assignment_turned_in",
      badge: pendingApprovalCount > 0 ? String(pendingApprovalCount) : undefined,
      badgeColor: "bg-error-container text-on-error-container",
      activeMatch: (p: string) => p.startsWith("/approvals"),
    },
    {
      href: "/audit",
      label: "Audit Logs",
      icon: "history_edu",
      activeMatch: (p: string) => p.startsWith("/audit"),
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-40 md:hidden backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-screen w-64 bg-surface-container-lowest z-50 flex flex-col justify-between select-none border-r border-[#262930] transition-transform duration-200 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="flex flex-col min-h-0">
          {/* Top Logo & Enterprise Badge */}
          <div className="h-14 px-space-md flex items-center justify-between bg-surface-container-low border-b border-[#262930]">
            <Link href="/dashboard" className="flex items-center gap-space-sm min-w-0" onClick={onClose}>
              <div className="w-8 h-8 rounded bg-primary-container text-on-primary-container flex items-center justify-center font-label-mono font-bold text-sm tracking-tighter">
                CG
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-headline-sm text-headline-sm text-primary tracking-tight truncate leading-none">
                  CodeGuard AI
                </span>
                <span className="font-label-mono text-label-mono text-outline uppercase mt-0.5">
                  Autonomous Core
                </span>
              </div>
            </Link>
            <span className="px-1.5 py-0.5 rounded font-label-mono text-kbd-shortcut bg-primary-container text-on-primary-container font-semibold tracking-wider">
              ENTERPRISE
            </span>
          </div>

          {/* Active Repository Switcher Dropdown */}
          <div className="p-space-sm relative">
            <button
              className="w-full flex items-center justify-between px-space-sm py-space-xs rounded bg-surface-container-low hover:bg-surface-container-high transition-colors text-left border border-[#262930]"
              type="button"
              onClick={() => setRepoDropdownOpen(!repoDropdownOpen)}
            >
              <div className="flex items-center gap-space-xs min-w-0">
                <span className="material-symbols-outlined text-[16px] text-primary-fixed">folder_open</span>
                <div className="flex flex-col min-w-0">
                  <span className="font-label-mono text-label-mono text-on-surface truncate">
                    {selectedRepo ? selectedRepo.full_name : "All Repositories"}
                  </span>
                  <span className="font-label-mono text-kbd-shortcut text-tertiary-fixed-dim flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-tertiary-fixed-dim inline-block"></span>
                    {selectedRepo ? `${selectedRepo.default_branch} (monitored)` : "Multi-tenant sync"}
                  </span>
                </div>
              </div>
              <span className="material-symbols-outlined text-[16px] text-on-surface-variant">unfold_more</span>
            </button>

            {/* Dropdown Menu */}
            {repoDropdownOpen && (
              <div className="absolute top-full left-space-sm right-space-sm mt-1 bg-surface-container-high border border-outline-variant/40 rounded shadow-xl z-50 max-h-48 overflow-y-auto p-1">
                <div
                  className="px-2 py-1.5 rounded hover:bg-surface-container text-xs font-label-mono text-on-surface cursor-pointer"
                  onClick={() => {
                    setSelectedRepo(null);
                    setRepoDropdownOpen(false);
                  }}
                >
                  All Repositories
                </div>
                {repositories.map((repo) => (
                  <div
                    key={repo.id}
                    className="px-2 py-1.5 rounded hover:bg-surface-container text-xs font-label-mono text-on-surface cursor-pointer truncate"
                    onClick={() => {
                      setSelectedRepo(repo);
                      setRepoDropdownOpen(false);
                    }}
                  >
                    {repo.full_name}
                  </div>
                ))}
                <Link
                  href="/repositories"
                  className="block px-2 py-1.5 mt-1 border-t border-[#262930] text-[11px] font-label-mono text-primary-fixed hover:underline"
                  onClick={() => setRepoDropdownOpen(false)}
                >
                  + Add / Connect Repo
                </Link>
              </div>
            )}
          </div>

          <div className="px-space-md py-space-xs">
            <span className="font-label-mono text-kbd-shortcut uppercase text-outline tracking-wider">
              Workspace Console
            </span>
          </div>

          {/* Nav links */}
          <nav className="flex-1 overflow-y-auto px-space-sm space-y-0.5">
            {navLinks.map((item) => {
              const active = item.activeMatch(pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  className={`flex items-center gap-space-sm px-space-sm py-1.5 rounded transition-colors ${
                    active
                      ? "bg-surface-container-high text-primary-fixed font-semibold"
                      : "font-body-sm text-body-sm text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`ml-auto font-label-mono text-kbd-shortcut px-1.5 py-0.2 rounded ${
                        item.badgeColor || "bg-surface-container-high text-on-surface"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Integration & Telemetry Status Cards */}
        <div className="p-space-sm space-y-space-xs bg-surface-container-lowest border-t border-[#262930]">
          <div className="p-space-xs rounded bg-surface-container-low flex flex-col gap-1 border border-[#262930]">
            <div className="flex items-center justify-between">
              <span className="font-label-mono text-kbd-shortcut uppercase text-outline">Integration</span>
              <span
                className={`flex items-center gap-1 font-label-mono text-kbd-shortcut ${
                  githubConnected ? "text-tertiary-fixed-dim" : "text-amber-400"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    githubConnected ? "bg-tertiary-fixed-dim" : "bg-amber-400"
                  }`}
                />
                {githubConnected ? "Connected" : "Setup Required"}
              </span>
            </div>
            <span className="font-label-mono text-label-mono text-on-surface-variant truncate">
              {githubConnected ? "GitHub App: Sync Active" : "No GitHub App Installed"}
            </span>
          </div>

          <div className="p-space-xs rounded bg-surface-container-low flex flex-col gap-1 border border-[#262930]">
            <div className="flex items-center justify-between">
              <span className="font-label-mono text-kbd-shortcut uppercase text-outline">Engine</span>
              <span className="font-label-mono text-kbd-shortcut text-primary-fixed">v3.4 Autonomous</span>
            </div>
            <span className="font-label-mono text-label-mono text-on-surface-variant truncate">
              Consensus: {engineStatus}
            </span>
          </div>

          <Link
            href="/debug"
            className="flex items-center justify-between px-space-xs py-1 text-on-surface-variant hover:text-on-surface font-label-mono text-label-mono transition-colors"
          >
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">terminal</span>
              System Telemetry &amp; Debug
            </span>
            <span className="font-kbd-shortcut text-kbd-shortcut bg-surface-container-high px-1 py-0.5 rounded text-outline">
              F1
            </span>
          </Link>
        </div>
      </aside>
    </>
  );
};
