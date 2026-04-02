"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useApp } from "./AppContext";
import { parseSlides, getSlideTitle } from "@/lib/slides";

export function SlideViewer() {
  const { state } = useApp();
  const file = state.activeFile;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [presenting, setPresenting] = useState(false);

  const slides = useMemo(
    () => (file?.fileType === "html" ? parseSlides(file.content) : []),
    [file],
  );

  // Jump to slide when agent sends present_slide
  useEffect(() => {
    if (state.presentSlide && file && state.presentSlide.file === file.name) {
      setCurrentIndex(state.presentSlide.slideIndex);
    }
  }, [state.presentSlide, file]);

  // Keyboard navigation
  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "Enter") {
        setCurrentIndex((i) => Math.min(i + 1, slides.length - 1));
      } else if (e.key === "ArrowLeft") {
        setCurrentIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Escape") {
        setPresenting(false);
      }
    },
    [slides.length],
  );

  useEffect(() => {
    if (presenting) {
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }
  }, [presenting, onKey]);

  if (!file || slides.length === 0) {
    return <div style={styles.empty}>No slides to display</div>;
  }

  if (presenting) {
    return (
      <div style={styles.presentOverlay} onClick={() => setPresenting(false)}>
        <div
          style={styles.presentSlide}
          dangerouslySetInnerHTML={{ __html: slides[currentIndex] }}
          onClick={(e) => e.stopPropagation()}
        />
        <div style={styles.presentCounter}>
          {currentIndex + 1} / {slides.length}
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Slide thumbnails sidebar */}
      <div style={styles.thumbList}>
        {slides.map((s, i) => (
          <div
            key={i}
            style={{
              ...styles.thumb,
              ...(i === currentIndex ? styles.thumbActive : {}),
            }}
            onClick={() => setCurrentIndex(i)}
          >
            <span style={styles.thumbNum}>{i + 1}</span>
            <span style={styles.thumbTitle}>{getSlideTitle(s)}</span>
          </div>
        ))}
      </div>

      {/* Main slide view */}
      <div style={styles.main}>
        <div style={styles.slideWrapper}>
          <div
            style={styles.slideContainer}
            dangerouslySetInnerHTML={{ __html: slides[currentIndex] }}
          />
        </div>
        <div style={styles.controls}>
          <button
            onClick={() => setCurrentIndex((i) => Math.max(i - 1, 0))}
            disabled={currentIndex === 0}
            style={styles.navBtn}
          >
            ← Prev
          </button>
          <span style={styles.counter}>
            {currentIndex + 1} / {slides.length}
          </span>
          <button
            onClick={() =>
              setCurrentIndex((i) => Math.min(i + 1, slides.length - 1))
            }
            disabled={currentIndex === slides.length - 1}
            style={styles.navBtn}
          >
            Next →
          </button>
          <button onClick={() => setPresenting(true)} style={styles.presentBtn}>
            Present
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    height: "100%",
    overflow: "hidden",
  },
  thumbList: {
    width: 160,
    minWidth: 160,
    overflow: "auto",
    borderRight: "1px solid #222",
    padding: 8,
  },
  thumb: {
    padding: "8px 10px",
    marginBottom: 4,
    borderRadius: 4,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 12,
    color: "#888",
  },
  thumbActive: {
    background: "#1a1a1a",
    color: "#fafafa",
  },
  thumbNum: {
    fontSize: 11,
    color: "#555",
    minWidth: 18,
  },
  thumbTitle: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  slideWrapper: {
    width: "100%",
    maxWidth: 960,
    aspectRatio: "16 / 9",
    background: "#fff",
    borderRadius: 8,
    overflow: "hidden",
    boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
  },
  slideContainer: {
    width: 960,
    height: 540,
    transformOrigin: "top left",
    transform: "scale(var(--slide-scale, 1))",
    overflow: "hidden",
  },
  controls: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    marginTop: 16,
  },
  navBtn: {
    padding: "6px 14px",
    background: "#222",
    border: "none",
    borderRadius: 4,
    color: "#ccc",
    cursor: "pointer",
    fontSize: 13,
  },
  counter: {
    fontSize: 13,
    color: "#888",
  },
  presentBtn: {
    padding: "6px 14px",
    background: "#2563eb",
    border: "none",
    borderRadius: 4,
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
    marginLeft: 16,
  },
  presentOverlay: {
    position: "fixed",
    inset: 0,
    background: "#000",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  presentSlide: {
    width: 960,
    height: 540,
    background: "#fff",
    overflow: "hidden",
    transform: "scale(1.5)",
  },
  presentCounter: {
    position: "absolute",
    bottom: 20,
    color: "#555",
    fontSize: 14,
  },
  empty: {
    color: "#444",
    fontSize: 14,
    textAlign: "center",
    padding: 40,
  },
};
