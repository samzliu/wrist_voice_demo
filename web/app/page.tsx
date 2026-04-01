"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react";
import { RoomEvent, RemoteParticipant } from "livekit-client";
import { VoicePanel } from "@/components/VoicePanel";
import { SlideViewer } from "@/components/SlideViewer";
import { parseSlides } from "@/lib/slideUtils";

const decoder = new TextDecoder();
const encoder = new TextEncoder();

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL!;

  const connect = useCallback(async () => {
    const res = await fetch("/api/token?room=onboarding-room&identity=human", { cache: "no-store" });
    const data = await res.json();
    setToken(data.token);
  }, []);

  if (!token) {
    return (
      <div style={styles.landing}>
        <h1 style={styles.title}>OpenClaw</h1>
        <p style={styles.subtitle}>Meet your AI agent team</p>
        <button onClick={connect} style={styles.connectBtn}>
          Start Onboarding
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
  const [slides, setSlides] = useState<string[]>([]);
  const [currentSlide, setCurrentSlide] = useState(0);

  // Listen for data messages from the agent
  useEffect(() => {
    const handler = (
      payload: Uint8Array,
      participant: RemoteParticipant | undefined,
    ) => {
      try {
        const msg = JSON.parse(decoder.decode(payload));

        switch (msg.type) {
          case "deck_sync": {
            const parsed = parseSlides(msg.html);
            setSlides(parsed);
            break;
          }
          case "go_to_slide": {
            // msg.slide is 1-indexed from agent
            setCurrentSlide(msg.slide - 1);
            break;
          }
          case "slide_updated": {
            setSlides((prev) => {
              const next = [...prev];
              const idx = msg.slide - 1;
              if (idx >= 0 && idx < next.length) {
                next[idx] = msg.html;
              }
              return next;
            });
            break;
          }
          case "slide_created": {
            setSlides((prev) => {
              const next = [...prev];
              const idx = msg.position - 1;
              next.splice(idx, 0, msg.html);
              return next;
            });
            break;
          }
          case "slide_deleted": {
            setSlides((prev) => {
              const next = [...prev];
              const idx = msg.slide - 1;
              if (idx >= 0 && idx < next.length) {
                next.splice(idx, 1);
              }
              return next;
            });
            break;
          }
        }
      } catch {}
    };
    room.on(RoomEvent.DataReceived, handler);
    return () => {
      room.off(RoomEvent.DataReceived, handler);
    };
  }, [room]);

  // When the human navigates, notify the agent
  const onSlideChange = useCallback(
    (slideIndex: number) => {
      setCurrentSlide(slideIndex);
      const msg = JSON.stringify({
        type: "human_navigate",
        slide: slideIndex + 1,
      });
      room.localParticipant
        .publishData(encoder.encode(msg), { reliable: true })
        .catch(() => {});
    },
    [room],
  );

  // Fetch the initial deck HTML on mount
  useEffect(() => {
    fetch("/api/deck")
      .then((r) => r.text())
      .then((html) => {
        const parsed = parseSlides(html);
        if (parsed.length > 0) {
          setSlides(parsed);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div style={styles.container}>
      <div style={styles.leftPanel}>
        <VoicePanel connected={connected} />
      </div>
      <div style={styles.divider} />
      <div style={styles.rightPanel}>
        <SlideViewer
          slides={slides}
          currentSlide={currentSlide}
          onSlideChange={onSlideChange}
        />
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
    width: 320,
    minWidth: 280,
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
};
