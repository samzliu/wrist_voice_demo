import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  const root = process.env.WRIST_WORKSPACES_ROOT;
  const workspaceDir = process.env.WRIST_WORKSPACE_DIR;

  // If a workspaces root or specific dir is configured, we're running locally
  if (root && fs.existsSync(root)) {
    const entries = fs.readdirSync(root, { withFileTypes: true });
    const workspaces = entries
      .filter((e) => e.isDirectory())
      .map((e) => ({
        name: e.name,
        path: path.join(root, e.name),
      }));
    return NextResponse.json({ workspaces, mode: "local" });
  }

  if (workspaceDir) {
    const defaultDir = path.resolve(workspaceDir);
    return NextResponse.json({
      workspaces: [{ name: path.basename(defaultDir), path: defaultDir }],
      mode: "local",
    });
  }

  // No workspace configured — server mode, agent creates a temp session workspace
  return NextResponse.json({ workspaces: [], mode: "server" });
}
