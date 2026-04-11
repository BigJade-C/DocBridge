import { useEffect, useMemo, useState } from "react";

import {
  deleteParagraph,
  getImageById,
  getParagraphById,
  getTopLevelParagraphs,
  insertParagraphAfter,
  setParagraphListKind,
  replaceImageSource,
  setParagraphAlignment,
  setParagraphFontSize,
  setImageAltText,
  toggleParagraphBold,
  updateParagraphText,
  type ParagraphAlignment,
} from "../editor/model";
import { readImageFileAsDataUrl } from "../imageUpload";
import type { EditorDocument } from "../types";
import { DocView } from "./DocView";
import { EditorToolbar } from "./EditorToolbar";

type EditorSurfaceProps = {
  initialDocument: EditorDocument;
  originalIr?: object | null;
  onDirtyChange?: (isDirty: boolean) => void;
};

export function EditorSurface({
  initialDocument,
  originalIr = null,
  onDirtyChange,
}: EditorSurfaceProps) {
  const [document, setDocument] = useState<EditorDocument>(initialDocument);
  const [cleanSnapshot, setCleanSnapshot] = useState(() => serializeDocument(initialDocument));
  const [selectedParagraphId, setSelectedParagraphId] = useState<string | null>(
    getTopLevelParagraphs(initialDocument)[0]?.id ?? null,
  );
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [debugVisible, setDebugVisible] = useState(false);

  const selectedParagraph = useMemo(
    () => (selectedParagraphId ? getParagraphById(document, selectedParagraphId) : null),
    [document, selectedParagraphId],
  );
  const selectedImage = useMemo(
    () => (selectedImageId ? getImageById(document, selectedImageId) : null),
    [document, selectedImageId],
  );
  const isDirty = serializeDocument(document) !== cleanSnapshot;

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  function handleToggleBold() {
    if (!selectedParagraphId) {
      return;
    }
    setDocument((current) => toggleParagraphBold(current, selectedParagraphId));
  }

  function handleFontSizeChange(value: number) {
    if (!selectedParagraphId || Number.isNaN(value)) {
      return;
    }
    setDocument((current) => setParagraphFontSize(current, selectedParagraphId, value));
  }

  function handleAlignmentChange(alignment: ParagraphAlignment) {
    if (!selectedParagraphId) {
      return;
    }
    setDocument((current) => setParagraphAlignment(current, selectedParagraphId, alignment));
  }

  function handleListKindChange(listKind: "none" | "numbered" | "bullet") {
    if (!selectedParagraphId) {
      return;
    }
    setDocument((current) => setParagraphListKind(current, selectedParagraphId, listKind));
  }

  function handleInsertParagraph() {
    if (!selectedParagraphId) {
      return;
    }
    setDocument((current) => {
      const result = insertParagraphAfter(current, selectedParagraphId);
      setSelectedParagraphId(result.insertedParagraphId);
      return result.document;
    });
  }

  function handleDeleteParagraph() {
    if (!selectedParagraphId) {
      return;
    }
    setDocument((current) => {
      const result = deleteParagraph(current, selectedParagraphId);
      setSelectedParagraphId(result.nextSelectedParagraphId);
      return result.document;
    });
  }

  function handleParagraphTextChange(paragraphId: string, text: string) {
    setDocument((current) => updateParagraphText(current, paragraphId, text));
  }

  function handleParagraphSelect(paragraphId: string) {
    setSelectedParagraphId(paragraphId);
    setSelectedImageId(null);
  }

  function handleImageSelect(imageId: string) {
    setSelectedImageId(imageId);
    setSelectedParagraphId(null);
  }

  async function handleReplaceImage(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !selectedImageId) {
      return;
    }

    try {
      const dataUrl = await readImageFileAsDataUrl(file);
      setDocument((current) => replaceImageSource(current, selectedImageId, dataUrl));
      setExportMessage("Image replaced");
    } catch (error) {
      setExportMessage(error instanceof Error ? error.message : "Image replacement failed");
    } finally {
      event.target.value = "";
    }
  }

  function handleImageAltTextChange(altText: string) {
    if (!selectedImageId) {
      return;
    }
    setDocument((current) => setImageAltText(current, selectedImageId, altText));
  }

  async function handleExportDocx() {
    setIsExporting(true);
    setExportMessage(null);

    try {
      const response = await fetch("/api/export-docx", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          editorModel: document,
          originalIr,
          fileName: "docbridge-export.docx",
        }),
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.status}`);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = "docbridge-export.docx";
      anchor.click();
      URL.revokeObjectURL(objectUrl);
      setCleanSnapshot(serializeDocument(document));
      setExportMessage("DOCX exported");
    } catch (error) {
      setExportMessage(error instanceof Error ? error.message : "Export failed");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <section className="editor-surface">
      <EditorToolbar
        paragraph={selectedParagraph}
        onToggleBold={handleToggleBold}
        onFontSizeChange={handleFontSizeChange}
        onAlignmentChange={handleAlignmentChange}
        onListKindChange={handleListKindChange}
        onInsertParagraph={handleInsertParagraph}
        onDeleteParagraph={handleDeleteParagraph}
        onExportDocx={handleExportDocx}
        onToggleDebug={() => setDebugVisible((current) => !current)}
        exportDisabled={isExporting}
        exportLabel={isExporting ? "Exporting..." : "Export DOCX"}
        debugVisible={debugVisible}
      />
      <div className={`editor-dirty-state${isDirty ? " is-dirty" : ""}`} aria-label="Editor dirty state">
        {isDirty ? "Unsaved changes" : "Clean"}
      </div>
      {exportMessage ? <div className="editor-export-message">{exportMessage}</div> : null}
      {selectedImage ? (
        <div className="editor-image-tools" aria-label="Image tools">
          <label className="editor-toolbar-field">
            <span>Replace image</span>
            <input
              aria-label="Replace image"
              type="file"
              accept="image/png,image/jpeg,image/gif,image/bmp"
              onChange={handleReplaceImage}
            />
          </label>
          <label className="editor-toolbar-field">
            <span>Alt text</span>
            <input
              aria-label="Image alt text"
              type="text"
              value={selectedImage.attrs?.alt ?? ""}
              onChange={(event) => handleImageAltTextChange(event.target.value)}
            />
          </label>
        </div>
      ) : null}
      <DocView
        document={document}
        editableParagraphId={selectedParagraphId}
        selectedImageId={selectedImageId}
        onSelectParagraph={handleParagraphSelect}
        onSelectImage={handleImageSelect}
        onParagraphTextChange={handleParagraphTextChange}
      />
      {debugVisible ? <pre className="editor-json-preview">{JSON.stringify(document, null, 2)}</pre> : null}
    </section>
  );
}

function serializeDocument(document: EditorDocument): string {
  return JSON.stringify(document);
}
