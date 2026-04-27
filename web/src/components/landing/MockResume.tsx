"use client";

type Props = {
  highlights?: boolean;
};

export default function MockResume({ highlights = false }: Props) {
  return (
    <div className="resume">
      <p className="r-name">Dhruv Patel</p>
      <p className="r-contact">
        dhruv@example.com · linkedin.com/in/dhruv · github.com/dhruv · Toronto, ON
      </p>

      <p className="r-section">Experience</p>
      <div className="r-row">
        <b>Senior Software Engineer · Stripe</b>
        <span>2023 — Present</span>
      </div>
      <p className="r-sub">Payments Platform · San Francisco, CA</p>
      <ul className="r-bullets">
        <li>
          Led migration of legacy ledger to event-sourced design, cutting reconciliation latency from{" "}
          <b>45m → 90s</b> across <b>1.2B</b> daily events.
        </li>
        <li>
          Owned p99 budget for the rails service; shipped backpressure controller dropping incidents{" "}
          <b>62% QoQ</b> (12 → 4).
        </li>
        <li>
          {highlights ? (
            <span className="hl-warn">Worked on improving system performance.</span>
          ) : (
            "Mentored 4 engineers; two promoted to L4 within the cycle."
          )}
        </li>
      </ul>

      <div className="r-row">
        <b>Software Engineer · Shopify</b>
        <span>2020 — 2023</span>
      </div>
      <p className="r-sub">Storefront Performance · Remote</p>
      <ul className="r-bullets">
        <li>
          Rebuilt critical render path; reduced TTFB by <b>380ms (-31%)</b> for top-1k merchants, lifting
          checkout conv. <b>+0.4pp</b>.
        </li>
        <li>
          {highlights ? (
            <span className="hl-error">Responsible for various caching projects.</span>
          ) : (
            "Authored RFC adopted org-wide for Edge cache keying — used by 14 teams."
          )}
        </li>
      </ul>

      <p className="r-section">Education</p>
      <div className="r-row">
        <b>University of Waterloo · BCS, Computer Science</b>
        <span>2016 — 2020</span>
      </div>
      <p className="r-sub">Honors, co-op stream · GPA 3.8/4.0</p>

      <p className="r-section">Skills</p>
      <div style={{ fontSize: 10, color: "#222", marginTop: 2 }}>
        <b>Languages:</b> Go, TypeScript, Python, Rust · <b>Infra:</b> Kafka, Postgres, K8s, Terraform · <b>Other:</b>{" "}
        gRPC, OpenTelemetry, Snowflake
      </div>
    </div>
  );
}
