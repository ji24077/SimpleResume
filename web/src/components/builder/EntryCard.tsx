"use client";

import { ReactNode } from "react";

type EntryCardProps = {
  heading: string;
  subheading?: string;
  onDelete: () => void;
  deleteLabel?: string;
  children: ReactNode;
};

export default function EntryCard({
  heading,
  subheading,
  onDelete,
  deleteLabel = "Remove entry",
  children,
}: EntryCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-zinc-100">{heading || "Untitled entry"}</p>
          {subheading && <p className="truncate text-xs text-zinc-500">{subheading}</p>}
        </div>
        <button
          type="button"
          onClick={onDelete}
          aria-label={deleteLabel}
          className="rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-400 hover:border-red-700 hover:text-red-300"
        >
          Delete
        </button>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}
