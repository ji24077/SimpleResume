"use client";

type Props = {
  highlights?: boolean;
};

export default function MockResume({ highlights = false }: Props) {
  return (
    <div className="resume">
      <p className="r-name">John Doe</p>
      <p className="r-contact">
        john@example.com · linkedin.com/in/johndoe · github.com/johndoe · New York, NY
      </p>

      <p className="r-section">Education</p>
      <div className="r-row">
        <b>MIT · Ph.D., Computer Science</b>
        <span>2024 — Present</span>
      </div>
      <p className="r-sub">Advisor: Prof. R. Lin · Systems & ML</p>
      <div className="r-row">
        <b>Stanford University · B.S., Computer Science</b>
        <span>2018 — 2022</span>
      </div>
      <p className="r-sub">Honors · GPA 3.9/4.0</p>

      <p className="r-section">Experience</p>
      <div className="r-row">
        <b>Software Engineer · Jane Street</b>
        <span>2024 — Present</span>
      </div>
      <p className="r-sub">Trading Systems · New York, NY</p>
      <ul className="r-bullets">
        <li>
          Built low-latency signal pipeline cutting tick-to-trade from{" "}
          <b>18µs → 6µs</b> across <b>200k</b> symbols.
        </li>
        <li>
          {highlights ? (
            <span className="hl-warn">Worked on trading systems.</span>
          ) : (
            <>
              Owner of OCaml order-router rewrite; <b>−40%</b> CPU on the equities matching path.
            </>
          )}
        </li>
      </ul>

      <div className="r-row">
        <b>Software Engineer · Google</b>
        <span>2023 — 2024</span>
      </div>
      <p className="r-sub">Search Infrastructure · Mountain View, CA</p>
      <ul className="r-bullets">
        <li>
          Cut tail latency on ranking serving path <b>p99 −34%</b> by porting hot inner loop to
          AVX-512 and fusing two RPC hops.
        </li>
        <li>
          Designed cross-shard cache invalidation protocol now serving <b>4B</b> queries/day.
        </li>
      </ul>

      <div className="r-row">
        <b>Software Engineer · Stripe</b>
        <span>2022 — 2023</span>
      </div>
      <p className="r-sub">Payments Platform · San Francisco, CA</p>
      <ul className="r-bullets">
        <li>
          Migrated legacy ledger to event-sourced design, cutting reconciliation latency{" "}
          <b>45m → 90s</b> across <b>1.2B</b> daily events.
        </li>
        <li>
          {highlights ? (
            <span className="hl-error">Responsible for various caching projects.</span>
          ) : (
            "Authored RFC adopted org-wide for idempotency keying — used by 14 teams."
          )}
        </li>
      </ul>

      <div className="r-row">
        <b>Software Engineer Intern · Uber</b>
        <span>Summer 2021</span>
      </div>
      <p className="r-sub">Marketplace · San Francisco, CA</p>
      <ul className="r-bullets">
        <li>
          Shipped surge-pricing experiment harness; A/B&apos;d across <b>32</b> cities, lifting driver
          utilization <b>+2.1pp</b>.
        </li>
      </ul>

      <p className="r-section">Projects</p>
      <div className="r-row">
        <b>Pretrain a vLLM</b>
        <span>2024</span>
      </div>
      <ul className="r-bullets">
        <li>
          Pretrained a <b>1.3B</b>-param decoder-only transformer on <b>60B</b> FineWeb tokens
          (FSDP, 8×H100); matched Pythia-1B perplexity at <b>38%</b> of compute.
        </li>
        <li>
          Open-sourced training stack with custom data loader; <b>1.2k</b> GitHub stars in 3 months.
        </li>
      </ul>

      <p className="r-section">Skills</p>
      <div style={{ fontSize: 10, color: "#222", marginTop: 2 }}>
        <b>Languages:</b> OCaml, Python, C++, Rust · <b>Infra:</b> CUDA, Kafka, K8s · <b>Other:</b>{" "}
        PyTorch, Triton, gRPC
      </div>
    </div>
  );
}
