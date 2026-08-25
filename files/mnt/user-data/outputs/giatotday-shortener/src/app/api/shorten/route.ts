import { NextRequest, NextResponse } from "next/server";
import { createShortLink } from "@/lib/shorten";

export async function POST(request: NextRequest) {
  const apiKey = request.headers.get("x-api-key");
  if (!apiKey || apiKey !== process.env.SHORTENER_API_KEY) {
    return NextResponse.json({ status: "error", message: "Unauthorized" }, { status: 401 });
  }

  let body: {
    targetUrl?: string;
    itemId?: string;
    source?: string;
    meta?: Record<string, unknown>;
  };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ status: "error", message: "Body JSON không hợp lệ" }, { status: 400 });
  }

  if (!body.targetUrl) {
    return NextResponse.json({ status: "error", message: "Thiếu targetUrl" }, { status: 400 });
  }

  try {
    const link = await createShortLink({
      targetUrl: body.targetUrl,
      itemId: body.itemId,
      source: body.source,
      meta: body.meta,
    });

    const shortUrl = `${process.env.SHORTENER_PUBLIC_BASE_URL}/affiliate/${link.code}`;

    return NextResponse.json({ status: "success", code: link.code, shortUrl });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Lỗi không xác định";
    return NextResponse.json({ status: "error", message }, { status: 400 });
  }
}
