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
    fetch("/api/backend-health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false, error: "Health check failed" }));
  }, []);

  const apiOk = !!health?.ok;
  const openaiOk = !!health?.openai_configured;
  const pdfOk = !!health?.pdf_compile;

  return (
    <div className="statusbar">
      <span>resumeroast.local · build 0.4.2</span>
      <div className="right">
        <span className={apiOk ? "" : "bad"}>API · {apiOk ? "OK" : "OFF"}</span>
        <span className={openaiOk ? "" : "bad"}>OpenAI · {openaiOk ? "OK" : "OFF"}</span>
        <span className={pdfOk ? "" : "bad"}>PDF compile · {pdfOk ? "OK" : "OFF"}</span>
      </div>
    </div>
  );
}
