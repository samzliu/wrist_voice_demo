import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/** GET /api/files?workspace=/path/to/dir&file=doc.md — download a workspace file */
export async function GET(req: NextRequest) {
  const workspace = req.nextUrl.searchParams.get("workspace");
  const file = req.nextUrl.searchParams.get("file");

  if (!workspace || !file) {
    return NextResponse.json({ error: "workspace and file params required" }, { status: 400 });
  }

  const resolved = path.resolve(workspace, file);
  // Prevent path traversal
  if (!resolved.startsWith(path.resolve(workspace))) {
    return NextResponse.json({ error: "invalid path" }, { status: 403 });
  }

  if (!fs.existsSync(resolved)) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }

  const content = fs.readFileSync(resolved);
  const ext = path.extname(file).toLowerCase();
  const mimeTypes: Record<string, string> = {
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".json": "application/json",
  };

  return new NextResponse(content, {
    headers: {
      "Content-Type": mimeTypes[ext] || "application/octet-stream",
      "Content-Disposition": `attachment; filename="${path.basename(file)}"`,
    },
  });
}
