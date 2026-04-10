import { irToEditorModel } from "./irToEditorModel";
import type { EditorDocument } from "./types";

export type ImportedDocument = {
  document: EditorDocument;
  originalIr: object;
};

export async function importDocumentFile(file: File): Promise<ImportedDocument> {
  const bytes = await readFileBytes(file);
  const fileContentBase64 = bytesToBase64(bytes);

  const response = await fetch("/api/import-document", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      fileName: file.name,
      fileContentBase64,
    }),
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(payload?.error ?? `Import failed: ${response.status}`);
  }

  const irPayload = (await response.json()) as object;
  return {
    document: irToEditorModel(irPayload as { blocks?: unknown[] }),
    originalIr: irPayload,
  };
}

async function readFileBytes(file: File): Promise<Uint8Array> {
  const arrayBufferMethod = (file as File & { arrayBuffer?: () => Promise<ArrayBuffer> }).arrayBuffer;
  if (typeof arrayBufferMethod === "function") {
    return new Uint8Array(await arrayBufferMethod.call(file));
  }

  return new Promise<Uint8Array>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read import file"));
    reader.onload = () => resolve(new Uint8Array(reader.result as ArrayBuffer));
    reader.readAsArrayBuffer(file);
  });
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}
