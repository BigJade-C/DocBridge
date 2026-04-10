import { useMemo, useState } from "react";

import {
  deleteParagraph,
  getParagraphById,
  getTopLevelParagraphs,
  insertParagraphAfter,
  setParagraphAlignment,
  setParagraphFontSize,
  toggleParagraphBold,
  updateParagraphText,
  type ParagraphAlignment,
} from "../editor/model";
import type { EditorDocument } from "../types";
import { DocView } from "./DocView";
import { EditorToolbar } from "./EditorToolbar";

type EditorSurfaceProps = {
  initialDocument: EditorDocument;
  originalIr?: object | null;
};

export function EditorSurface({ initialDocument, originalIr = null }: EditorSurfaceProps) {
  const [document, setDocument] = useState<EditorDocument>(initialDocument);
  const [selectedParagraphId, setSelectedParagraphId] = useState<string | null>(
    getTopLevelParagraphs(initialDocument)[0]?.id ?? null,
  );
  const [isExporting, setIsExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [debugVisible, setDebugVisible] = useState(false);

  const selectedParagraph = useMemo(
    () => (selectedParagraphId ? getParagraphById(document, selectedParagraphId) : null),
    [document, selectedParagraphId],
  );

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
        onInsertParagraph={handleInsertParagraph}
        onDeleteParagraph={handleDeleteParagraph}
        onExportDocx={handleExportDocx}
        onToggleDebug={() => setDebugVisible((current) => !current)}
        exportDisabled={isExporting}
        exportLabel={isExporting ? "Exporting..." : "Export DOCX"}
        debugVisible={debugVisible}
      />
      {exportMessage ? <div className="editor-export-message">{exportMessage}</div> : null}
      <DocView
        document={document}
        editableParagraphId={selectedParagraphId}
        onSelectParagraph={handleParagraphSelect}
        onParagraphTextChange={handleParagraphTextChange}
      />
      {debugVisible ? <pre className="editor-json-preview">{JSON.stringify(document, null, 2)}</pre> : null}
    </section>
  );
}
