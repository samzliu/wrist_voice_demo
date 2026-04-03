"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
} from "react";
import { useRoomContext } from "@livekit/components-react";
import { Room, RoomEvent, RemoteParticipant } from "livekit-client";
import type {
  AgentMessage,
  ClientMessage,
  FileEntry,
  SearchResultItem,
} from "@/lib/protocol";

// ── State ───────────────────────────────────────────────────

export type ReasoningEntry = {
  id: string;
  timestamp: number;
} & (
  | { kind: "reasoning"; text: string }
  | {
      kind: "tool_call";
      tool: string;
      args: Record<string, unknown>;
      source?: string;
      result?: string;
      durationMs?: number;
      done: boolean;
    }
);

export type ActiveFile = {
  name: string;
  content: string;
  fileType: "markdown" | "html" | "other";
};

type ActiveTab = "editor" | "slides" | "search" | "web";

export interface AppState {
  connected: boolean;
  agentPaused: boolean;
  agentState: "active" | "thinking" | "paused";
  monologue: boolean;
  workspacePath: string;
  fileList: FileEntry[];
  activeFile: ActiveFile | null;
  reasoningLog: ReasoningEntry[];
  searchResults: { query: string; results: SearchResultItem[] } | null;
  viewedUrl: { url: string; title?: string; content: string } | null;
  activeTab: ActiveTab;
  presentSlide: { file: string; slideIndex: number } | null;
}

const initialState: AppState = {
  connected: false,
  agentPaused: false,
  agentState: "active",
  monologue: false,
  workspacePath: "",
  fileList: [],
  activeFile: null,
  reasoningLog: [],
  searchResults: null,
  viewedUrl: null,
  activeTab: "editor",
  presentSlide: null,
};

// ── Actions ─────────────────────────────────────────────────

type Action =
  | { type: "SET_CONNECTED"; value: boolean }
  | { type: "SET_PAUSED"; value: boolean }
  | { type: "SET_MONOLOGUE"; value: boolean }
  | { type: "SET_ACTIVE_TAB"; tab: ActiveTab }
  | { type: "SET_WORKSPACE_PATH"; path: string }
  | { type: "AGENT_MSG"; msg: AgentMessage };

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_CONNECTED":
      return { ...state, connected: action.value };
    case "SET_PAUSED":
      return { ...state, agentPaused: action.value };
    case "SET_MONOLOGUE":
      return { ...state, monologue: action.value };
    case "SET_WORKSPACE_PATH":
      return { ...state, workspacePath: action.path };
    case "SET_ACTIVE_TAB":
      return { ...state, activeTab: action.tab };
    case "AGENT_MSG":
      return handleAgentMessage(state, action.msg);
    default:
      return state;
  }
}

function handleAgentMessage(state: AppState, msg: AgentMessage): AppState {
  switch (msg.type) {
    case "doc_update": {
      const activeFile = state.activeFile;
      if (activeFile && activeFile.name === msg.file) {
        return { ...state, activeFile: { ...activeFile, content: msg.content } };
      }
      return {
        ...state,
        activeFile: { name: msg.file, content: msg.content, fileType: "markdown" },
      };
    }

    case "file_list":
      return {
        ...state,
        fileList: msg.files,
      };

    case "file_content": {
      const ft =
        msg.file_type === "html"
          ? "html"
          : msg.file_type === "markdown"
            ? "markdown"
            : "other";
      const tab = ft === "html" ? "slides" : "editor";
      return {
        ...state,
        activeFile: { name: msg.file, content: msg.content, fileType: ft as ActiveFile["fileType"] },
        activeTab: tab,
      };
    }

    case "tool_call": {
      const entry: ReasoningEntry = {
        id: msg.id,
        timestamp: Date.now(),
        kind: "tool_call",
        tool: msg.tool,
        args: msg.args,
        source: msg.source,
        done: false,
      };
      return { ...state, reasoningLog: [...state.reasoningLog, entry] };
    }

    case "tool_result": {
      const log = state.reasoningLog.map((e) => {
        if (e.id === msg.id && e.kind === "tool_call") {
          return { ...e, result: msg.result, durationMs: msg.duration_ms, done: true };
        }
        return e;
      });
      return { ...state, reasoningLog: log };
    }

    case "reasoning": {
      const entry: ReasoningEntry = {
        id: `r-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        timestamp: Date.now(),
        kind: "reasoning",
        text: msg.text,
      };
      return { ...state, reasoningLog: [...state.reasoningLog, entry] };
    }

    case "search_results":
      return {
        ...state,
        searchResults: { query: msg.query, results: msg.results },
        activeTab: "search",
      };

    case "url_content":
      return {
        ...state,
        viewedUrl: { url: msg.url, title: msg.title, content: msg.content },
        activeTab: "web",
      };

    case "present_slide":
      return {
        ...state,
        presentSlide: { file: msg.file, slideIndex: msg.slide_index },
        activeTab: "slides",
      };

    case "agent_state":
      return { ...state, agentState: msg.state };

    case "deep_think_result": {
      const entry: ReasoningEntry = {
        id: `dt-${Date.now()}`,
        timestamp: Date.now(),
        kind: "reasoning",
        text: `[Deep think complete] ${msg.task}\n${msg.result}`,
      };
      return { ...state, reasoningLog: [...state.reasoningLog, entry] };
    }

    default:
      return state;
  }
}

// ── Context ─────────────────────────────────────────────────

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  sendMessage: (msg: ClientMessage) => void;
}

const AppCtx = createContext<AppContextValue | null>(null);

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}

// ── Provider ────────────────────────────────────────────────

const decoder = new TextDecoder();
const encoder = new TextEncoder();

export function AppProvider({ children }: { children: React.ReactNode }) {
  const room = useRoomContext();
  const [state, dispatch] = useReducer(reducer, initialState);
  const suppressEcho = useRef(false);

  // Listen for agent messages
  useEffect(() => {
    const handler = (
      payload: Uint8Array,
      _participant: RemoteParticipant | undefined,
    ) => {
      if (suppressEcho.current) return;
      try {
        const msg = JSON.parse(decoder.decode(payload)) as AgentMessage;
        dispatch({ type: "AGENT_MSG", msg });
      } catch {
        // ignore malformed messages
      }
    };
    room.on(RoomEvent.DataReceived, handler);
    return () => {
      room.off(RoomEvent.DataReceived, handler);
    };
  }, [room]);

  // Send messages to agent
  const sendMessage = useCallback(
    (msg: ClientMessage) => {
      const isEdit = msg.type === "human_edit";
      if (isEdit) suppressEcho.current = true;
      room.localParticipant
        .publishData(encoder.encode(JSON.stringify(msg)), { reliable: true })
        .finally(() => {
          if (isEdit) suppressEcho.current = false;
        });
    },
    [room],
  );

  return (
    <AppCtx.Provider value={{ state, dispatch, sendMessage }}>
      {children}
    </AppCtx.Provider>
  );
}
