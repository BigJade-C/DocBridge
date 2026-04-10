import type { TableNode } from "../types";
import { ParagraphView } from "./ParagraphView";

type TableViewProps = {
  node: TableNode;
};

export function TableView({ node }: TableViewProps) {
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
                    <ParagraphView key={paragraph.id} node={paragraph} />
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
