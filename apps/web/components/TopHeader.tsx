"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, authStorage } from "../lib/api";

interface TopHeaderProps {
  onToggleMobileSidebar: () => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({ onToggleMobileSidebar }) => {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<{
    id: string;
    login: string;
    email?: string;
    role: string;
    picture?: string;
  } | null>(null);
  const [activePrsCount, setActivePrsCount] = useState<number>(0);
  const [criticalCount, setCriticalCount] = useState<number>(0);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    // Check for token in URL query parameter (e.g. from Google OAuth callback)
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get("token");
      if (token) {
        authStorage.setToken(token);
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
      }
    }

    // Load auth user
    api
      .getAuthMe()
      .then((res) => {
        if (res.authenticated && res.user) {
          setCurrentUser(res.user);
        }
      })
      .catch(() => setCurrentUser(null));

    // Load live telemetry counts
    Promise.allSettled([
      api.getPullRequests(1, 20),
      api.getApprovals(1, 10, undefined, undefined, "PENDING"),
    ]).then(([prsRes, appsRes]) => {
      if (prsRes.status === "fulfilled" && prsRes.value) {
        setActivePrsCount(prsRes.value.total || prsRes.value.items?.length || 0);
      }
      if (appsRes.status === "fulfilled" && appsRes.value) {
        setCriticalCount(appsRes.value.total || 0);
      }
    });
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      authStorage.removeToken();
    }
    setCurrentUser(null);
    window.location.reload();
  };

  // Generate breadcrumb items
  const getBreadcrumbs = () => {
    const parts = pathname.split("/").filter(Boolean);
    if (parts.length === 0 || parts[0] === "dashboard") {
      return [{ label: "CodeGuard AI", href: "/dashboard" }, { label: "Overview", href: "/dashboard" }];
    }
    return [
      { label: "CodeGuard AI", href: "/dashboard" },
      ...parts.map((part, index) => {
        const href = "/" + parts.slice(0, index + 1).join("/");
        const formatted = part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, " ");
        return { label: formatted, href };
      }),
    ];
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="fixed top-0 left-0 md:left-64 right-0 h-14 bg-surface-container-lowest/90 backdrop-blur-md z-40 flex items-center justify-between px-gutter-desktop border-b border-[#262930]">
      {/* Left section: Mobile hamburger & Breadcrumbs */}
      <div className="flex items-center gap-space-md min-w-0">
        <button
          type="button"
          onClick={onToggleMobileSidebar}
          className="md:hidden p-1.5 rounded hover:bg-surface-container text-on-surface-variant hover:text-on-surface"
          aria-label="Toggle navigation"
        >
          <span className="material-symbols-outlined text-[20px]">menu</span>
        </button>

        <div className="hidden sm:flex items-center gap-1.5 font-label-mono text-label-mono text-on-surface-variant truncate">
          {breadcrumbs.map((crumb, i) => (
            <React.Fragment key={crumb.href + i}>
              {i > 0 && <span className="text-outline-variant">/</span>}
              <Link
                href={crumb.href}
                className={
                  i === breadcrumbs.length - 1
                    ? "text-primary-fixed font-semibold truncate"
                    : "hover:text-on-surface transition-colors truncate"
                }
              >
                {crumb.label}
              </Link>
            </React.Fragment>
          ))}
        </div>

        {/* Global Search Input */}
        <div className="relative hidden lg:flex items-center ml-2">
          <span className="material-symbols-outlined absolute left-2.5 text-[16px] text-outline">search</span>
          <input
            className="bg-surface-container-low text-on-surface placeholder:text-outline font-body-sm text-body-sm pl-8 pr-12 py-1 rounded w-56 focus:w-72 transition-all outline-none border border-[#262930] focus:border-primary-fixed"
            placeholder="Search commands, symbols, or CVEs..."
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <span className="absolute right-2 font-kbd-shortcut text-kbd-shortcut bg-surface-container-highest px-1.5 py-0.5 rounded text-on-surface-variant">
            Ctrl K
          </span>
        </div>
      </div>

      {/* Right section: Live Telemetry & User Profile */}
      <div className="flex items-center gap-space-md">
        {/* Telemetry Pills */}
        <div className="hidden xl:flex items-center gap-space-xs">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container-low font-label-mono text-label-mono text-on-surface border border-[#262930]">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-fixed"></span>
            {activePrsCount} PRs Active
          </span>
          {criticalCount > 0 ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-error-container font-label-mono text-label-mono text-on-error-container">
              <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
              {criticalCount} Critical Blocked
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container-low font-label-mono text-label-mono text-tertiary-fixed-dim border border-[#262930]">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary-fixed-dim"></span>
              Zero Vulnerabilities Blocked
            </span>
          )}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container-low font-label-mono text-label-mono text-tertiary-fixed-dim border border-[#262930]">
            <span className="w-1.5 h-1.5 rounded-full bg-tertiary-fixed-dim"></span>
            Pipeline 99.8%
          </span>
        </div>

        {/* User Auth Profile */}
        <div className="flex items-center gap-space-sm pl-space-xs relative">
          {currentUser ? (
            <div>
              <button
                type="button"
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="flex items-center gap-space-xs pl-space-xs rounded bg-surface-container-low py-1 pr-space-sm hover:bg-surface-container-high transition-colors border border-[#262930]"
              >
                {currentUser.picture ? (
                  <img
                    alt={currentUser.login}
                    className="w-7 h-7 rounded-full object-cover"
                    src={currentUser.picture}
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-primary-container text-on-primary-container font-label-mono font-bold text-xs flex items-center justify-center">
                    {currentUser.login?.charAt(0).toUpperCase() || "U"}
                  </div>
                )}
                <div className="flex flex-col text-left">
                  <span className="font-label-md text-label-md text-on-surface font-semibold leading-none truncate max-w-[120px]">
                    {currentUser.login || currentUser.email}
                  </span>
                  <span className="font-label-mono text-kbd-shortcut text-outline uppercase mt-0.5">
                    {currentUser.role || "Lead Architect"}
                  </span>
                </div>
                <span className="material-symbols-outlined text-[16px] text-outline">expand_more</span>
              </button>

              {userDropdownOpen && (
                <div className="absolute right-0 top-full mt-2 w-52 bg-surface-container-high border border-outline-variant/40 rounded shadow-2xl p-1 z-50">
                  <div className="px-3 py-2 border-b border-[#262930]">
                    <p className="text-xs font-semibold text-on-surface">{currentUser.login}</p>
                    <p className="text-[11px] font-label-mono text-outline truncate">{currentUser.email}</p>
                  </div>
                  <Link
                    href="/policies"
                    className="flex items-center gap-2 px-3 py-1.5 text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded transition-colors"
                    onClick={() => setUserDropdownOpen(false)}
                  >
                    <span className="material-symbols-outlined text-[16px]">security</span>
                    Security Policies
                  </Link>
                  <Link
                    href="/audit"
                    className="flex items-center gap-2 px-3 py-1.5 text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded transition-colors"
                    onClick={() => setUserDropdownOpen(false)}
                  >
                    <span className="material-symbols-outlined text-[16px]">history</span>
                    Audit Trail
                  </Link>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-error hover:bg-error-container/20 rounded transition-colors border-t border-[#262930] mt-1"
                  >
                    <span className="material-symbols-outlined text-[16px]">logout</span>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/google/login`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-label-mono text-label-md bg-surface-container-high text-on-surface hover:bg-surface-container-highest border border-[#262930] transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">login</span>
              Sign in with Google
            </a>
          )}
        </div>
      </div>
    </header>
  );
};
