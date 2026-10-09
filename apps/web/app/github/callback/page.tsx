"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../lib/api";

function GitHubCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const installationIdStr = searchParams.get("installation_id");
    const setupAction = searchParams.get("setup_action");
    const errorParam = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (errorParam) {
      setStatus("error");
      setErrorMessage(errorDescription || `GitHub returned error: ${errorParam}`);
      return;
    }

    if (!installationIdStr) {
      setStatus("error");
      setErrorMessage("No installation ID received from GitHub.");
      return;
    }

    const installationId = parseInt(installationIdStr, 10);
    if (isNaN(installationId) || installationId <= 0) {
      setStatus("error");
      setErrorMessage("Invalid installation ID received from GitHub.");
      return;
    }

    // Verify and link installation with CodeGuard backend
    api
      .verifyGitHubInstallation(installationId)
      .then(() => {
        setStatus("success");
        // Forward to repositories page with query params so repository discovery drawer opens automatically
        router.replace(`/repositories?installation_id=${installationId}&setup_action=${setupAction || "install"}`);
      })
      .catch((err) => {
        console.error("Installation verification error:", err);
        setStatus("error");
        setErrorMessage(
          err.message || "Failed to verify GitHub installation. Please try again."
        );
      });
  }, [searchParams, router]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="max-w-md w-full p-8 bg-slate-900 border border-slate-800 rounded-xl shadow-xl text-center">
        {status === "verifying" && (
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin mx-auto" />
            <h2 className="text-lg font-bold text-white">Connecting GitHub...</h2>
            <p className="text-sm text-slate-400">
              Verifying CodeGuard AI GitHub App installation and discovering accessible repositories.
            </p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-950/80 border border-emerald-600 text-emerald-400 flex items-center justify-center mx-auto text-xl font-bold">
              ✓
            </div>
            <h2 className="text-lg font-bold text-white">GitHub Connected!</h2>
            <p className="text-sm text-slate-400">
              Redirecting to repositories to select which projects to monitor...
            </p>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-full bg-rose-950/80 border border-rose-600 text-rose-400 flex items-center justify-center mx-auto text-xl font-bold">
              ✕
            </div>
            <h2 className="text-lg font-bold text-white">Connection Failed</h2>
            <p className="text-sm text-rose-300 bg-rose-950/40 p-3 rounded border border-rose-900/50">
              {errorMessage}
            </p>
            <div className="pt-2">
              <Link
                href="/repositories"
                className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-sm"
              >
                Return to Repositories
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GitHubCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center text-slate-500 font-mono text-sm">
          Loading callback...
        </div>
      }
    >
      <GitHubCallbackContent />
    </Suspense>
  );
}
