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
    <div
      className="rounded-lg p-4"
      style={{ border: "1px solid var(--border)", background: "var(--canvas-alt)" }}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate" style={{ fontSize: 14, fontWeight: 500, color: "var(--fg-1)" }}>
            {heading || "Untitled entry"}
          </p>
          {subheading && (
            <p className="truncate font-mono muted" style={{ fontSize: 11 }}>
              {subheading}
            </p>
          )}
        </div>
        <button type="button" onClick={onDelete} aria-label={deleteLabel} className="btn btn-soft btn-sm">
          Delete
        </button>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}
