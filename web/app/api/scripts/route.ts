import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  const scriptsDir = process.env.WRIST_SCRIPTS_DIR;
  if (!scriptsDir || !fs.existsSync(scriptsDir)) {
    return NextResponse.json({ scripts: [] });
  }

  const files = fs.readdirSync(scriptsDir).filter((f) => f.endsWith(".md"));
  const scripts = files.map((f) => {
    const content = fs.readFileSync(path.join(scriptsDir, f), "utf-8");
    const lines = content.split("\n").filter(Boolean);
    return {
      name: f.replace(/\.md$/, ""),
      preview: lines.slice(0, 3).join(" ").slice(0, 200),
      content,
    };
  });

  return NextResponse.json({ scripts });
}
