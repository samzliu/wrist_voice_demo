"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react";
import { Room, RoomEvent, ConnectionState } from "livekit-client";
import { AppProvider, useApp } from "@/components/AppContext";
import { PreRoomConfig, SessionMode } from "@/components/PreRoomConfig";
import { FileSidebar } from "@/components/FileSidebar";
import { MainContent } from "@/components/MainContent";
import { ReasoningPanel } from "@/components/ReasoningPanel";
import { BottomControlBar } from "@/components/BottomControlBar";

const encoder = new TextEncoder();

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const configRef = useRef<{ script: string; workspace: string; mode: SessionMode }>({
    script: "",
    workspace: "",
    mode: "workspace",
  });
  const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL!;

  const connect = useCallback(
    async (scriptContent: string, workspacePath: string, mode: SessionMode) => {
      configRef.current = { script: scriptContent, workspace: workspacePath, mode };
      const roomId = `coworker-${Date.now()}`;
      const res = await fetch(`/api/token?room=${roomId}&identity=human`);
      const data = await res.json();
      setToken(data.token);
    },
    [],
  );

  const onRoomConnected = useCallback(
    (room: Room) => {
      const msg = JSON.stringify({
        type: "config",
        script_content: configRef.current.script,
        workspace_path: configRef.current.workspace,
        mode: configRef.current.mode,
      });
      room.localParticipant.publishData(encoder.encode(msg), {
        reliable: true,
      });
    },
    [],
  );

  if (!token) {
    return <PreRoomConfig onConnect={connect} />;
  }

  return (
    <LiveKitRoom
      serverUrl={livekitUrl}
      token={token}
      connect={true}
      audio={true}
      onConnected={() => {
        // Need room ref from context — handled in AppShell
      }}
      style={styles.room}
    >
      <RoomAudioRenderer />
      <AppProvider>
        <AppShell onRoomConnected={onRoomConnected} mode={configRef.current.mode} />
      </AppProvider>
    </LiveKitRoom>
  );
}

function AppShell({
  onRoomConnected,
  mode,
}: {
  onRoomConnected: (room: Room) => void;
  mode: SessionMode;
}) {
  const { dispatch } = useApp();
  const room = useRoomContext();
  const sentConfig = useRef(false);

  useEffect(() => {
    const onConnected = () => {
      dispatch({ type: "SET_CONNECTED", value: true });
    };

    const onParticipantConnected = () => {
      if (!sentConfig.current) {
        sentConfig.current = true;
        onRoomConnected(room);
      }
    };

    if (room.state === ConnectionState.Connected) {
      onConnected();
      if (room.remoteParticipants.size > 0 && !sentConfig.current) {
        sentConfig.current = true;
        onRoomConnected(room);
      }
    }

    room.on(RoomEvent.Connected, onConnected);
    room.on(RoomEvent.ParticipantConnected, onParticipantConnected);
    return () => {
      room.off(RoomEvent.Connected, onConnected);
      room.off(RoomEvent.ParticipantConnected, onParticipantConnected);
    };
  }, [room, dispatch, onRoomConnected]);

  if (mode === "chat") {
    return (
      <div style={styles.shell}>
        <div style={styles.content}>
          <ReasoningPanel />
        </div>
        <BottomControlBar />
      </div>
    );
  }

  return (
    <div style={styles.shell}>
      <div style={styles.content}>
        <FileSidebar />
        <MainContent />
        <ReasoningPanel />
      </div>
      <BottomControlBar />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  room: {
    height: "100vh",
    background: "#0a0a0a",
  },
  shell: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    background: "#0a0a0a",
    color: "#fafafa",
  },
  content: {
    flex: 1,
    display: "flex",
    overflow: "hidden",
    position: "relative",
  },
};
