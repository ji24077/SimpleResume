"use client";

import { useEffect, useState } from "react";

type BackendHealth = {
  ok?: boolean;
  openai_configured?: boolean;
  pdf_compile?: boolean;
  error?: string;
};

export default function Statusbar() {
  const [health, setHealth] = useState<BackendHealth | null>(null);

  useEffect(() => {
    let alive = true;
    const ping = () => {
      fetch("/api/backend-health")
        .then((r) => r.json())
        .then((d) => {
          if (alive) setHealth(d);
        })
        .catch(() => {
          if (alive) setHealth({ ok: false, error: "Health check failed" });
        });
    };
    ping();
    const t = setInterval(ping, 30000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const apiOk = !!health?.ok;
  const openaiOk = !!health?.openai_configured;
  const pdfOk = !!health?.pdf_compile;

  return (
    <div className="statusbar">
      <span>simpleresume.local · build 0.4.2</span>
      <div className="right">
        <span className={apiOk ? "" : "bad"}>API · {apiOk ? "OK" : "OFF"}</span>
        <span className={openaiOk ? "" : "bad"}>OpenAI · {openaiOk ? "OK" : "OFF"}</span>
        <span className={pdfOk ? "" : "bad"}>PDF compile · {pdfOk ? "OK" : "OFF"}</span>
      </div>
    </div>
  );
}
