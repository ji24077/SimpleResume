import { NextRequest, NextResponse } from "next/server";
import { longFetch } from "@/lib/long-fetch";

export const maxDuration = 600;

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const r = await longFetch(`${BACKEND}/resume/render-only`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  if (r.ok) {
    const buf = await r.arrayBuffer();
    return new NextResponse(buf, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Cache-Control": "no-store",
      },
    });
  }
  let detail: string;
  try {
    const j = await r.json();
    detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
  } catch {
    detail = await r.text();
  }
  return NextResponse.json({ detail }, { status: r.status });
}
