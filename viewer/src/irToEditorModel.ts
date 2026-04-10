import type { EditorDocument, ImageNode, ParagraphNode, TableCellNode, TableNode, TextNode } from "./types";

type IrCharacterStyle = {
  bold?: boolean | null;
  font_size_pt?: number | null;
};

type IrTextRun = {
  kind?: string;
  text?: string | null;
  resolved_text?: string | null;
  character_style?: IrCharacterStyle | null;
};

type IrParagraphBlock = {
  block_type: "paragraph";
  paragraph_style?: {
    alignment?: string | null;
  } | null;
  list_info?: {
    kind?: string | null;
    level?: number | null;
  } | null;
  text_runs?: IrTextRun[];
};

type IrTableCell = {
  text?: string | null;
  colspan?: number | null;
  rowspan?: number | null;
};

type IrTableBlock = {
  block_type: "table";
  rows?: Array<{
    cells?: IrTableCell[];
  }>;
};

type IrImageBlock = {
  block_type: "image";
  binary_stream_ref?: string | null;
  width?: number | null;
  height?: number | null;
  alt_text?: string | null;
};

type IrBlock = IrParagraphBlock | IrTableBlock | IrImageBlock;

type IrDocument = {
  blocks?: unknown[];
};

class IdGenerator {
  private counters = new Map<string, number>();

  next(prefix: string): string {
    const value = (this.counters.get(prefix) ?? 0) + 1;
    this.counters.set(prefix, value);
    return `${prefix}${value}`;
  }
}

export function irToEditorModel(irDocument: IrDocument): EditorDocument {
  const idGen = new IdGenerator();
  return {
    type: "doc",
    id: idGen.next("doc"),
    children: (irDocument.blocks ?? [])
      .filter(isIrBlock)
      .map((block) => blockToNode(block, idGen)),
  };
}

function isIrBlock(value: unknown): value is IrBlock {
  return typeof value === "object" && value !== null && "block_type" in value;
}

function blockToNode(block: IrBlock, idGen: IdGenerator) {
  if (block.block_type === "paragraph") {
    return paragraphToNode(block, idGen);
  }
  if (block.block_type === "table") {
    return tableToNode(block, idGen);
  }
  return imageToNode(block, idGen);
}

function paragraphToNode(block: IrParagraphBlock, idGen: IdGenerator): ParagraphNode {
  const children: TextNode[] = (block.text_runs ?? [])
    .map((run) => textRunToNode(run, idGen))
    .filter((node): node is TextNode => node !== null);

  return {
    type: "paragraph",
    id: idGen.next("p"),
    attrs: {
      alignment: block.paragraph_style?.alignment ?? "left",
      listKind: irListKindToEditor(block.list_info?.kind),
      listLevel: typeof block.list_info?.level === "number" ? block.list_info.level : undefined,
    },
    children,
  };
}

function irListKindToEditor(
  kind: string | null | undefined,
): "none" | "numbered" | "bullet" | undefined {
  if (kind === "numbered") {
    return "numbered";
  }
  if (kind === "bulleted") {
    return "bullet";
  }
  return "none";
}

function textRunToNode(run: IrTextRun, idGen: IdGenerator): TextNode | null {
  const text = run.kind === "field" ? run.resolved_text ?? "" : run.text ?? "";
  if (!text) {
    return null;
  }

  const marks: TextNode["marks"] = [];
  if (run.character_style?.bold) {
    marks.push({ type: "bold" });
  }
  if (typeof run.character_style?.font_size_pt === "number") {
    marks.push({ type: "fontSize", value: run.character_style.font_size_pt });
  }

  return {
    type: "text",
    id: idGen.next("text"),
    text,
    marks,
  };
}

function tableToNode(block: IrTableBlock, idGen: IdGenerator): TableNode {
  return {
    type: "table",
    id: idGen.next("t"),
    rows: (block.rows ?? []).map((row) => ({
      type: "tableRow",
      id: idGen.next("tr"),
      cells: (row.cells ?? []).map((cell) => tableCellToNode(cell, idGen)),
    })),
  };
}

function tableCellToNode(cell: IrTableCell, idGen: IdGenerator): TableCellNode {
  return {
    type: "tableCell",
    id: idGen.next("tc"),
    colspan: cell.colspan ?? 1,
    rowspan: cell.rowspan ?? 1,
    children: [
      {
        type: "paragraph",
        id: idGen.next("p"),
        attrs: { alignment: "left" },
        children: cell.text
          ? [
              {
                type: "text",
                id: idGen.next("text"),
                text: cell.text,
                marks: [],
              },
            ]
          : [],
      },
    ],
  };
}

function imageToNode(block: IrImageBlock, idGen: IdGenerator): ImageNode {
  return {
    type: "image",
    id: idGen.next("img"),
    attrs: {
      src: block.binary_stream_ref ?? null,
      width: block.width ?? null,
      height: block.height ?? null,
      alt: block.alt_text ?? null,
    },
  };
}
