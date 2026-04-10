export type EditorMark =
  | { type: "bold" }
  | { type: "fontSize"; value: number };

export type TextNode = {
  type: "text";
  id: string;
  text: string;
  marks?: EditorMark[];
};

export type ParagraphNode = {
  type: "paragraph";
  id: string;
  attrs?: {
    alignment?: string;
    listKind?: "none" | "numbered" | "bullet";
    listLevel?: number;
  };
  children: TextNode[];
};

export type TableCellNode = {
  type: "tableCell";
  id: string;
  colspan?: number;
  rowspan?: number;
  children: ParagraphNode[];
};

export type TableRowNode = {
  type: "tableRow";
  id: string;
  cells: TableCellNode[];
};

export type TableNode = {
  type: "table";
  id: string;
  rows: TableRowNode[];
};

export type ImageNode = {
  type: "image";
  id: string;
  attrs?: {
    src?: string | null;
    width?: number | null;
    height?: number | null;
    alt?: string | null;
  };
};

export type BlockNode = ParagraphNode | TableNode | ImageNode;

export type EditorDocument = {
  type: "doc";
  id?: string;
  children: BlockNode[];
};
