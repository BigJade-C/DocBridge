import { fireEvent, render, screen, within } from "@testing-library/react";

import fixture from "../test/fixtures/008_mixed.json";
import originalIrFixture from "../test/fixtures/008_mixed.ir.json";
import type { EditorDocument } from "../types";
import { EditorSurface } from "./EditorSurface";

const PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5u8AAAAASUVORK5CYII=";

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

  it("numbered list, bullet list, and clear list update paragraph metadata", () => {
    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const paragraph = screen.getByTestId("paragraph-p2");
    fireEvent.focus(paragraph);
    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));

    fireEvent.click(screen.getByRole("button", { name: "Numbered List" }));
    expect(paragraph).toHaveAttribute("data-list-kind", "numbered");
    expect(screen.getByText(/"listKind": "numbered"/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bullet List" }));
    expect(paragraph).toHaveAttribute("data-list-kind", "bullet");
    expect(screen.getByText(/"listKind": "bullet"/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear List" }));
    expect(paragraph).toHaveAttribute("data-list-kind", "none");
    expect(screen.getByText(/"listKind": "none"/)).toBeInTheDocument();
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

  it("table cell text becomes editable while image blocks remain read-only", () => {
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

    const tableParagraph = within(table as HTMLTableElement).getByText("A").closest('[role="textbox"]');
    expect(tableParagraph).toHaveAttribute("contenteditable", "true");
  });

  it("editing table cell text updates the in-memory model while keeping table structure", () => {
    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    const tableCellParagraph = screen.getByTestId("paragraph-p5");
    tableCellParagraph.textContent = "수정된 셀";
    fireEvent.input(tableCellParagraph);
    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));

    expect(screen.getByText("수정된 셀")).toBeInTheDocument();
    expect(screen.getByText(/"text": "수정된 셀"/)).toBeInTheDocument();
    expect(screen.getByText(/"colspan": 1/)).toBeInTheDocument();
    expect(screen.getByText(/"rowspan": 1/)).toBeInTheDocument();
  });

  it("replacing an image updates the in-memory model and preview", async () => {
    render(
      <EditorSurface
        initialDocument={fixture as EditorDocument}
        originalIr={originalIrFixture as object}
      />,
    );

    fireEvent.click(screen.getByTestId("image-img1"));
    const replaceInput = screen.getByLabelText("Replace image") as HTMLInputElement;
    const replacementFile = new File(
      [Uint8Array.from(atob(PNG_BASE64), (char) => char.charCodeAt(0))],
      "replacement.png",
      { type: "image/png" },
    );

    fireEvent.change(replaceInput, { target: { files: [replacementFile] } });

    expect(await screen.findByRole("img", { name: "그림입니다." })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show Debug" }));
    expect(screen.getByText(/"src": "data:image\/png;base64,/)).toBeInTheDocument();
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
