"use client";

import type { ReviewIssue } from "@/lib/types";

type Props = {
  name: string;
  issues: ReviewIssue[];
};

export default function PageHead({ name, issues }: Props) {
  const counts = issues.reduce(
    (acc, i) => {
      if (i.severity === "critical") acc.critical += 1;
      else if (i.severity === "moderate") acc.warn += 1;
      else acc.minor += 1;
      return acc;
    },
    { critical: 0, warn: 0, minor: 0 },
  );

  return (
    <>
      <div className="t-eyebrow" style={{ marginBottom: 6 }}>
        editor · base résumé
      </div>
      <h1 className="font-display" style={{ fontSize: 28, fontWeight: 600 }}>
        {name || "Your résumé"} — review &amp; rewrite
      </h1>
      <div className="row" style={{ gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        {counts.critical > 0 && <span className="pill error">{counts.critical} critical</span>}
        {counts.warn > 0 && <span className="pill warn">{counts.warn} warn</span>}
        {counts.minor > 0 && <span className="pill success">{counts.minor} strength</span>}
        <span className="pill info">ATS · OK</span>
      </div>
    </>
  );
}
