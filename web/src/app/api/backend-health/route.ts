import { NextResponse } from "next/server";

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET() {
  try {
    const r = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    const data = await r.json();
    return NextResponse.json(data, { status: r.ok ? 200 : 502 });
  } catch {
    return NextResponse.json(
      { ok: false, error: "Cannot reach API. Is uvicorn running on port 8000?" },
      { status: 503 },
    );
  }
}
