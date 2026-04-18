import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const contentType = req.headers.get("content-type") || "";

  let upstream: Response;
  if (contentType.includes("application/json")) {
    upstream = await fetch(`${BACKEND}/resume/score-from-text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await req.text(),
    });
  } else {
    upstream = await fetch(`${BACKEND}/resume/score`, {
      method: "POST",
      body: await req.arrayBuffer(),
      headers: { "Content-Type": contentType },
    });
  }

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
