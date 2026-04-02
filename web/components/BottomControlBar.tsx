"use client";

import {
  TrackToggle,
  useLocalParticipant,
  useParticipants,
} from "@livekit/components-react";
import { Track } from "livekit-client";
import { useApp } from "./AppContext";

export function BottomControlBar() {
  const { state, dispatch, sendMessage } = useApp();
  const participants = useParticipants();
  const { localParticipant } = useLocalParticipant();

  const agentParticipant = participants.find(
    (p) => p.identity !== localParticipant.identity,
  );
  const agentSpeaking = agentParticipant?.isSpeaking ?? false;
  const userSpeaking = localParticipant.isSpeaking;
  const micOn = localParticipant.isMicrophoneEnabled;

  // Determine turn state
  let turnLabel = "";
  let turnColor = "#555";
  if (state.agentPaused) {
    turnLabel = "Paused";
    turnColor = "#f87171";
  } else if (state.agentState === "thinking") {
    turnLabel = "Thinking...";
    turnColor = "#f59e0b";
  } else if (agentSpeaking) {
    turnLabel = "Agent speaking";
    turnColor = "#4ade80";
  } else if (userSpeaking) {
    turnLabel = "Listening...";
    turnColor = "#60a5fa";
  } else if (!agentParticipant) {
    turnLabel = "Waiting for agent...";
    turnColor = "#666";
  } else {
    turnLabel = "Waiting for you";
    turnColor = "#888";
  }

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
      {/* Left: connection + turn indicator */}
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
        <span style={styles.separator}>·</span>
        <span
          style={{
            ...styles.turnIndicator,
            background: turnColor + "22",
            borderColor: turnColor + "44",
            color: turnColor,
          }}
        >
          <span
            style={{
              ...styles.turnDot,
              background: turnColor,
              ...(agentSpeaking || userSpeaking
                ? { animation: "pulse 1s infinite" }
                : {}),
            }}
          />
          {turnLabel}
        </span>
        {!micOn && state.connected && (
          <span style={styles.micOff}>Mic off</span>
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

      {/* Inject keyframes for pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
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
  separator: {
    color: "#444",
    fontSize: 14,
  },
  turnIndicator: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    fontSize: 12,
    fontWeight: 500,
    padding: "3px 10px",
    borderRadius: 12,
    border: "1px solid",
  },
  turnDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    flexShrink: 0,
  },
  micOff: {
    fontSize: 11,
    color: "#f87171",
    marginLeft: 4,
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
