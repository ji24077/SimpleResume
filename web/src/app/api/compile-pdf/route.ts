import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }
  const r = await fetch(`${BACKEND}/compile-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
