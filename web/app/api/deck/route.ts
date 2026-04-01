import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

export async function GET() {
  const deckDir = process.env.WRIST_DECK_DIR ?? join(process.env.HOME ?? "~", "slides");
  const deckPath = join(deckDir, "onboarding.html");

  try {
    const html = await readFile(deckPath, "utf-8");
    return new NextResponse(html, {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  } catch {
    return new NextResponse("<!-- No deck found -->", {
      status: 404,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }
}
