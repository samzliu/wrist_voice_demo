"use client";

import { useApp } from "./AppContext";

export function WebViewer() {
  const { state } = useApp();
  const data = state.viewedUrl;

  if (!data) {
    return <div style={styles.empty}>No page loaded</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.urlBar}>
        <span style={styles.urlLabel}>URL:</span>
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          style={styles.url}
        >
          {data.url}
        </a>
      </div>
      <iframe
        src={data.url}
        style={styles.iframe}
        sandbox="allow-scripts allow-same-origin"
        title="Web viewer"
        onError={() => {
          // iframe blocked — fall back handled by content display
        }}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden",
  },
  urlBar: {
    padding: "10px 20px",
    borderBottom: "1px solid #222",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  urlLabel: {
    fontSize: 12,
    color: "#666",
    fontWeight: 600,
  },
  url: {
    fontSize: 13,
    color: "#60a5fa",
    textDecoration: "none",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  iframe: {
    flex: 1,
    border: "none",
    background: "#fff",
  },
  empty: {
    color: "#444",
    fontSize: 14,
    textAlign: "center",
    padding: 40,
  },
};
