"use client";

import { useCallback, useEffect, useState } from "react";

type Script = { name: string; preview: string; content: string };
type Workspace = { name: string; path: string };

interface PreRoomConfigProps {
  onConnect: (scriptContent: string, workspacePath: string) => void;
}

export function PreRoomConfig({ onConnect }: PreRoomConfigProps) {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedScript, setSelectedScript] = useState("");
  const [selectedWorkspace, setSelectedWorkspace] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/scripts")
        .then((r) => r.json())
        .then((d) => setScripts(d.scripts || []))
        .catch(() => {}),
      fetch("/api/workspaces")
        .then((r) => r.json())
        .then((d) => {
          const ws = d.workspaces || [];
          setWorkspaces(ws);
          if (ws.length > 0) setSelectedWorkspace(ws[0].path);
        })
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const handleConnect = useCallback(() => {
    const script = scripts.find((s) => s.name === selectedScript);
    onConnect(script?.content || "", selectedWorkspace);
  }, [scripts, selectedScript, selectedWorkspace, onConnect]);

  if (loading) {
    return (
      <div style={styles.landing}>
        <div style={styles.spinner}>Loading...</div>
      </div>
    );
  }

  return (
    <div style={styles.landing}>
      <h1 style={styles.title}>Coworker</h1>
      <p style={styles.subtitle}>Voice AI coworking — edit together in real time</p>

      <div style={styles.form}>
        {/* Persona / Script selector */}
        <div style={styles.field}>
          <label style={styles.label}>Persona / Script</label>
          <select
            value={selectedScript}
            onChange={(e) => setSelectedScript(e.target.value)}
            style={styles.select}
          >
            <option value="">None (default assistant)</option>
            {scripts.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
          {selectedScript && (
            <div style={styles.preview}>
              {scripts.find((s) => s.name === selectedScript)?.preview}
            </div>
          )}
        </div>

        {/* Workspace selector */}
        <div style={styles.field}>
          <label style={styles.label}>Workspace</label>
          {workspaces.length > 0 ? (
            <select
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              style={styles.select}
            >
              {workspaces.map((w) => (
                <option key={w.path} value={w.path}>
                  {w.name}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              style={styles.input}
              placeholder="~/markdown"
            />
          )}
        </div>
      </div>

      <button onClick={handleConnect} style={styles.connectBtn}>
        Connect
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  landing: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    background: "#0a0a0a",
    color: "#fafafa",
  },
  title: {
    fontSize: 48,
    fontWeight: 700,
    margin: 0,
  },
  subtitle: {
    fontSize: 18,
    color: "#888",
    marginTop: 8,
    marginBottom: 32,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 20,
    width: 360,
    marginBottom: 32,
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: 600,
    color: "#888",
  },
  select: {
    padding: "10px 12px",
    fontSize: 14,
    background: "#111",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#fafafa",
    outline: "none",
  },
  input: {
    padding: "10px 12px",
    fontSize: 14,
    background: "#111",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#fafafa",
    outline: "none",
  },
  preview: {
    fontSize: 12,
    color: "#666",
    padding: "8px 10px",
    background: "#0f0f0f",
    borderRadius: 4,
    maxHeight: 60,
    overflow: "hidden",
    lineHeight: 1.4,
  },
  connectBtn: {
    padding: "14px 40px",
    fontSize: 16,
    fontWeight: 600,
    background: "#fff",
    color: "#000",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
  },
  spinner: {
    color: "#666",
    fontSize: 16,
  },
};
