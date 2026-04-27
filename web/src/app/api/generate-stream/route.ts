import { NextRequest, NextResponse } from "next/server";
import { longFetch } from "@/lib/long-fetch";

export const maxDuration = 900; // 15 min — covers worst-case revision loops

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const ct = req.headers.get("content-type") || "";
  let res: Response;

  if (ct.includes("application/json")) {
    const body = await req.text();
    res = await longFetch(`${BACKEND}/generate-json-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
  } else {
    // Forward multipart body as-is (preserves boundary)
    const buf = await req.arrayBuffer();
    res = await longFetch(`${BACKEND}/generate-stream`, {
      method: "POST",
      headers: { "Content-Type": ct },
      body: buf,
    });
  }

  return new NextResponse(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
    },
  });
}
