import { useMemo } from "react";

import type { ParagraphNode } from "../types";
import { getParagraphFontSize, isParagraphBold, type ParagraphAlignment } from "../editor/model";

type EditorToolbarProps = {
  paragraph: ParagraphNode | null;
  onToggleBold: () => void;
  onFontSizeChange: (value: number) => void;
  onAlignmentChange: (alignment: ParagraphAlignment) => void;
  onInsertParagraph: () => void;
  onDeleteParagraph: () => void;
  onExportDocx: () => void;
  onToggleDebug: () => void;
  exportDisabled?: boolean;
  exportLabel?: string;
  debugVisible?: boolean;
};

export function EditorToolbar({
  paragraph,
  onToggleBold,
  onFontSizeChange,
  onAlignmentChange,
  onInsertParagraph,
  onDeleteParagraph,
  onExportDocx,
  onToggleDebug,
  exportDisabled = false,
  exportLabel = "Export DOCX",
  debugVisible = false,
}: EditorToolbarProps) {
  const isDisabled = paragraph === null;
  const currentBold = paragraph ? isParagraphBold(paragraph) : false;
  const currentFontSize = useMemo(() => (paragraph ? getParagraphFontSize(paragraph) ?? 10 : 10), [paragraph]);
  const currentAlignment = paragraph?.attrs?.alignment ?? "left";

  return (
    <div className="editor-toolbar" role="toolbar" aria-label="Paragraph formatting toolbar">
      <button type="button" onClick={onToggleBold} disabled={isDisabled} aria-pressed={currentBold}>
        Bold
      </button>

      <label className="editor-toolbar-field">
        <span>Font size</span>
        <input
          type="number"
          min={8}
          max={72}
          step={1}
          value={currentFontSize}
          disabled={isDisabled}
          onChange={(event) => onFontSizeChange(Number(event.target.value))}
        />
      </label>

      <div className="editor-toolbar-group" aria-label="Paragraph alignment">
        {(["left", "center", "right"] as ParagraphAlignment[]).map((alignment) => (
          <button
            key={alignment}
            type="button"
            onClick={() => onAlignmentChange(alignment)}
            disabled={isDisabled}
            aria-pressed={currentAlignment === alignment}
          >
            {alignment}
          </button>
        ))}
      </div>

      <button type="button" onClick={onInsertParagraph} disabled={isDisabled}>
        Insert paragraph
      </button>
      <button type="button" onClick={onDeleteParagraph} disabled={isDisabled}>
        Delete paragraph
      </button>
      <button type="button" onClick={onExportDocx} disabled={exportDisabled}>
        {exportLabel}
      </button>
      <button type="button" onClick={onToggleDebug} aria-pressed={debugVisible}>
        {debugVisible ? "Hide Debug" : "Show Debug"}
      </button>
    </div>
  );
}
