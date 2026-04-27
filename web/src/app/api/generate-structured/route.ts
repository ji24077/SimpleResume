import { NextRequest, NextResponse } from "next/server";
import { longFetch } from "@/lib/long-fetch";

export const maxDuration = 900;

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await longFetch(`${BACKEND}/resume/generate-from-structured`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  return new NextResponse(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
    },
  });
}
