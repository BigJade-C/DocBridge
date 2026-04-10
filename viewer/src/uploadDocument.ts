import { irToEditorModel } from "./irToEditorModel";
import type { EditorDocument } from "./types";

export type LoadedUpload = {
  kind: "editor-model" | "ir";
  document: EditorDocument;
  originalIr: object | null;
};

export async function loadUploadedJsonFile(file: File): Promise<LoadedUpload> {
  const text = await readFileText(file);
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch (error) {
    throw new Error("Invalid JSON file");
  }

  if (isEditorDocument(payload)) {
    return {
      kind: "editor-model",
      document: payload,
      originalIr: null,
    };
  }

  if (isIrDocument(payload)) {
    return {
      kind: "ir",
      document: irToEditorModel(payload),
      originalIr: payload,
    };
  }

  throw new Error("Unsupported JSON shape. Expected Editor Model or IR JSON.");
}

function isEditorDocument(value: unknown): value is EditorDocument {
  if (!isRecord(value)) {
    return false;
  }
  return value.type === "doc" && Array.isArray(value.children);
}

function isIrDocument(value: unknown): value is { blocks: object[] } {
  if (!isRecord(value)) {
    return false;
  }
  return Array.isArray(value.blocks);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function readFileText(file: File): Promise<string> {
  const textMethod = (file as File & { text?: () => Promise<string> }).text;
  if (typeof textMethod === "function") {
    return textMethod.call(file);
  }

  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read JSON file"));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsText(file);
  });
}
