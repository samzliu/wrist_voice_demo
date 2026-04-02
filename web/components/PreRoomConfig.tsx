"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Script = { name: string; preview: string; content: string };
type Workspace = { name: string; path: string };

interface PreRoomConfigProps {
  onConnect: (scriptContent: string, workspacePath: string) => void;
}

export function PreRoomConfig({ onConnect }: PreRoomConfigProps) {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedScript, setSelectedScript] = useState("");
  const [scriptContent, setScriptContent] = useState("");
  const [selectedWorkspace, setSelectedWorkspace] = useState("");
  const [customScriptName, setCustomScriptName] = useState("");
  const [loading, setLoading] = useState(true);
  const scriptInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

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

  const handleScriptFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setCustomScriptName(file.name.replace(/\.md$/, ""));
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        setScriptContent(text);
        setSelectedScript("__custom__");
      };
      reader.readAsText(file);
    },
    [],
  );

  const handleFolderSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      // webkitRelativePath gives us "foldername/file" — extract the folder
      const firstPath = files[0].webkitRelativePath;
      const folderName = firstPath.split("/")[0];
      // We can't get the absolute path from the browser, so use the folder name
      // and let the backend resolve it
      setSelectedWorkspace(folderName);
    },
    [],
  );

  const handleConnect = useCallback(() => {
    let script = scriptContent;
    if (selectedScript && selectedScript !== "__custom__") {
      const found = scripts.find((s) => s.name === selectedScript);
      if (found) script = found.content;
    }
    onConnect(script, selectedWorkspace);
  }, [scripts, selectedScript, scriptContent, selectedWorkspace, onConnect]);

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

  return (
    <div style={styles.landing}>
      <h1 style={styles.title}>Coworker</h1>
      <p style={styles.subtitle}>
        Voice AI coworking — edit together in real time
      </p>

      <div style={styles.form}>
        {/* Persona / Script */}
        <div style={styles.field}>
          <label style={styles.label}>Persona / Script</label>
          <div style={styles.pickerRow}>
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
                <option value="">None (default)</option>
                {scripts.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={() => scriptInputRef.current?.click()}
              style={styles.fileBtn}
            >
              {activeScriptName ? `📄 ${activeScriptName}` : "Browse .md file..."}
            </button>
            <input
              ref={scriptInputRef}
              type="file"
              accept=".md,.markdown,.txt"
              onChange={handleScriptFile}
              style={{ display: "none" }}
            />
          </div>
          {activeScriptName && (
            <div style={styles.preview}>
              {selectedScript === "__custom__"
                ? scriptContent.split("\n").slice(0, 3).join(" ").slice(0, 200)
                : scripts.find((s) => s.name === selectedScript)?.preview}
            </div>
          )}
        </div>

        {/* Workspace folder */}
        <div style={styles.field}>
          <label style={styles.label}>Workspace Folder</label>
          <div style={styles.pickerRow}>
            {workspaces.length > 0 && (
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
            )}
            <input
              value={
                workspaces.find((w) => w.path === selectedWorkspace)
                  ? ""
                  : selectedWorkspace
              }
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              style={styles.pathInput}
              placeholder="Or type a path..."
            />
          </div>
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
    width: 420,
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
  pickerRow: {
    display: "flex",
    gap: 8,
  },
  select: {
    flex: 1,
    padding: "10px 12px",
    fontSize: 14,
    background: "#111",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#fafafa",
    outline: "none",
  },
  fileBtn: {
    padding: "10px 14px",
    fontSize: 13,
    background: "#1a1a1a",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#aaa",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  pathInput: {
    flex: 1,
    padding: "10px 12px",
    fontSize: 13,
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
