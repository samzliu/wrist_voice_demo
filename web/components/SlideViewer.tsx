"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { buildSlideDoc } from "@/lib/slideUtils";

interface Props {
  slides: string[];
  currentSlide: number;
  onSlideChange: (slide: number) => void;
}

export function SlideViewer({ slides, currentSlide, onSlideChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  // Calculate scale to fit the 960x540 slide in the container
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      // Leave room for bottom bar and some padding
      const availH = height - 60;
      const availW = width;
      const s = Math.min(availW / 960, availH / 540);
      setScale(Math.max(0.3, s));
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        if (currentSlide < slides.length - 1) {
          onSlideChange(currentSlide + 1);
        }
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        if (currentSlide > 0) {
          onSlideChange(currentSlide - 1);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentSlide, slides.length, onSlideChange]);

  const goNext = useCallback(() => {
    if (currentSlide < slides.length - 1) onSlideChange(currentSlide + 1);
  }, [currentSlide, slides.length, onSlideChange]);

  const goPrev = useCallback(() => {
    if (currentSlide > 0) onSlideChange(currentSlide - 1);
  }, [currentSlide, onSlideChange]);

  if (slides.length === 0) {
    return (
      <div style={styles.empty}>
        <p style={styles.emptyText}>Waiting for slides...</p>
      </div>
    );
  }

  const slideDoc = buildSlideDoc(slides[currentSlide] || "");

  return (
    <div ref={containerRef} style={styles.container}>
      {/* Thumbnail sidebar */}
      <div style={styles.thumbnailSidebar}>
        {slides.map((slide, i) => (
          <div
            key={i}
            onClick={() => onSlideChange(i)}
            style={{
              ...styles.thumbnail,
              border: i === currentSlide ? "2px solid #3b82f6" : "2px solid transparent",
            }}
          >
            <div style={styles.thumbnailNumber}>{i + 1}</div>
            <iframe
              srcDoc={buildSlideDoc(slide)}
              style={styles.thumbnailFrame}
              sandbox="allow-scripts"
              scrolling="no"
              tabIndex={-1}
            />
          </div>
        ))}
      </div>

      {/* Main slide area */}
      <div style={styles.mainArea}>
        <div style={styles.slideWrapper}>
          <div
            style={{
              transform: `scale(${scale})`,
              transformOrigin: "center center",
              width: 960,
              height: 540,
            }}
          >
            <iframe
              srcDoc={slideDoc}
              style={styles.slideFrame}
              sandbox="allow-scripts"
              scrolling="no"
            />
          </div>
        </div>

        {/* Bottom bar */}
        <div style={styles.bottomBar}>
          <button
            onClick={goPrev}
            disabled={currentSlide === 0}
            style={{
              ...styles.navButton,
              opacity: currentSlide === 0 ? 0.3 : 1,
            }}
          >
            &#8592;
          </button>
          <span style={styles.slideCounter}>
            {currentSlide + 1} / {slides.length}
          </span>
          <button
            onClick={goNext}
            disabled={currentSlide === slides.length - 1}
            style={{
              ...styles.navButton,
              opacity: currentSlide === slides.length - 1 ? 0.3 : 1,
            }}
          >
            &#8594;
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
    background: "#0a0a0a",
  },
  empty: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    background: "#0a0a0a",
  },
  emptyText: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: 16,
    color: "#555",
  },
  thumbnailSidebar: {
    width: 140,
    minWidth: 140,
    overflowY: "auto" as const,
    padding: "12px 8px",
    display: "flex",
    flexDirection: "column" as const,
    gap: 8,
    borderRight: "1px solid #222",
  },
  thumbnail: {
    position: "relative" as const,
    width: 120,
    height: 68,
    borderRadius: 4,
    overflow: "hidden",
    cursor: "pointer",
    flexShrink: 0,
    background: "#0f172a",
  },
  thumbnailNumber: {
    position: "absolute" as const,
    top: 2,
    left: 4,
    fontSize: 10,
    color: "#666",
    zIndex: 1,
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  thumbnailFrame: {
    width: 960,
    height: 540,
    border: "none",
    transform: "scale(0.125)",
    transformOrigin: "top left",
    pointerEvents: "none" as const,
  },
  mainArea: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  slideWrapper: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  slideFrame: {
    width: 960,
    height: 540,
    border: "none",
    borderRadius: 8,
    boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
  },
  bottomBar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 24,
    padding: "12px 0 16px 0",
  },
  navButton: {
    background: "transparent",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#ccc",
    padding: "6px 16px",
    fontSize: 18,
    cursor: "pointer",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  slideCounter: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: 14,
    color: "#888",
    minWidth: 60,
    textAlign: "center" as const,
  },
};
