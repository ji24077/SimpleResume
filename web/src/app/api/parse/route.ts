import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const ct = req.headers.get("content-type") || "";
  let res: Response;

  if (ct.includes("application/json")) {
    const body = await req.json();
    const form = new FormData();
    if (typeof body.text === "string") form.append("text", body.text);
    if (typeof body.contact_email === "string") form.append("contact_email", body.contact_email);
    if (typeof body.contact_linkedin === "string")
      form.append("contact_linkedin", body.contact_linkedin);
    if (typeof body.contact_phone === "string") form.append("contact_phone", body.contact_phone);
    res = await fetch(`${BACKEND}/resume/parse`, { method: "POST", body: form });
  } else {
    const form = await req.formData();
    res = await fetch(`${BACKEND}/resume/parse`, { method: "POST", body: form });
  }

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") || "application/json",
    },
  });
}
