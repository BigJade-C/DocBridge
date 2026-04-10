import type { TableNode } from "../types";
import { ParagraphView } from "./ParagraphView";

type TableViewProps = {
  node: TableNode;
  editableParagraphId?: string | null;
  onSelectParagraph?: (paragraphId: string) => void;
  onParagraphTextChange?: (paragraphId: string, text: string) => void;
};

export function TableView({
  node,
  editableParagraphId,
  onSelectParagraph,
  onParagraphTextChange,
}: TableViewProps) {
  const isEditable = Boolean(onSelectParagraph && onParagraphTextChange);

  return (
    <div className="em-table-wrap" data-node-id={node.id}>
      <table className="em-table">
        <tbody>
          {node.rows.map((row) => (
            <tr key={row.id}>
              {row.cells.map((cell) => (
                <td
                  key={cell.id}
                  colSpan={cell.colspan ?? 1}
                  rowSpan={cell.rowspan ?? 1}
                  data-node-id={cell.id}
                >
                  {cell.children.map((paragraph) => (
                    <ParagraphView
                      key={paragraph.id}
                      node={paragraph}
                      editable={isEditable}
                      selected={editableParagraphId === paragraph.id}
                      onSelect={onSelectParagraph}
                      onTextChange={onParagraphTextChange}
                    />
                  ))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
