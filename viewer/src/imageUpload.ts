export async function readImageFileAsDataUrl(file: File): Promise<string> {
  const bytes = await readFileBytes(file);
  const mimeType = file.type || inferMimeType(file.name) || "application/octet-stream";
  return `data:${mimeType};base64,${bytesToBase64(bytes)}`;
}

function inferMimeType(fileName: string): string | null {
  const lowerName = fileName.toLowerCase();
  if (lowerName.endsWith(".png")) {
    return "image/png";
  }
  if (lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  if (lowerName.endsWith(".gif")) {
    return "image/gif";
  }
  if (lowerName.endsWith(".bmp")) {
    return "image/bmp";
  }
  return null;
}

async function readFileBytes(file: File): Promise<Uint8Array> {
  const arrayBufferMethod = (file as File & { arrayBuffer?: () => Promise<ArrayBuffer> }).arrayBuffer;
  if (typeof arrayBufferMethod === "function") {
    return new Uint8Array(await arrayBufferMethod.call(file));
  }

  return new Promise<Uint8Array>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read image file"));
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
