"use client";

import { useState } from "react";
import { useApp } from "./AppContext";

export function WebViewer() {
  const { state } = useApp();
  const data = state.viewedUrl;
  const [iframeError, setIframeError] = useState(false);
  const [showText, setShowText] = useState(false);

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
        <div style={styles.viewToggle}>
          <button
            onClick={() => setShowText(false)}
            style={{
              ...styles.toggleBtn,
              ...(showText ? {} : styles.toggleActive),
            }}
          >
            Page
          </button>
          <button
            onClick={() => setShowText(true)}
            style={{
              ...styles.toggleBtn,
              ...(showText ? styles.toggleActive : {}),
            }}
          >
            Text
          </button>
        </div>
      </div>
      {showText || iframeError ? (
        <div style={styles.textContent}>
          {data.title && <h2 style={styles.textTitle}>{data.title}</h2>}
          <pre style={styles.textBody}>{data.content}</pre>
        </div>
      ) : (
        <iframe
          src={data.url}
          style={styles.iframe}
          sandbox="allow-scripts allow-same-origin"
          title="Web viewer"
          onLoad={(e) => {
            // Check if iframe loaded successfully
            try {
              const frame = e.target as HTMLIFrameElement;
              // If we can't access contentDocument, it might be blocked
              if (!frame.contentDocument?.body?.innerHTML) {
                setIframeError(true);
              }
            } catch {
              // Cross-origin — iframe loaded but we can't inspect it, that's OK
            }
          }}
          onError={() => setIframeError(true)}
        />
      )}
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
    flexShrink: 0,
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
    flex: 1,
  },
  viewToggle: {
    display: "flex",
    gap: 2,
    marginLeft: "auto",
  },
  toggleBtn: {
    padding: "4px 10px",
    fontSize: 11,
    background: "#1a1a1a",
    border: "1px solid #333",
    color: "#666",
    cursor: "pointer",
    borderRadius: 4,
  },
  toggleActive: {
    background: "#333",
    color: "#fafafa",
  },
  iframe: {
    flex: 1,
    border: "none",
    background: "#fff",
  },
  textContent: {
    flex: 1,
    overflow: "auto",
    padding: 20,
  },
  textTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: "#fafafa",
    marginTop: 0,
    marginBottom: 16,
  },
  textBody: {
    fontSize: 13,
    color: "#ccc",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    margin: 0,
    fontFamily: "inherit",
  },
  empty: {
    color: "#444",
    fontSize: 14,
    textAlign: "center",
    padding: 40,
  },
};
