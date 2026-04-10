import type { BlockNode, EditorDocument, ImageNode, ParagraphNode, TableNode } from "../types";
import { ImageView } from "./ImageView";
import { ParagraphView } from "./ParagraphView";
import { TableView } from "./TableView";

type DocViewProps = {
  document: EditorDocument;
  editableParagraphId?: string | null;
  onSelectParagraph?: (paragraphId: string) => void;
  onParagraphTextChange?: (paragraphId: string, text: string) => void;
};

export function DocView({
  document,
  editableParagraphId,
  onSelectParagraph,
  onParagraphTextChange,
}: DocViewProps) {
  return (
    <div className="em-doc" data-node-id={document.id}>
      {document.children.map((child) => (
        <NodeView
          key={child.id}
          node={child}
          editableParagraphId={editableParagraphId}
          onSelectParagraph={onSelectParagraph}
          onParagraphTextChange={onParagraphTextChange}
        />
      ))}
    </div>
  );
}

function NodeView({
  node,
  editableParagraphId,
  onSelectParagraph,
  onParagraphTextChange,
}: {
  node: BlockNode;
  editableParagraphId?: string | null;
  onSelectParagraph?: (paragraphId: string) => void;
  onParagraphTextChange?: (paragraphId: string, text: string) => void;
}) {
  const isEditable = Boolean(onSelectParagraph && onParagraphTextChange);

  if (node.type === "paragraph") {
    return (
      <ParagraphView
        node={node as ParagraphNode}
        editable={isEditable}
        selected={editableParagraphId === node.id}
        onSelect={onSelectParagraph}
        onTextChange={onParagraphTextChange}
      />
    );
  }
  if (node.type === "table") {
    return (
      <TableView
        node={node as TableNode}
        editableParagraphId={editableParagraphId}
        onSelectParagraph={onSelectParagraph}
        onParagraphTextChange={onParagraphTextChange}
      />
    );
  }
  if (node.type === "image") {
    return <ImageView node={node as ImageNode} />;
  }
  return null;
}
