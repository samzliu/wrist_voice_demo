"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Script = { name: string; preview: string; content: string };
type Workspace = { name: string; path: string };
type EnvMode = "local" | "server";

export type SessionMode = "workspace" | "chat";

interface PreRoomConfigProps {
  onConnect: (
    scriptContent: string,
    workspacePath: string,
    mode: SessionMode,
  ) => void;
}

export function PreRoomConfig({ onConnect }: PreRoomConfigProps) {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [envMode, setEnvMode] = useState<EnvMode>("server");
  const [selectedScript, setSelectedScript] = useState("");
  const [scriptContent, setScriptContent] = useState("");
  const [workspacePath, setWorkspacePath] = useState("");
  const [customScriptName, setCustomScriptName] = useState("");
  const [mode, setMode] = useState<SessionMode>("workspace");
  const [loading, setLoading] = useState(true);
  const scriptInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/scripts")
        .then((r) => r.json())
        .then((d) => {
          const s = d.scripts || [];
          setScripts(s);
          // Auto-select first script as default if available
          if (s.length > 0) setSelectedScript(s[0].name);
        })
        .catch(() => {}),
      fetch("/api/workspaces")
        .then((r) => r.json())
        .then((d) => {
          const ws = d.workspaces || [];
          setWorkspaces(ws);
          setEnvMode(d.mode || "server");
          if (ws.length > 0) setWorkspacePath(ws[0].path);
        })
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const handleScriptFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setCustomScriptName(file.name.replace(/\.md$/, ""));
      const reader = new FileReader();
      reader.onload = () => {
        setScriptContent(reader.result as string);
        setSelectedScript("__custom__");
      };
      reader.readAsText(file);
    },
    [],
  );

  const handleConnect = useCallback(() => {
    let script = scriptContent;
    if (selectedScript && selectedScript !== "__custom__") {
      const found = scripts.find((s) => s.name === selectedScript);
      if (found) script = found.content;
    }
    // In server mode or chat mode, send empty workspace path — agent creates temp dir
    const ws = mode === "workspace" && envMode === "local" ? workspacePath : "";
    onConnect(script, ws, mode);
  }, [scripts, selectedScript, scriptContent, workspacePath, mode, envMode, onConnect]);

  if (loading) {
    return (
      <div style={styles.landing}>
        <div style={styles.spinner}>Loading...</div>
      </div>
    );
  }

  const activeScriptName =
    selectedScript === "__custom__"
      ? customScriptName
      : selectedScript || null;

  const showWorkspacePicker = mode === "workspace" && envMode === "local";

  return (
    <div style={styles.landing}>
      <h1 style={styles.title}>Coworker</h1>
      <p style={styles.subtitle}>
        Voice AI coworking — edit together in real time
      </p>

      <div style={styles.form}>
        {/* Mode toggle */}
        <div style={styles.field}>
          <label style={styles.label}>Mode</label>
          <div style={styles.modeRow}>
            <button
              onClick={() => setMode("workspace")}
              style={{
                ...styles.modeBtn,
                ...(mode === "workspace" ? styles.modeBtnActive : {}),
              }}
            >
              <span style={styles.modeIcon}>📁</span>
              <span>Workspace</span>
              <span style={styles.modeDesc}>
                Files, slides, search, editing
              </span>
            </button>
            <button
              onClick={() => setMode("chat")}
              style={{
                ...styles.modeBtn,
                ...(mode === "chat" ? styles.modeBtnActive : {}),
              }}
            >
              <span style={styles.modeIcon}>💬</span>
              <span>Chat</span>
              <span style={styles.modeDesc}>
                Voice only — roleplay, practice, discuss
              </span>
            </button>
          </div>
        </div>

        {/* Persona / Script */}
        <div style={styles.field}>
          <label style={styles.label}>
            {mode === "chat" ? "Role / Script" : "Persona / Script"}
          </label>
          {scripts.length > 0 && (
            <select
              value={selectedScript === "__custom__" ? "" : selectedScript}
              onChange={(e) => {
                setSelectedScript(e.target.value);
                setScriptContent("");
                setCustomScriptName("");
              }}
              style={styles.select}
            >
              <option value="">
                {mode === "chat" ? "None (freeform)" : "None (default)"}
              </option>
              {scripts.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          )}
          <label style={styles.uploadLabel}>
            <input
              ref={scriptInputRef}
              type="file"
              accept=".md,.markdown,.txt"
              onChange={handleScriptFile}
              style={styles.hiddenInput}
            />
            <span style={{
              ...styles.uploadBtn,
              ...(selectedScript === "__custom__" ? styles.uploadBtnLoaded : {}),
            }}>
              {selectedScript === "__custom__"
                ? `Loaded: ${customScriptName}`
                : "Upload a .md file"}
            </span>
          </label>
          {activeScriptName && (
            <div style={styles.preview}>
              {selectedScript === "__custom__"
                ? scriptContent.split("\n").slice(0, 3).join(" ").slice(0, 200)
                : scripts.find((s) => s.name === selectedScript)?.preview}
            </div>
          )}
        </div>

        {/* Workspace folder — only in workspace mode + local env */}
        {showWorkspacePicker && (
          <div style={styles.field}>
            <label style={styles.label}>Workspace Folder</label>
            {workspaces.length > 0 && (
              <select
                value={
                  workspaces.find((w) => w.path === workspacePath)
                    ? workspacePath
                    : "__custom__"
                }
                onChange={(e) => {
                  if (e.target.value !== "__custom__") {
                    setWorkspacePath(e.target.value);
                  }
                }}
                style={{ ...styles.select, marginBottom: 6 }}
              >
                {workspaces.map((w) => (
                  <option key={w.path} value={w.path}>
                    {w.name} — {w.path}
                  </option>
                ))}
                <option value="__custom__">Custom path...</option>
              </select>
            )}
            <input
              value={workspacePath}
              onChange={(e) => setWorkspacePath(e.target.value)}
              style={styles.pathInput}
              placeholder="/absolute/path/to/folder"
            />
          </div>
        )}

        {/* Server mode info */}
        {mode === "workspace" && envMode === "server" && (
          <div style={styles.serverNote}>
            A temporary workspace will be created for this session. Use the
            download button to save your files before disconnecting.
          </div>
        )}
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
    width: 480,
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
  modeRow: {
    display: "flex",
    gap: 10,
  },
  modeBtn: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: 4,
    padding: "14px 12px",
    background: "#111",
    border: "2px solid #222",
    borderRadius: 10,
    color: "#888",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
  },
  modeBtnActive: {
    borderColor: "#fafafa",
    color: "#fafafa",
    background: "#1a1a1a",
  },
  modeIcon: {
    fontSize: 22,
  },
  modeDesc: {
    fontSize: 11,
    fontWeight: 400,
    color: "#555",
    marginTop: 2,
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
  uploadLabel: {
    cursor: "pointer",
  },
  hiddenInput: {
    position: "absolute" as const,
    width: 1,
    height: 1,
    opacity: 0,
    overflow: "hidden",
  },
  uploadBtn: {
    display: "block",
    padding: "10px 14px",
    fontSize: 13,
    background: "#1a1a1a",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#aaa",
    textAlign: "center" as const,
  },
  uploadBtnLoaded: {
    background: "#0f2a1a",
    borderColor: "#166534",
    color: "#4ade80",
  },
  pathInput: {
    padding: "10px 12px",
    fontSize: 13,
    background: "#111",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#fafafa",
    outline: "none",
    fontFamily: "monospace",
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
  serverNote: {
    fontSize: 12,
    color: "#888",
    padding: "10px 14px",
    background: "#111",
    borderRadius: 6,
    border: "1px solid #222",
    lineHeight: 1.5,
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
