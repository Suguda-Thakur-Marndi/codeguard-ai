"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../../lib/api";
import { PullRequest } from "../../lib/types";

export default function DiffReviewPage() {
  const router = useRouter();
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getPullRequests(1, 20)
      .then((res) => {
        const items = res.items || [];
        setPrs(items);
        if (items.length > 0) {
          // Forward to most recent pull request workspace
          router.replace(`/pull-requests/${items[0].id}`);
        } else {
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="p-12 text-center font-label-mono text-outline text-sm">
        Opening Code Diff Review Workspace...
      </div>
    );
  }

  return (
    <div className="p-8 max-w-xl mx-auto text-center space-y-4">
      <div className="w-12 h-12 rounded bg-surface-container-high border border-[#262930] flex items-center justify-center mx-auto text-primary-fixed">
        <span className="material-symbols-outlined text-[24px]">difference</span>
      </div>
      <h2 className="font-headline-sm text-headline-sm text-primary">No Active Diffs Available</h2>
      <p className="font-body-sm text-body-sm text-outline">
        No active pull requests were found for diff review. Connect a repository or open a pull request to trigger the 3-panel review workspace.
      </p>
      <Link
        href="/repositories"
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded bg-primary-container text-on-primary-container font-headline-sm text-body-sm font-semibold hover:brightness-105"
      >
        <span className="material-symbols-outlined text-[16px]">add_moderator</span>
        <span>Connect Repository</span>
      </Link>
    </div>
  );
}
