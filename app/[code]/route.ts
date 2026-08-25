import { NextRequest, NextResponse } from "next/server";
import { logClick, resolveShortLink } from "@/lib/shorten";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> },
) {
  const { code } = await params;

  const link = await resolveShortLink(code);

  if (!link) {
    return NextResponse.redirect(new URL("/", request.url), { status: 302 });
  }

  logClick(code, {
    ip: request.headers.get("x-forwarded-for"),
    userAgent: request.headers.get("user-agent"),
    referer: request.headers.get("referer"),
  }).catch((err) => console.error("logClick error:", err));

  return NextResponse.redirect(link.target_url, { status: 302 });
}