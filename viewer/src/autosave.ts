import type { EditorDocument } from "./types";

export const AUTOSAVE_STORAGE_PREFIX = "docbridge.autosave.v1";
export const AUTOSAVE_DEBOUNCE_MS = 1500;

type AutosavePayload = {
  savedAt: string;
  document: EditorDocument;
};

export function buildAutosaveKey(sourceType: string, sourceLabel: string): string {
  return `${AUTOSAVE_STORAGE_PREFIX}:${encodeURIComponent(sourceType)}:${encodeURIComponent(sourceLabel)}`;
}

export function saveAutosaveDraft(key: string, document: EditorDocument, savedAt: Date = new Date()): string {
  const iso = savedAt.toISOString();
  const payload: AutosavePayload = {
    savedAt: iso,
    document,
  };
  window.localStorage.setItem(key, JSON.stringify(payload));
  return iso;
}

export function formatLastSavedLabel(savedAt: string | null, now: Date = new Date()): string {
  if (!savedAt) {
    return "Autosave not yet written";
  }

  const savedDate = new Date(savedAt);
  const diffMs = Math.max(0, now.getTime() - savedDate.getTime());
  const diffSeconds = Math.floor(diffMs / 1000);

  if (diffSeconds < 5) {
    return "Last saved just now";
  }
  return `Last saved ${diffSeconds}s ago`;
}
