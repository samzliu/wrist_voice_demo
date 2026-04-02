"use client";

import { useApp } from "./AppContext";

export function SearchResults() {
  const { state } = useApp();
  const data = state.searchResults;

  if (!data) {
    return <div style={styles.empty}>No search results</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.queryBar}>
        <span style={styles.queryLabel}>Search:</span>
        <span style={styles.queryText}>{data.query}</span>
      </div>
      <div style={styles.results}>
        {data.results.map((r, i) => (
          <div key={i} style={styles.card}>
            <a
              href={r.url}
              target="_blank"
              rel="noopener noreferrer"
              style={styles.title}
            >
              {r.title}
            </a>
            <div style={styles.url}>{r.url}</div>
            <div style={styles.snippet}>{r.snippet}</div>
          </div>
        ))}
        {data.results.length === 0 && (
          <div style={styles.empty}>No results found</div>
        )}
      </div>
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
  queryBar: {
    padding: "12px 20px",
    borderBottom: "1px solid #222",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  queryLabel: {
    fontSize: 12,
    color: "#666",
    fontWeight: 600,
  },
  queryText: {
    fontSize: 14,
    color: "#fafafa",
  },
  results: {
    flex: 1,
    overflow: "auto",
    padding: 16,
  },
  card: {
    padding: 16,
    marginBottom: 12,
    background: "#111",
    borderRadius: 8,
    border: "1px solid #222",
  },
  title: {
    fontSize: 15,
    fontWeight: 600,
    color: "#60a5fa",
    textDecoration: "none",
    display: "block",
    marginBottom: 4,
  },
  url: {
    fontSize: 12,
    color: "#555",
    marginBottom: 8,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  snippet: {
    fontSize: 13,
    color: "#aaa",
    lineHeight: 1.5,
  },
  empty: {
    color: "#444",
    fontSize: 14,
    textAlign: "center",
    padding: 40,
  },
};
