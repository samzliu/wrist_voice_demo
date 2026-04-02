/** Parse and manipulate HTML slide decks. */

const SLIDE_RE = /<section\s+class="slide"[^>]*>[\s\S]*?<\/section>/gi;

/** Extract individual slide HTML strings from a deck. */
export function parseSlides(html: string): string[] {
  return html.match(SLIDE_RE) || [];
}

/** Get the deck wrapper (everything outside the slides). */
export function getDeckShell(html: string): { before: string; after: string } {
  const slides = parseSlides(html);
  if (slides.length === 0) return { before: html, after: "" };

  const firstIdx = html.indexOf(slides[0]);
  const lastSlide = slides[slides.length - 1];
  const lastIdx = html.lastIndexOf(lastSlide) + lastSlide.length;

  return {
    before: html.slice(0, firstIdx),
    after: html.slice(lastIdx),
  };
}

/** Reassemble a deck from the shell and updated slides. */
export function reassembleDeck(
  before: string,
  slides: string[],
  after: string,
): string {
  return before + slides.join("\n") + after;
}

/** Extract the first heading text from a slide's HTML. */
export function getSlideTitle(slideHtml: string): string {
  const match = slideHtml.match(/<h[12][^>]*>(.*?)<\/h[12]>/i);
  if (match) return match[1].replace(/<[^>]+>/g, "").trim();
  return "Untitled";
}
