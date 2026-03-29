import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const ct = req.headers.get("content-type") || "";
  let res: Response;

  if (ct.includes("application/json")) {
    const body = await req.json();
    res = await fetch(`${BACKEND}/generate-json-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } else {
    const form = await req.formData();
    res = await fetch(`${BACKEND}/generate-stream`, {
      method: "POST",
      body: form,
    });
  }

  return new NextResponse(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
    },
  });
}
