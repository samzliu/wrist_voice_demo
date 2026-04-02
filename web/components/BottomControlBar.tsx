"use client";

import { TrackToggle } from "@livekit/components-react";
import { Track } from "livekit-client";
import { useApp } from "./AppContext";

export function BottomControlBar() {
  const { state, dispatch, sendMessage } = useApp();

  const togglePause = () => {
    const next = !state.agentPaused;
    dispatch({ type: "SET_PAUSED", value: next });
    sendMessage({ type: next ? "pause" : "resume" });
  };

  const toggleMonologue = () => {
    const next = !state.monologue;
    dispatch({ type: "SET_MONOLOGUE", value: next });
    sendMessage({ type: next ? "monologue_on" : "monologue_off" });
  };

  return (
    <div style={styles.bar}>
      {/* Left: connection status */}
      <div style={styles.left}>
        <span
          style={{
            ...styles.dot,
            background: state.connected ? "#4ade80" : "#f87171",
          }}
        />
        <span style={styles.statusText}>
          {state.connected ? "Connected" : "Connecting..."}
        </span>
        {state.agentState !== "active" && (
          <span style={styles.agentStatus}>
            {state.agentState === "paused" ? "Paused" : "Thinking..."}
          </span>
        )}
      </div>

      {/* Center: controls */}
      <div style={styles.center}>
        <TrackToggle
          source={Track.Source.Microphone}
          style={styles.micBtn}
        />
        <button
          onClick={togglePause}
          style={{
            ...styles.controlBtn,
            background: state.agentPaused ? "#f87171" : "#333",
          }}
          title={state.agentPaused ? "Resume agent" : "Pause agent"}
        >
          {state.agentPaused ? "▶" : "⏸"}
        </button>
        <button
          onClick={toggleMonologue}
          style={{
            ...styles.controlBtn,
            background: state.monologue ? "#f59e0b" : "#333",
          }}
          title={state.monologue ? "End monologue" : "Monologue mode"}
        >
          {state.monologue ? "🔊" : "📝"}
        </button>
      </div>

      {/* Right: spacer */}
      <div style={styles.right} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    alignItems: "center",
    height: 56,
    padding: "0 20px",
    background: "#111",
    borderTop: "1px solid #222",
    flexShrink: 0,
  },
  left: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    flex: 1,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  },
  statusText: {
    fontSize: 13,
    color: "#888",
  },
  agentStatus: {
    fontSize: 12,
    color: "#f59e0b",
    marginLeft: 8,
  },
  center: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  micBtn: {
    width: 44,
    height: 44,
    borderRadius: "50%",
    border: "none",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
  },
  controlBtn: {
    width: 44,
    height: 44,
    borderRadius: "50%",
    border: "none",
    color: "#fafafa",
    cursor: "pointer",
    fontSize: 16,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  right: {
    flex: 1,
  },
};
