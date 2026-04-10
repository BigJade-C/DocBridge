import { fireEvent, render, screen, within } from "@testing-library/react";

import fixture from "../test/fixtures/008_mixed.json";
import originalIrFixture from "../test/fixtures/008_mixed.ir.json";
import type { EditorDocument } from "../types";
import { EditorSurface } from "./EditorSurface";

describe("EditorSurface", () => {
  it("editing text updates the in-memory model and rendered paragraph", () => {
    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const paragraph = screen.getByTestId("paragraph-p2");
    paragraph.textContent = "수정된 첫 번째 문단";
    fireEvent.input(paragraph);
    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));

    expect(screen.getByText("수정된 첫 번째 문단")).toBeInTheDocument();
    expect(screen.getByText(/"text": "수정된 첫 번째 문단"/)).toBeInTheDocument();
  });

  it("bold, font size, and alignment controls update paragraph formatting", () => {
    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const paragraph = screen.getByTestId("paragraph-p2");
    fireEvent.focus(paragraph);

    fireEvent.click(screen.getByRole("button", { name: "Bold" }));
    expect(paragraph).toHaveStyle({ fontWeight: "700" });
    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));
    expect(screen.getByText(/"type": "bold"/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Font size"), { target: { value: "18" } });
    expect(paragraph).toHaveStyle({ fontSize: "18px" });
    expect(screen.getByText(/"value": 18/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "center" }));
    expect(paragraph).toHaveStyle({ textAlign: "center" });
    expect(screen.getAllByText(/"alignment": "center"/).length).toBeGreaterThan(0);
  });

  it("insert and delete paragraph keep document structure stable", () => {
    const { container } = render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const beforeParagraphCount = container.querySelectorAll('[data-testid^="paragraph-"]').length;

    fireEvent.focus(screen.getByTestId("paragraph-p2"));
    fireEvent.click(screen.getByRole("button", { name: "Insert paragraph" }));

    const afterInsertCount = container.querySelectorAll('[data-testid^="paragraph-"]').length;
    expect(afterInsertCount).toBe(beforeParagraphCount + 1);

    const paragraphs = container.querySelector(".em-doc")?.querySelectorAll('[data-testid^="paragraph-"]') ?? [];
    expect(paragraphs.length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Delete paragraph" }));
    const afterDeleteCount = container.querySelectorAll('[data-testid^="paragraph-"]').length;
    expect(afterDeleteCount).toBe(beforeParagraphCount);
  });

  it("table and image remain read-only while paragraph editing is enabled", () => {
    const { container } = render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const table = container.querySelector("table");
    expect(table).not.toBeNull();
    expect(within(table as HTMLTableElement).getByText("A")).toBeInTheDocument();

    const imagePlaceholder = screen.getByText("src: BinData/BIN0001.png");
    expect(imagePlaceholder).toBeInTheDocument();

    const tableParagraph = within(table as HTMLTableElement).getByText("A").closest("p");
    expect(tableParagraph).not.toHaveAttribute("contenteditable", "true");
  });

  it("keeps the debug panel hidden by default and toggles it on demand", () => {
    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    expect(screen.queryByText(/"type": "doc"/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));
    expect(screen.getByText(/"type": "doc"/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Hide Debug" }));
    expect(screen.queryByText(/"type": "doc"/)).not.toBeInTheDocument();
  });

  it("exports the current edited document as a DOCX download", async () => {
    const blob = new Blob(["docx-bytes"], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => blob,
    });
    const createObjectURLMock = vi.fn().mockReturnValue("blob:docx");
    const revokeObjectURLMock = vi.fn();
    const clickMock = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    globalThis.fetch = fetchMock as typeof fetch;
    URL.createObjectURL = createObjectURLMock;
    URL.revokeObjectURL = revokeObjectURLMock;

    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const paragraph = screen.getByTestId("paragraph-p2");
    paragraph.textContent = "내보낼 문단";
    fireEvent.input(paragraph);
    fireEvent.focus(paragraph);
    fireEvent.click(screen.getByRole("button", { name: "Bold" }));
    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));

    fireEvent.click(screen.getByRole("button", { name: "Export DOCX" }));

    await screen.findByText("DOCX exported");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, requestInit] = fetchMock.mock.calls[0];
    const payload = JSON.parse(String(requestInit?.body));
    expect(payload.editorModel.children[1].children[0].text).toBe("내보낼 문단");
    expect(payload.originalIr).toBeTruthy();
    expect(createObjectURLMock).toHaveBeenCalledWith(blob);
    expect(revokeObjectURLMock).toHaveBeenCalled();
    clickMock.mockRestore();
  });
});
