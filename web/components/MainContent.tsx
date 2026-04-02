"use client";

import { useMemo } from "react";
import { useApp } from "./AppContext";
import { TabBar, Tab } from "./TabBar";
import { MarkdownEditor } from "./MarkdownEditor";
import { SlideViewer } from "./SlideViewer";
import { SearchResults } from "./SearchResults";
import { WebViewer } from "./WebViewer";

export function MainContent() {
  const { state, dispatch, sendMessage } = useApp();

  const tabs = useMemo(() => {
    const t: Tab[] = [{ id: "editor", label: "Editor" }];
    // Show slides tab if an HTML file is active or has been viewed
    if (state.activeFile?.fileType === "html") {
      t.push({ id: "slides", label: "Slides" });
    }
    if (state.searchResults) {
      t.push({ id: "search", label: "Search", closable: true });
    }
    if (state.viewedUrl) {
      t.push({ id: "web", label: "Web", closable: true });
    }
    return t;
  }, [state.activeFile?.fileType, state.searchResults, state.viewedUrl]);

  const onEditorChange = (content: string) => {
    if (!state.activeFile) return;
    sendMessage({
      type: "human_edit",
      content,
      file: state.activeFile.name,
    });
  };

  const onTabClose = (id: string) => {
    // Clear the associated data and switch back to editor
    dispatch({ type: "SET_ACTIVE_TAB", tab: "editor" });
  };

  return (
    <div style={styles.container}>
      <TabBar
        tabs={tabs}
        activeTab={state.activeTab}
        onSelect={(id) => dispatch({ type: "SET_ACTIVE_TAB", tab: id as never })}
        onClose={onTabClose}
      />
      <div style={styles.content}>
        {state.activeTab === "editor" && (
          <>
            {state.activeFile && state.activeFile.fileType !== "html" ? (
              <MarkdownEditor
                content={state.activeFile.content}
                onChange={onEditorChange}
              />
            ) : (
              <div style={styles.placeholder}>
                {state.activeFile
                  ? "This file type uses the Slides tab"
                  : "Select a file or wait for the agent..."}
              </div>
            )}
          </>
        )}
        {state.activeTab === "slides" && <SlideViewer />}
        {state.activeTab === "search" && <SearchResults />}
        {state.activeTab === "web" && <WebViewer />}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  content: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  placeholder: {
    color: "#444",
    fontSize: 14,
    textAlign: "center",
    padding: 60,
  },
};
