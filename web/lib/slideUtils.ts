/**
 * Slide parsing and rendering utilities.
 * Mirrors the HTML slide format from stash_web:
 *   - Deck = single HTML file with <div class="deck"> container
 *   - Slide = <section class="slide"> element, 960x540px
 */

const SLIDE_RE = /<section\s+class="slide"[^>]*>[\s\S]*?<\/section>/gi;

/**
 * Extract all <section class="slide"> blocks from a deck HTML string.
 */
export function parseSlides(deckHtml: string): string[] {
  return deckHtml.match(SLIDE_RE) || [];
}

/**
 * Wrap a single slide section in a minimal HTML document for iframe srcDoc rendering.
 */
export function buildSlideDoc(slideHtml: string): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      width: 960px;
      height: 540px;
      overflow: hidden;
      background: #0f172a;
    }
    .slide {
      width: 960px;
      height: 540px;
      overflow: hidden;
      position: relative;
    }
  </style>
</head>
<body>
  ${slideHtml}
</body>
</html>`;
}
