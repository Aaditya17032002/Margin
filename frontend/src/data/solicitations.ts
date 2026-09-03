import type { Citation, DocumentPage } from "@/types";

/**
 * Every citation in Margin resolves to a real line of a real page. The seed
 * corpus therefore stores the document body first, and citations are derived
 * from it by page and line index — so a quote can never drift out of sync with
 * the source it claims to come from.
 */
export function citationFactory(pages: DocumentPage[]) {
  return function cite(
    id: string,
    page: number,
    section: string,
    lineIndex: number,
    span = 1,
  ): Citation {
    const doc = pages.find((p) => p.page === page);
    if (!doc) throw new Error(`Seed error: page ${page} missing for citation ${id}`);
    const lines = doc.lines.slice(lineIndex, lineIndex + span);
    if (lines.length === 0) throw new Error(`Seed error: no line at ${page}:${lineIndex}`);
    const total = doc.lines.length + 4;
    return {
      id,
      page,
      section,
      quote: lines.join(" "),
      bbox: {
        x: 0.11,
        y: (lineIndex + 2) / total,
        w: 0.78,
        h: Math.max(span, 1) / total,
      },
    };
  };
}

export function findLineIndex(pages: DocumentPage[], page: number, quote: string) {
  const doc = pages.find((p) => p.page === page);
  if (!doc) return -1;
  return doc.lines.findIndex((line) => quote.includes(line) || line === quote);
}
