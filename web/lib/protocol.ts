/** Data channel message types between web client and voice agent. */

// ── Agent → Client ──────────────────────────────────────────

export type FileEntry = { name: string; type: "markdown" | "html" | "other" };

export type SearchResultItem = {
  title: string;
  url: string;
  snippet: string;
  score?: number;
};

export type DocUpdateMsg = { type: "doc_update"; file: string; content: string };
export type FileListMsg = { type: "file_list"; files: FileEntry[] };
export type FileContentMsg = {
  type: "file_content";
  file: string;
  content: string;
  file_type: string;
};
export type ToolCallMsg = {
  type: "tool_call";
  tool: string;
  args: Record<string, unknown>;
  id: string;
  source?: "agent" | "deep";
};
export type ToolResultMsg = {
  type: "tool_result";
  id: string;
  result: string;
  duration_ms?: number;
};
export type ReasoningMsg = { type: "reasoning"; text: string };
export type SearchResultsMsg = {
  type: "search_results";
  query: string;
  results: SearchResultItem[];
};
export type UrlContentMsg = {
  type: "url_content";
  url: string;
  title?: string;
  content: string;
};
export type PresentSlideMsg = {
  type: "present_slide";
  file: string;
  slide_index: number;
};
export type AgentStateMsg = {
  type: "agent_state";
  state: "thinking" | "paused" | "active";
};
export type DeepThinkResultMsg = {
  type: "deep_think_result";
  task: string;
  result: string;
};

export type AgentMessage =
  | DocUpdateMsg
  | FileListMsg
  | FileContentMsg
  | ToolCallMsg
  | ToolResultMsg
  | ReasoningMsg
  | SearchResultsMsg
  | UrlContentMsg
  | PresentSlideMsg
  | AgentStateMsg
  | DeepThinkResultMsg;

// ── Client → Agent ──────────────────────────────────────────

export type ConfigMsg = {
  type: "config";
  script_content: string;
  workspace_path: string;
};
export type HumanEditMsg = { type: "human_edit"; content: string; file: string };
export type PauseMsg = { type: "pause" };
export type ResumeMsg = { type: "resume" };
export type MonologueOnMsg = { type: "monologue_on" };
export type MonologueOffMsg = { type: "monologue_off" };
export type RequestFileListMsg = { type: "request_file_list" };
export type RequestFileContentMsg = { type: "request_file_content"; file: string };
export type FileCreateMsg = { type: "file_create"; name: string; file_type: string };
export type FileRenameMsg = {
  type: "file_rename";
  old_name: string;
  new_name: string;
};
export type FileDeleteMsg = { type: "file_delete"; name: string };
export type CancelDeepThinkMsg = { type: "cancel_deep_think" };

export type ClientMessage =
  | ConfigMsg
  | HumanEditMsg
  | PauseMsg
  | ResumeMsg
  | MonologueOnMsg
  | MonologueOffMsg
  | RequestFileListMsg
  | RequestFileContentMsg
  | FileCreateMsg
  | FileRenameMsg
  | FileDeleteMsg
  | CancelDeepThinkMsg;
