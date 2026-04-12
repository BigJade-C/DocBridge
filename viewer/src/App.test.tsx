import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { buildAutosaveKey } from "./autosave";
import { App } from "./App";

function buildResponse(payload: object) {
  return {
    ok: true,
    json: async () => payload,
  };
}

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
  });

  it("loads the default 008 fixture and switches to another fixture", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/003_table_basic.json")) {
        const mod = await import("./test/fixtures/003_table_basic.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/003_table_basic.ir.json")) {
        const mod = await import("./test/fixtures/003_table_basic.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);

    const statusBar = screen.getByLabelText("Document status");
    expect(await screen.findByText("문서 제목")).toBeInTheDocument();
    expect(within(statusBar).getByText("008_mixed")).toBeInTheDocument();
    expect(within(statusBar).getByText("Fixture")).toBeInTheDocument();
    expect(within(statusBar).getByText("Loaded")).toBeInTheDocument();
    expect(within(statusBar).getByText("Clean")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Fixture"), {
      target: { value: "003_table_basic" },
    });

    await waitFor(() => {
      expect(within(statusBar).getByText("003_table_basic")).toBeInTheDocument();
    });
    expect(await screen.findByText("표 예제")).toBeInTheDocument();
    expect(screen.getByText("표 아래 설명")).toBeInTheDocument();
  });

  it("shows drag-over feedback and loads dropped JSON files", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const { container } = render(<App />);
    await screen.findByText("문서 제목");

    fireEvent.dragEnter(container.firstChild as HTMLElement, {
      dataTransfer: { types: ["Files"], files: [] },
    });
    expect(screen.getByLabelText("Drop zone")).toBeInTheDocument();

    const droppedFile = new File(
      [
        JSON.stringify({
          type: "doc",
          id: "doc-drop",
          children: [
            {
              type: "paragraph",
              id: "p-drop",
              attrs: { alignment: "left" },
              children: [{ type: "text", id: "t-drop", text: "드롭 문서", marks: [] }],
            },
          ],
        }),
      ],
      "dropped.json",
      { type: "application/json" },
    );

    fireEvent.drop(container.firstChild as HTMLElement, {
      dataTransfer: { types: ["Files"], files: [droppedFile] },
    });

    expect(await screen.findByText("드롭 문서")).toBeInTheDocument();
    expect(screen.queryByLabelText("Drop zone")).not.toBeInTheDocument();
  });

  it("uploads Editor Model JSON and then still allows fixture switching", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/001_text_only.json")) {
        const mod = await import("./test/fixtures/001_text_only.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/001_text_only.ir.json")) {
        const mod = await import("./test/fixtures/001_text_only.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);

    const statusBar = screen.getByLabelText("Document status");
    await screen.findByText("문서 제목");

    const uploadedDoc = {
      type: "doc",
      id: "doc-upload",
      children: [
        {
          type: "paragraph",
          id: "p-upload",
          attrs: { alignment: "left" },
          children: [{ type: "text", id: "t-upload", text: "업로드 문단", marks: [] }],
        },
      ],
    };
    const fileInput = screen.getByLabelText("Upload JSON") as HTMLInputElement;
    const uploadFile = new File([JSON.stringify(uploadedDoc)], "uploaded-editor.json", {
      type: "application/json",
    });

    fireEvent.change(fileInput, { target: { files: [uploadFile] } });

    expect(await screen.findByText("업로드 문단")).toBeInTheDocument();
    expect(screen.getByText("uploaded-editor.json")).toBeInTheDocument();
    expect(screen.getByText("EditorModel JSON")).toBeInTheDocument();
    expect(within(statusBar).getByText("Clean")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Fixture"), {
      target: { value: "001_text_only" },
    });

    expect(await screen.findByText("제목입니다")).toBeInTheDocument();
    expect(screen.getByText("첫 번째 문단입니다")).toBeInTheDocument();
  });

  it("uploads IR JSON and renders it after conversion", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);
    const statusBar = screen.getByLabelText("Document status");
    await screen.findByText("문서 제목");

    const uploadedIr = {
      source_path: "BodyText/Section0",
      blocks: [
        {
          block_type: "paragraph",
          paragraph_style: { alignment: "center" },
          text_runs: [
            {
              kind: "text",
              text: "IR 업로드 문단",
              character_style: { bold: true, font_size_pt: 18 },
            },
          ],
        },
      ],
    };
    const fileInput = screen.getByLabelText("Upload JSON") as HTMLInputElement;
    const uploadFile = new File([JSON.stringify(uploadedIr)], "uploaded-ir.json", {
      type: "application/json",
    });

    fireEvent.change(fileInput, { target: { files: [uploadFile] } });

    const paragraph = await screen.findByText("IR 업로드 문단");
    expect(paragraph).toBeInTheDocument();
    expect(screen.getByText("uploaded-ir.json")).toBeInTheDocument();
    expect(screen.getByText("IR JSON")).toBeInTheDocument();
    expect(within(statusBar).getByText("Clean")).toBeInTheDocument();
    expect(paragraph).toHaveStyle({
      fontWeight: "700",
      fontSize: "18px",
      textAlign: "center",
    });
  });

  it("shows a clear error for invalid JSON uploads", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);
    const statusBar = screen.getByLabelText("Document status");
    await screen.findByText("문서 제목");

    const fileInput = screen.getByLabelText("Upload JSON") as HTMLInputElement;
    const invalidFile = new File(["{not valid json"], "broken.json", {
      type: "application/json",
    });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(await screen.findByText("Invalid JSON file")).toBeInTheDocument();
  });

  it("shows a clear error for dropped invalid files", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const { container } = render(<App />);
    await screen.findByText("문서 제목");

    const invalidFile = new File(["bad"], "dropped.txt", { type: "text/plain" });
    fireEvent.drop(container.firstChild as HTMLElement, {
      dataTransfer: { types: ["Files"], files: [invalidFile] },
    });

    expect(await screen.findByText("Unsupported file type: dropped.txt")).toBeInTheDocument();
  });

  it("uploads HWP through the import adapter path", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      if (url === "/api/import-document") {
        const payload = JSON.parse(String(init?.body));
        expect(payload.fileName).toBe("sample.hwp");
        return buildResponse({
          blocks: [
            {
              block_type: "paragraph",
              paragraph_style: { alignment: "left" },
              text_runs: [{ kind: "text", text: "HWP 가져오기 결과" }],
            },
          ],
        });
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);
    const statusBar = screen.getByLabelText("Document status");
    await screen.findByText("문서 제목");

    const fileInput = screen.getByLabelText("Import HWP/DOCX") as HTMLInputElement;
    const uploadFile = new File(["fake-hwp"], "sample.hwp");
    fireEvent.change(fileInput, { target: { files: [uploadFile] } });

    expect(await screen.findByText("HWP 가져오기 결과")).toBeInTheDocument();
    expect(screen.getByText("sample.hwp")).toBeInTheDocument();
    expect(screen.getByText("HWP")).toBeInTheDocument();
    expect(within(statusBar).getByText("Clean")).toBeInTheDocument();
  });

  it("uploads DOCX through the import adapter path", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      if (url === "/api/import-document") {
        const payload = JSON.parse(String(init?.body));
        expect(payload.fileName).toBe("sample.docx");
        return buildResponse({
          blocks: [
            {
              block_type: "paragraph",
              paragraph_style: { alignment: "right" },
              text_runs: [{ kind: "text", text: "DOCX 가져오기 결과" }],
            },
          ],
        });
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);
    const statusBar = screen.getByLabelText("Document status");
    await screen.findByText("문서 제목");

    const fileInput = screen.getByLabelText("Import HWP/DOCX") as HTMLInputElement;
    const uploadFile = new File(["fake-docx"], "sample.docx");
    fireEvent.change(fileInput, { target: { files: [uploadFile] } });

    const paragraph = await screen.findByText("DOCX 가져오기 결과");
    expect(paragraph).toBeInTheDocument();
    expect(screen.getByText("sample.docx")).toBeInTheDocument();
    expect(screen.getByText("DOCX")).toBeInTheDocument();
    expect(within(statusBar).getByText("Clean")).toBeInTheDocument();
    expect(paragraph).toHaveStyle({ textAlign: "right" });
  });

  it("marks the current document dirty after editing and resets on fixture switch", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/001_text_only.json")) {
        const mod = await import("./test/fixtures/001_text_only.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/001_text_only.ir.json")) {
        const mod = await import("./test/fixtures/001_text_only.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);

    const statusBar = screen.getByLabelText("Document status");
    const paragraph = await screen.findByTestId("paragraph-p2");
    paragraph.textContent = "수정된 첫 번째 문단";
    fireEvent.input(paragraph);

    expect(within(statusBar).getByText("Dirty")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Fixture"), {
      target: { value: "001_text_only" },
    });

    await screen.findByText("제목입니다");
    expect(within(statusBar).getByText("Clean")).toBeInTheDocument();
  });

  it("uses a different autosave key when loading a different document", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/001_text_only.json")) {
        const mod = await import("./test/fixtures/001_text_only.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/001_text_only.ir.json")) {
        const mod = await import("./test/fixtures/001_text_only.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);

    const firstParagraph = await screen.findByTestId("paragraph-p2");
    firstParagraph.textContent = "첫 문서 변경";
    fireEvent.input(firstParagraph);
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 1600));
    });

    const firstKey = buildAutosaveKey("fixture", "008_mixed");
    expect(window.localStorage.getItem(firstKey)).toContain("첫 문서 변경");

    fireEvent.change(screen.getByLabelText("Fixture"), {
      target: { value: "001_text_only" },
    });

    await screen.findByText("제목입니다");

    const secondKey = buildAutosaveKey("fixture", "001_text_only");
    expect(secondKey).not.toBe(firstKey);
    expect(window.localStorage.getItem(secondKey)).toBeNull();
  });

  it("shows a clear error for unsupported import file types", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/fixtures/008_mixed.json")) {
        const mod = await import("./test/fixtures/008_mixed.json");
        return buildResponse(mod.default as object);
      }
      if (url.endsWith("/fixtures/008_mixed.ir.json")) {
        const mod = await import("./test/fixtures/008_mixed.ir.json");
        return buildResponse(mod.default as object);
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<App />);
    await screen.findByText("문서 제목");

    const fileInput = screen.getByLabelText("Import HWP/DOCX") as HTMLInputElement;
    const uploadFile = new File(["bad"], "sample.txt");
    fireEvent.change(fileInput, { target: { files: [uploadFile] } });

    expect(await screen.findByText("Unsupported file type: sample.txt")).toBeInTheDocument();
  });
});
