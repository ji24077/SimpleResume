import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const contentType = req.headers.get("content-type") || "";
  let upstream: Response;

  if (contentType.includes("application/json")) {
    upstream = await fetch(`${BACKEND}/generate-json-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await req.text(),
    });
  } else {
    upstream = await fetch(`${BACKEND}/generate-stream`, {
      method: "POST",
      body: await req.arrayBuffer(),
      headers: { "Content-Type": contentType },
    });
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": "application/x-ndjson; charset=utf-8" },
  });
}
