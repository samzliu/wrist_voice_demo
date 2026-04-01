"use client";

import {
  useLocalParticipant,
  useParticipants,
  TrackToggle,
} from "@livekit/components-react";
import { Track } from "livekit-client";

export function VoicePanel({ connected }: { connected: boolean }) {
  const participants = useParticipants();
  const { localParticipant } = useLocalParticipant();

  const agentParticipant = participants.find(
    (p) => p.identity !== localParticipant.identity,
  );

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Coworker</h2>
        <div style={styles.status}>
          <span
            style={{
              ...styles.dot,
              background: connected ? "#4ade80" : "#f87171",
            }}
          />
          {connected ? "Connected" : "Connecting..."}
        </div>
      </div>

      <div style={styles.participants}>
        {/* Agent */}
        <div style={styles.participant}>
          <div style={styles.avatar}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2a3 3 0 0 0-3 3v4a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </div>
          <div>
            <div style={styles.name}>Agent</div>
            <div style={styles.role}>
              {agentParticipant ? "Speaking..." : "Waiting to join..."}
            </div>
          </div>
        </div>

        {/* Human */}
        <div style={styles.participant}>
          <div style={{ ...styles.avatar, background: "#1d4ed8" }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="8" r="5" />
              <path d="M20 21a8 8 0 1 0-16 0" />
            </svg>
          </div>
          <div>
            <div style={styles.name}>You</div>
            <div style={styles.role}>
              {localParticipant.isMicrophoneEnabled ? "Mic on" : "Mic muted"}
            </div>
          </div>
        </div>
      </div>

      <div style={styles.controls}>
        <TrackToggle
          source={Track.Source.Microphone}
          style={styles.micButton}
        />
      </div>

      <div style={styles.footer}>
        <p style={styles.hint}>Click the mic to toggle, or just start talking</p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    padding: 24,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 24,
    fontWeight: 700,
    margin: 0,
  },
  status: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginTop: 8,
    fontSize: 13,
    color: "#888",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
  },
  participants: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
    flex: 1,
  },
  participant: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: 12,
    borderRadius: 8,
    background: "#141414",
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: "50%",
    background: "#166534",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    flexShrink: 0,
  },
  name: {
    fontWeight: 600,
    fontSize: 15,
  },
  role: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  controls: {
    display: "flex",
    justifyContent: "center",
    padding: "24px 0",
  },
  micButton: {
    width: 56,
    height: 56,
    borderRadius: "50%",
    border: "2px solid #333",
    background: "#1a1a1a",
    color: "#fff",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 20,
  },
  footer: {
    borderTop: "1px solid #222",
    paddingTop: 16,
  },
  hint: {
    fontSize: 12,
    color: "#555",
    textAlign: "center" as const,
    margin: 0,
  },
};
