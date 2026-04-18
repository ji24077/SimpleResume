import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    { detail: "Not implemented yet" },
    { status: 501 }
  );
}
