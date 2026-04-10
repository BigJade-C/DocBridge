import type { BlockNode, EditorDocument, EditorMark, ImageNode, ParagraphNode, TextNode } from "../types";

export type ParagraphAlignment = "left" | "center" | "right";
export type ParagraphListKind = "none" | "numbered" | "bullet";

export function getTopLevelParagraphs(document: EditorDocument): ParagraphNode[] {
  return document.children.filter((child): child is ParagraphNode => child.type === "paragraph");
}

export function getParagraphById(document: EditorDocument, paragraphId: string): ParagraphNode | null {
  const paragraph = document.children.find(
    (child): child is ParagraphNode => child.type === "paragraph" && child.id === paragraphId,
  );
  return paragraph ?? null;
}

export function getImageById(document: EditorDocument, imageId: string): ImageNode | null {
  const image = document.children.find(
    (child): child is ImageNode => child.type === "image" && child.id === imageId,
  );
  return image ?? null;
}

export function getParagraphText(paragraph: ParagraphNode): string {
  return paragraph.children.map((child) => child.text).join("");
}

export function isParagraphBold(paragraph: ParagraphNode): boolean {
  if (paragraph.children.length === 0) {
    return false;
  }
  return paragraph.children.every((child) => hasMark(child.marks, "bold"));
}

export function getParagraphFontSize(paragraph: ParagraphNode): number | null {
  for (const child of paragraph.children) {
    const mark = child.marks?.find((item): item is Extract<EditorMark, { type: "fontSize" }> => item.type === "fontSize");
    if (mark) {
      return mark.value;
    }
  }
  return null;
}

export function getParagraphListKind(paragraph: ParagraphNode): ParagraphListKind {
  return paragraph.attrs?.listKind ?? "none";
}

export function updateParagraphText(
  document: EditorDocument,
  paragraphId: string,
  nextText: string,
): EditorDocument {
  return updateAnyParagraph(document, paragraphId, (paragraph) => {
    const marks = paragraph.children[0]?.marks ?? [];
    return buildUpdatedParagraphText(document, paragraph, nextText, marks);
  });
}

export function toggleParagraphBold(document: EditorDocument, paragraphId: string): EditorDocument {
  return updateTopLevelParagraph(document, paragraphId, (paragraph) => {
    const shouldEnable = !isParagraphBold(paragraph);
    return {
      ...paragraph,
      children: paragraph.children.map((child) => ({
        ...child,
        marks: replaceMark(child.marks ?? [], shouldEnable ? { type: "bold" } : null, "bold"),
      })),
    };
  });
}

export function setParagraphFontSize(
  document: EditorDocument,
  paragraphId: string,
  value: number,
): EditorDocument {
  return updateTopLevelParagraph(document, paragraphId, (paragraph) => ({
    ...paragraph,
    children: paragraph.children.map((child) => ({
      ...child,
      marks: replaceMark(child.marks ?? [], { type: "fontSize", value }, "fontSize"),
    })),
  }));
}

export function setParagraphAlignment(
  document: EditorDocument,
  paragraphId: string,
  alignment: ParagraphAlignment,
): EditorDocument {
  return updateTopLevelParagraph(document, paragraphId, (paragraph) => ({
    ...paragraph,
    attrs: {
      ...paragraph.attrs,
      alignment,
    },
  }));
}

export function setParagraphListKind(
  document: EditorDocument,
  paragraphId: string,
  listKind: ParagraphListKind,
): EditorDocument {
  return updateTopLevelParagraph(document, paragraphId, (paragraph) => ({
    ...paragraph,
    attrs: {
      ...paragraph.attrs,
      listKind,
      listLevel: listKind === "none" ? undefined : 0,
    },
  }));
}

export function insertParagraphAfter(
  document: EditorDocument,
  paragraphId: string,
): { document: EditorDocument; insertedParagraphId: string } {
  const insertedParagraphId = createNextId(document, "p");
  const insertedTextId = createNextId(document, "text");
  const nextChildren: BlockNode[] = [];

  for (const child of document.children) {
    nextChildren.push(child);
    if (child.type === "paragraph" && child.id === paragraphId) {
      nextChildren.push({
        type: "paragraph",
        id: insertedParagraphId,
        attrs: { alignment: "left" },
        children: [
          {
            type: "text",
            id: insertedTextId,
            text: "",
            marks: [],
          },
        ],
      });
    }
  }

  return {
    document: {
      ...document,
      children: nextChildren,
    },
    insertedParagraphId,
  };
}

export function deleteParagraph(
  document: EditorDocument,
  paragraphId: string,
): { document: EditorDocument; nextSelectedParagraphId: string | null } {
  const nextChildren = document.children.filter(
    (child) => !(child.type === "paragraph" && child.id === paragraphId),
  );
  const nextDocument = {
    ...document,
    children: nextChildren,
  };
  const nextParagraph = getTopLevelParagraphs(nextDocument)[0] ?? null;
  return {
    document: nextDocument,
    nextSelectedParagraphId: nextParagraph?.id ?? null,
  };
}

export function replaceImageSource(
  document: EditorDocument,
  imageId: string,
  nextSource: string,
): EditorDocument {
  return {
    ...document,
    children: document.children.map((child) => {
      if (child.type !== "image" || child.id !== imageId) {
        return child;
      }
      return {
        ...child,
        attrs: {
          ...child.attrs,
          src: nextSource,
        },
      };
    }),
  };
}

export function setImageAltText(
  document: EditorDocument,
  imageId: string,
  altText: string,
): EditorDocument {
  return {
    ...document,
    children: document.children.map((child) => {
      if (child.type !== "image" || child.id !== imageId) {
        return child;
      }
      return {
        ...child,
        attrs: {
          ...child.attrs,
          alt: altText,
        },
      };
    }),
  };
}

function updateTopLevelParagraph(
  document: EditorDocument,
  paragraphId: string,
  updater: (paragraph: ParagraphNode) => ParagraphNode,
): EditorDocument {
  return {
    ...document,
    children: document.children.map((child) => {
      if (child.type !== "paragraph" || child.id !== paragraphId) {
        return child;
      }
      return updater(child);
    }),
  };
}

function updateAnyParagraph(
  document: EditorDocument,
  paragraphId: string,
  updater: (paragraph: ParagraphNode) => ParagraphNode,
): EditorDocument {
  return {
    ...document,
    children: document.children.map((child) => {
      if (child.type === "paragraph") {
        return child.id === paragraphId ? updater(child) : child;
      }
      if (child.type === "table") {
        return {
          ...child,
          rows: child.rows.map((row) => ({
            ...row,
            cells: row.cells.map((cell) => ({
              ...cell,
              children: cell.children.map((paragraph) =>
                paragraph.id === paragraphId ? updater(paragraph) : paragraph,
              ),
            })),
          })),
        };
      }
      return child;
    }),
  };
}

function buildUpdatedParagraphText(
  document: EditorDocument,
  paragraph: ParagraphNode,
  nextText: string,
  marks: EditorMark[],
): ParagraphNode {
  return {
    ...paragraph,
    children: nextText
      ? [
          {
            type: "text",
            id: paragraph.children[0]?.id ?? createNextId(document, "text"),
            text: nextText,
            marks,
          },
        ]
      : [],
  };
}

function createNextId(document: EditorDocument, prefix: string): string {
  const ids = collectIds(document);
  let maxValue = 0;
  for (const id of ids) {
    if (!id.startsWith(prefix)) {
      continue;
    }
    const numeric = Number.parseInt(id.slice(prefix.length), 10);
    if (!Number.isNaN(numeric)) {
      maxValue = Math.max(maxValue, numeric);
    }
  }
  return `${prefix}${maxValue + 1}`;
}

function collectIds(document: EditorDocument): string[] {
  const ids: string[] = [];
  if (document.id) {
    ids.push(document.id);
  }
  for (const child of document.children) {
    ids.push(child.id);
    if (child.type === "paragraph") {
      ids.push(...child.children.map((textNode) => textNode.id));
    }
    if (child.type === "table") {
      for (const row of child.rows) {
        ids.push(row.id);
        for (const cell of row.cells) {
          ids.push(cell.id);
          for (const paragraph of cell.children) {
            ids.push(paragraph.id);
            ids.push(...paragraph.children.map((textNode) => textNode.id));
          }
        }
      }
    }
  }
  return ids;
}

function replaceMark(
  marks: EditorMark[],
  nextMark: EditorMark | null,
  type: EditorMark["type"],
): EditorMark[] {
  const filtered = marks.filter((mark) => mark.type !== type);
  return nextMark ? [...filtered, nextMark] : filtered;
}

function hasMark(marks: EditorMark[] | undefined, type: EditorMark["type"]): boolean {
  return Boolean(marks?.some((mark) => mark.type === type));
}
