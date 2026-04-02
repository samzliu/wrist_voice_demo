"use client";

export type Tab = {
  id: string;
  label: string;
  closable?: boolean;
};

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onSelect: (id: string) => void;
  onClose?: (id: string) => void;
}

export function TabBar({ tabs, activeTab, onSelect, onClose }: TabBarProps) {
  return (
    <div style={styles.bar}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onSelect(tab.id)}
          style={{
            ...styles.tab,
            ...(activeTab === tab.id ? styles.activeTab : {}),
          }}
        >
          {tab.label}
          {tab.closable && onClose && (
            <span
              onClick={(e) => {
                e.stopPropagation();
                onClose(tab.id);
              }}
              style={styles.close}
            >
              ×
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    borderBottom: "1px solid #222",
    background: "#0f0f0f",
    flexShrink: 0,
    overflow: "hidden",
  },
  tab: {
    padding: "8px 16px",
    fontSize: 13,
    color: "#666",
    background: "none",
    borderTop: "none",
    borderLeft: "none",
    borderRight: "none",
    borderBottom: "2px solid transparent",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: 6,
    whiteSpace: "nowrap",
  },
  activeTab: {
    color: "#fafafa",
    borderBottom: "2px solid #fafafa",
  },
  close: {
    fontSize: 14,
    color: "#666",
    cursor: "pointer",
    lineHeight: 1,
  },
};
