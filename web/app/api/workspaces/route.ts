import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  const root = process.env.WRIST_WORKSPACES_ROOT;
  if (!root || !fs.existsSync(root)) {
    // Return default workspace
    const defaultDir =
      process.env.WRIST_WORKSPACE_DIR ||
      path.join(process.env.HOME || "~", "markdown");
    return NextResponse.json({
      workspaces: [{ name: path.basename(defaultDir), path: defaultDir }],
    });
  }

  const entries = fs.readdirSync(root, { withFileTypes: true });
  const workspaces = entries
    .filter((e) => e.isDirectory())
    .map((e) => ({
      name: e.name,
      path: path.join(root, e.name),
    }));

  return NextResponse.json({ workspaces });
}
