import { render, screen, within } from "@testing-library/react";

import fixture from "../test/fixtures/008_mixed.json";
import type { EditorDocument } from "../types";
import { DocView } from "./DocView";

describe("DocView", () => {
  it("renders mixed document blocks in order", () => {
    const { container } = render(<DocView document={fixture as EditorDocument} />);

    const blockSequence = Array.from(container.querySelector(".em-doc")?.children ?? []).map((node) => {
      if (node.matches("p")) {
        return "paragraph";
      }
      if (node.matches(".em-table-wrap")) {
        return "table";
      }
      if (node.matches("figure")) {
        return "image";
      }
      return "unknown";
    });

    expect(blockSequence).toEqual([
      "paragraph",
      "paragraph",
      "table",
      "paragraph",
      "image",
      "paragraph",
    ]);
  });

  it("renders marks, table cells, and image placeholder metadata", () => {
    const { container } = render(<DocView document={fixture as EditorDocument} />);

    const title = screen.getByText("문서 제목");
    expect(title).toBeInTheDocument();
    expect(title).toHaveClass("em-text-bold");
    expect(title).toHaveStyle({ fontSize: "15px" });

    const table = container.querySelector("table");
    expect(table).not.toBeNull();
    expect(within(table as HTMLTableElement).getByText("A")).toBeInTheDocument();
    expect(within(table as HTMLTableElement).getByText("F")).toBeInTheDocument();

    expect(screen.getByText("그림입니다.")).toBeInTheDocument();
    expect(screen.getByText("src: BinData/BIN0001.png")).toBeInTheDocument();
    expect(screen.getByText("size: 444 × 517")).toBeInTheDocument();
  });
});
