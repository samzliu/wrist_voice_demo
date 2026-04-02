"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react";
import { RoomEvent, RemoteParticipant } from "livekit-client";
import { VoicePanel } from "@/components/VoicePanel";
import { MarkdownEditor } from "@/components/MarkdownEditor";

const decoder = new TextDecoder();
const encoder = new TextEncoder();

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL!;

  const connect = useCallback(async () => {
    const roomId = `coworker-${Date.now()}`;
    const res = await fetch(`/api/token?room=${roomId}&identity=human`);
    const data = await res.json();
    setToken(data.token);
  }, []);

  if (!token) {
    return (
      <div style={styles.landing}>
        <h1 style={styles.title}>Coworker</h1>
        <p style={styles.subtitle}>Voice AI coworking — edit together in real time</p>
        <button onClick={connect} style={styles.connectBtn}>
          Connect
        </button>
      </div>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={livekitUrl}
      token={token}
      connect={true}
      audio={true}
      onConnected={() => setConnected(true)}
      onDisconnected={() => setConnected(false)}
      style={styles.room}
    >
      <RoomAudioRenderer />
      <AppContent connected={connected} />
    </LiveKitRoom>
  );
}

function AppContent({ connected }: { connected: boolean }) {
  const room = useRoomContext();
  const [doc, setDoc] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");
  const [monologue, setMonologue] = useState(false);
  const suppressEcho = useRef(false);

  // Listen for data messages from the agent
  useEffect(() => {
    const handler = (
      payload: Uint8Array,
      participant: RemoteParticipant | undefined,
    ) => {
      try {
        const msg = JSON.parse(decoder.decode(payload));
        if (msg.type === "doc_update" && !suppressEcho.current) {
          setDoc(msg.content);
          if (msg.file) setFileName(msg.file);
        }
      } catch {}
    };
    room.on(RoomEvent.DataReceived, handler);
    return () => { room.off(RoomEvent.DataReceived, handler); };
  }, [room]);

  // Send human edits to agent
  const onEditorChange = useCallback(
    (content: string) => {
      setDoc(content);
      suppressEcho.current = true;
      const msg = JSON.stringify({ type: "human_edit", content, file: fileName });
      room.localParticipant
        .publishData(encoder.encode(msg), { reliable: true })
        .finally(() => {
          suppressEcho.current = false;
        });
    },
    [room, fileName],
  );

  const toggleMonologue = useCallback(() => {
    const next = !monologue;
    setMonologue(next);
    const msg = JSON.stringify({ type: next ? "monologue_on" : "monologue_off" });
    room.localParticipant.publishData(encoder.encode(msg), { reliable: true });
  }, [room, monologue]);

  return (
    <div style={styles.container}>
      <div style={styles.leftPanel}>
        <VoicePanel
          connected={connected}
          monologue={monologue}
          onToggleMonologue={toggleMonologue}
        />
      </div>
      <div style={styles.divider} />
      <div style={styles.rightPanel}>
        <div style={styles.fileHeader}>
          {fileName ? fileName : "Waiting for agent to open a file..."}
        </div>
        <MarkdownEditor content={doc} onChange={onEditorChange} />
      </div>
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
  room: {
    height: "100vh",
    background: "#0a0a0a",
  },
  container: {
    display: "flex",
    height: "100vh",
    background: "#0a0a0a",
    color: "#fafafa",
  },
  leftPanel: {
    width: 360,
    minWidth: 320,
    display: "flex",
    flexDirection: "column",
    borderRight: "1px solid #222",
  },
  divider: {
    width: 1,
    background: "#222",
  },
  rightPanel: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  fileHeader: {
    padding: "12px 20px",
    fontSize: 13,
    fontWeight: 600,
    color: "#888",
    borderBottom: "1px solid #222",
    fontFamily: "monospace",
  },
};
