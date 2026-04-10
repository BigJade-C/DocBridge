import { useEffect, useMemo, useRef, type CSSProperties } from "react";

import type { ParagraphNode } from "../types";
import { TextNodeView } from "./TextNodeView";

type ParagraphViewProps = {
  node: ParagraphNode;
  editable?: boolean;
  selected?: boolean;
  onSelect?: (paragraphId: string) => void;
  onTextChange?: (paragraphId: string, text: string) => void;
};

const ALIGNMENT_MAP: Record<string, CSSProperties["textAlign"]> = {
  left: "left",
  center: "center",
  right: "right",
  justify: "justify",
};

export function ParagraphView({
  node,
  editable = false,
  selected = false,
  onSelect,
  onTextChange,
}: ParagraphViewProps) {
  const editorRef = useRef<HTMLDivElement | null>(null);
  const paragraphText = useMemo(() => node.children.map((child) => child.text).join(""), [node.children]);
  const style: CSSProperties = {
    textAlign: ALIGNMENT_MAP[node.attrs?.alignment ?? "left"] ?? "left",
  };
  const firstChildMarks = node.children[0]?.marks ?? [];
  const isBold = firstChildMarks.some((mark) => mark.type === "bold");
  const fontSizeMark = firstChildMarks.find((mark) => mark.type === "fontSize");
  const fontSize = fontSizeMark ? fontSizeMark.value : undefined;
  const isTitleLike = (node.attrs?.alignment ?? "left") === "center" && isBold && (fontSize ?? 0) >= 14;
  const paragraphClassName = `em-paragraph${isTitleLike ? " em-paragraph-title" : ""}`;

  useEffect(() => {
    if (!editable || !editorRef.current) {
      return;
    }
    if (editorRef.current.textContent !== paragraphText) {
      editorRef.current.textContent = paragraphText;
    }
  }, [editable, paragraphText]);

  if (editable) {
    const editorStyle: CSSProperties = {
      ...style,
      fontWeight: isBold ? 700 : 400,
      fontSize: fontSize ? `${fontSize}px` : undefined,
    };

    return (
      <div
        ref={editorRef}
        className={`${paragraphClassName} em-paragraph-editor${selected ? " is-selected" : ""}`}
        style={editorStyle}
        data-node-id={node.id}
        data-testid={`paragraph-${node.id}`}
        role="textbox"
        contentEditable
        suppressContentEditableWarning
        onFocus={() => onSelect?.(node.id)}
        onClick={() => onSelect?.(node.id)}
        onInput={(event) => onTextChange?.(node.id, event.currentTarget.textContent ?? "")}
      />
    );
  }

  return (
    <p className={paragraphClassName} style={style} data-node-id={node.id}>
      {node.children.length > 0 ? (
        node.children.map((child) => <TextNodeView key={child.id} node={child} />)
      ) : (
        <span className="em-paragraph-empty" aria-hidden="true">
          {"\u00A0"}
        </span>
      )}
    </p>
  );
}
