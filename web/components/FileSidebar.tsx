"use client";

import { useCallback, useEffect, useState } from "react";
import { useApp } from "./AppContext";

export function FileSidebar() {
  const { state, sendMessage } = useApp();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [renamingFile, setRenamingFile] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // Request file list on mount
  useEffect(() => {
    if (state.connected) {
      sendMessage({ type: "request_file_list" });
    }
  }, [state.connected, sendMessage]);

  const selectFile = useCallback(
    (name: string) => {
      sendMessage({ type: "request_file_content", file: name });
    },
    [sendMessage],
  );

  const createFile = useCallback(() => {
    if (!newName.trim()) return;
    const name = newName.trim();
    const fileType = name.endsWith(".html") ? "html" : "markdown";
    sendMessage({ type: "file_create", name, file_type: fileType });
    setNewName("");
    setCreating(false);
  }, [newName, sendMessage]);

  const deleteFile = useCallback(
    (name: string) => {
      sendMessage({ type: "file_delete", name });
    },
    [sendMessage],
  );

  const renameFile = useCallback(() => {
    if (!renamingFile || !renameValue.trim()) return;
    sendMessage({
      type: "file_rename",
      old_name: renamingFile,
      new_name: renameValue.trim(),
    });
    setRenamingFile(null);
    setRenameValue("");
  }, [renamingFile, renameValue, sendMessage]);

  const fileIcon = (type: string) => {
    if (type === "html") return "◻";
    if (type === "markdown") return "¶";
    return "○";
  };

  return (
    <div style={styles.sidebar}>
      <div style={styles.header}>
        <span style={styles.title}>Files</span>
        <button
          onClick={() => setCreating(!creating)}
          style={styles.addBtn}
          title="New file"
        >
          +
        </button>
      </div>

      {creating && (
        <div style={styles.createRow}>
          <input
            style={styles.input}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createFile()}
            placeholder="filename.md"
            autoFocus
          />
        </div>
      )}

      <div style={styles.list}>
        {state.fileList.map((f) => (
          <div
            key={f.name}
            style={{
              ...styles.fileRow,
              ...(state.activeFile?.name === f.name ? styles.active : {}),
            }}
            onClick={() => selectFile(f.name)}
          >
            {renamingFile === f.name ? (
              <input
                style={styles.input}
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") renameFile();
                  if (e.key === "Escape") setRenamingFile(null);
                }}
                onClick={(e) => e.stopPropagation()}
                autoFocus
              />
            ) : (
              <>
                <span style={styles.icon}>{fileIcon(f.type)}</span>
                <span style={styles.fileName}>{f.name}</span>
                <div style={styles.actions}>
                  <button
                    style={styles.actionBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      setRenamingFile(f.name);
                      setRenameValue(f.name);
                    }}
                    title="Rename"
                  >
                    ✎
                  </button>
                  <button
                    style={styles.actionBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteFile(f.name);
                    }}
                    title="Delete"
                  >
                    ×
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
        {state.fileList.length === 0 && (
          <div style={styles.empty}>No files</div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: 240,
    minWidth: 240,
    display: "flex",
    flexDirection: "column",
    borderRight: "1px solid #222",
    background: "#0a0a0a",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 14px",
    borderBottom: "1px solid #222",
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: "#888",
  },
  addBtn: {
    background: "none",
    border: "1px solid #333",
    color: "#888",
    fontSize: 16,
    cursor: "pointer",
    borderRadius: 4,
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    lineHeight: 1,
  },
  createRow: {
    padding: "6px 10px",
    borderBottom: "1px solid #1a1a1a",
  },
  list: {
    flex: 1,
    overflow: "auto",
    padding: "4px 0",
  },
  fileRow: {
    display: "flex",
    alignItems: "center",
    padding: "6px 14px",
    cursor: "pointer",
    gap: 8,
    fontSize: 13,
    color: "#ccc",
  },
  active: {
    background: "#1a1a1a",
    color: "#fafafa",
  },
  icon: {
    fontSize: 12,
    color: "#555",
    width: 16,
    textAlign: "center",
    flexShrink: 0,
  },
  fileName: {
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  actions: {
    display: "flex",
    gap: 2,
    opacity: 0.4,
  },
  actionBtn: {
    background: "none",
    border: "none",
    color: "#888",
    cursor: "pointer",
    fontSize: 13,
    padding: "0 3px",
  },
  input: {
    width: "100%",
    padding: "4px 8px",
    fontSize: 12,
    background: "#111",
    border: "1px solid #333",
    borderRadius: 3,
    color: "#fafafa",
    outline: "none",
  },
  empty: {
    color: "#444",
    fontSize: 12,
    textAlign: "center",
    padding: 20,
  },
};
