/** Journey for feedback API: with_flow | without_flow */
export const FLOW_KEY = "journeyFlow";

export function setJourneyFlow(flow: "with_flow" | "without_flow") {
  localStorage.setItem(FLOW_KEY, flow);
}

export function getJourneyFlow(): "with_flow" | "without_flow" {
  const v = localStorage.getItem(FLOW_KEY);
  return v === "with_flow" ? "with_flow" : "without_flow";
}

/** Selected content card ids from ContentSelection; map to API literal */
export const CONTENT_SELECTION_KEY = "contentSelectionIds";

export function setContentSelectionIds(ids: string[]) {
  localStorage.setItem(CONTENT_SELECTION_KEY, JSON.stringify(ids));
}

export function getContentTypeForFeedback(): "quotes" | "exercises" | "videos" | undefined {
  try {
    const raw = localStorage.getItem(CONTENT_SELECTION_KEY);
    if (!raw) return undefined;
    const ids: string[] = JSON.parse(raw);
    if (ids.includes("quotes")) return "quotes";
    if (ids.includes("exercise")) return "exercises";
    if (ids.includes("videos")) return "videos";
    return undefined;
  } catch {
    return undefined;
  }
}
