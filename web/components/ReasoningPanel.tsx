"use client";

import { useEffect, useRef, useState } from "react";
import { useApp, ReasoningEntry } from "./AppContext";

export function ReasoningPanel() {
  const { state } = useApp();
  const [open, setOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.reasoningLog.length]);

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={styles.toggleClosed}>
        ‹
      </button>
    );
  }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>Activity</span>
        <button onClick={() => setOpen(false)} style={styles.toggleOpen}>
          ›
        </button>
      </div>
      <div style={styles.log}>
        {state.reasoningLog.length === 0 && (
          <div style={styles.empty}>No activity yet</div>
        )}
        {state.reasoningLog.map((entry) => (
          <EntryRow key={entry.id} entry={entry} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function EntryRow({ entry }: { entry: ReasoningEntry }) {
  const [expanded, setExpanded] = useState(false);

  if (entry.kind === "reasoning") {
    return (
      <div style={styles.entry}>
        <span style={styles.reasoningText}>{entry.text}</span>
      </div>
    );
  }

  // tool_call
  return (
    <div style={styles.entry}>
      <div
        style={styles.toolHeader}
        onClick={() => setExpanded(!expanded)}
      >
        <span style={styles.toolIndicator}>
          {entry.done ? "✓" : "⟳"}
        </span>
        <span style={styles.toolName}>{entry.tool}</span>
        {entry.durationMs !== undefined && (
          <span style={styles.duration}>{entry.durationMs}ms</span>
        )}
      </div>
      {expanded && (
        <div style={styles.details}>
          <div style={styles.detailBlock}>
            <span style={styles.detailLabel}>args</span>
            <pre style={styles.pre}>
              {JSON.stringify(entry.args, null, 2)}
            </pre>
          </div>
          {entry.result && (
            <div style={styles.detailBlock}>
              <span style={styles.detailLabel}>result</span>
              <pre style={styles.pre}>{entry.result}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 320,
    minWidth: 320,
    display: "flex",
    flexDirection: "column",
    borderLeft: "1px solid #222",
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
  toggleOpen: {
    background: "none",
    border: "none",
    color: "#666",
    fontSize: 18,
    cursor: "pointer",
    padding: "0 4px",
  },
  toggleClosed: {
    position: "absolute",
    right: 0,
    top: "50%",
    transform: "translateY(-50%)",
    background: "#1a1a1a",
    border: "1px solid #333",
    borderRight: "none",
    color: "#888",
    fontSize: 18,
    cursor: "pointer",
    padding: "12px 6px",
    borderRadius: "4px 0 0 4px",
    zIndex: 10,
  },
  log: {
    flex: 1,
    overflow: "auto",
    padding: "8px 10px",
  },
  empty: {
    color: "#444",
    fontSize: 12,
    textAlign: "center",
    padding: 20,
  },
  entry: {
    marginBottom: 8,
    fontSize: 12,
  },
  reasoningText: {
    color: "#888",
    fontStyle: "italic",
    lineHeight: 1.4,
  },
  toolHeader: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    cursor: "pointer",
    padding: "4px 0",
  },
  toolIndicator: {
    fontSize: 11,
    color: "#4ade80",
  },
  toolName: {
    color: "#c084fc",
    fontFamily: "monospace",
    fontWeight: 600,
  },
  duration: {
    color: "#555",
    fontSize: 11,
    marginLeft: "auto",
  },
  details: {
    marginLeft: 18,
    marginTop: 4,
  },
  detailBlock: {
    marginBottom: 6,
  },
  detailLabel: {
    fontSize: 10,
    color: "#555",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  pre: {
    margin: "2px 0 0 0",
    padding: 6,
    background: "#111",
    borderRadius: 4,
    fontSize: 11,
    color: "#aaa",
    overflow: "auto",
    maxHeight: 200,
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
  },
};
