"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { useEffect, useRef } from "react";

interface Props {
  content: string;
  onChange: (content: string) => void;
}

export function MarkdownEditor({ content, onChange }: Props) {
  const isExternalUpdate = useRef(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: "Waiting for the agent to start editing, or start typing...",
      }),
    ],
    content: "",
    editorProps: {
      attributes: {
        style: "outline: none; min-height: 100%; padding: 20px 32px; font-size: 15px; line-height: 1.7;",
      },
    },
    onUpdate: ({ editor }) => {
      if (!isExternalUpdate.current) {
        // Convert to markdown-like text. TipTap stores as HTML internally,
        // but we pass the text content for simplicity. For a real app,
        // you'd use a markdown serializer.
        onChange(editor.storage.markdown?.getMarkdown?.() ?? editor.getText());
      }
    },
  });

  // Sync external content changes (from agent) into the editor
  useEffect(() => {
    if (!editor || !content) return;
    const currentText = editor.getText();
    // Only update if the content actually changed (avoid cursor jumps)
    if (content !== currentText) {
      isExternalUpdate.current = true;
      // Preserve cursor position as best we can
      const { from, to } = editor.state.selection;
      editor.commands.setContent(markdownToHtml(content), false);
      try {
        const maxPos = editor.state.doc.content.size;
        editor.commands.setTextSelection({
          from: Math.min(from, maxPos),
          to: Math.min(to, maxPos),
        });
      } catch {}
      isExternalUpdate.current = false;
    }
  }, [content, editor]);

  return (
    <div style={styles.wrapper}>
      <EditorContent editor={editor} style={styles.editor} />
    </div>
  );
}

/** Minimal markdown → HTML for display. Handles headings, bold, italic, lists, code blocks. */
function markdownToHtml(md: string): string {
  let html = md
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
    // Headings
    .replace(/^######\s+(.+)$/gm, "<h6>$1</h6>")
    .replace(/^#####\s+(.+)$/gm, "<h5>$1</h5>")
    .replace(/^####\s+(.+)$/gm, "<h4>$1</h4>")
    .replace(/^###\s+(.+)$/gm, "<h3>$1</h3>")
    .replace(/^##\s+(.+)$/gm, "<h2>$1</h2>")
    .replace(/^#\s+(.+)$/gm, "<h1>$1</h1>")
    // Bold & italic
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Unordered lists
    .replace(/^[-*]\s+(.+)$/gm, "<li>$1</li>")
    // Ordered lists
    .replace(/^\d+\.\s+(.+)$/gm, "<li>$1</li>")
    // Horizontal rules
    .replace(/^---$/gm, "<hr>")
    // Line breaks → paragraphs
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>");

  // Wrap loose <li> in <ul>
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>");
  // Clean up double-wrapped uls
  html = html.replace(/<\/ul>\s*<ul>/g, "");

  return `<p>${html}</p>`;
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    flex: 1,
    overflow: "auto",
    background: "#0a0a0a",
  },
  editor: {
    height: "100%",
    color: "#e0e0e0",
  },
};
