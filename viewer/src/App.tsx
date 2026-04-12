import { useEffect, useRef, useState } from "react";

import { EditorSurface } from "./components/EditorSurface";
import { buildAutosaveKey } from "./autosave";
import { FixtureSelector } from "./components/FixtureSelector";
import { DEFAULT_FIXTURE_ID, getFixtureOption } from "./fixtures";
import { importDocumentFile } from "./importDocument";
import { loadFixture } from "./loadFixture";
import { loadUploadedJsonFile } from "./uploadDocument";
import type { EditorDocument } from "./types";

type SourceType = "fixture" | "editor-model-json" | "ir-json" | "hwp" | "docx";

export function App() {
  const [document, setDocument] = useState<EditorDocument | null>(null);
  const [originalIr, setOriginalIr] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFixtureId, setSelectedFixtureId] = useState(DEFAULT_FIXTURE_ID);
  const [isLoading, setIsLoading] = useState(true);
  const [sourceLabel, setSourceLabel] = useState(DEFAULT_FIXTURE_ID);
  const [sourceType, setSourceType] = useState<SourceType>("fixture");
  const [isDirty, setIsDirty] = useState(false);
  const [editorSessionKey, setEditorSessionKey] = useState(0);
  const [isDragActive, setIsDragActive] = useState(false);
  const dragDepthRef = useRef(0);

  useEffect(() => {
    let isMounted = true;

    setIsLoading(true);
    setError(null);

    loadFixture(selectedFixtureId)
      .then(({ document: editorPayload, originalIr: irPayload }) => {
        if (isMounted) {
          setDocument(editorPayload);
          setOriginalIr(irPayload);
          setSourceLabel(selectedFixtureId);
          setSourceType("fixture");
          setIsDirty(false);
          setEditorSessionKey((current) => current + 1);
        }
      })
      .catch((err: Error) => {
        if (isMounted) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedFixtureId]);

  const selectedFixture = getFixtureOption(selectedFixtureId);
  const autosaveKey = buildAutosaveKey(sourceType, sourceLabel);

  async function processLocalFile(file: File) {
    const lowerName = file.name.toLowerCase();

    setIsLoading(true);
    setError(null);

    try {
      if (lowerName.endsWith(".json")) {
        const loaded = await loadUploadedJsonFile(file);
        setDocument(loaded.document);
        setOriginalIr(loaded.originalIr);
        setSourceLabel(file.name);
        setSourceType(loaded.kind === "editor-model" ? "editor-model-json" : "ir-json");
        setIsDirty(false);
        setEditorSessionKey((current) => current + 1);
        return;
      }

      if (lowerName.endsWith(".hwp") || lowerName.endsWith(".hwpx") || lowerName.endsWith(".docx")) {
        const imported = await importDocumentFile(file);
        setDocument(imported.document);
        setOriginalIr(imported.originalIr);
        setSourceLabel(file.name);
        setSourceType(lowerName.endsWith(".docx") ? "docx" : "hwp");
        setIsDirty(false);
        setEditorSessionKey((current) => current + 1);
        return;
      }

      throw new Error(`Unsupported file type: ${file.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    await processLocalFile(file);
    event.target.value = "";
  }

  async function handleImportUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    await processLocalFile(file);
    event.target.value = "";
  }

  function handleDragEnter(event: React.DragEvent<HTMLElement>) {
    if (!hasFiles(event)) {
      return;
    }
    event.preventDefault();
    dragDepthRef.current += 1;
    setIsDragActive(true);
  }

  function handleDragOver(event: React.DragEvent<HTMLElement>) {
    if (!hasFiles(event)) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsDragActive(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLElement>) {
    if (!hasFiles(event)) {
      return;
    }
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDragActive(false);
    }
  }

  async function handleDrop(event: React.DragEvent<HTMLElement>) {
    if (!hasFiles(event)) {
      return;
    }
    event.preventDefault();
    dragDepthRef.current = 0;
    setIsDragActive(false);

    const file = event.dataTransfer.files?.[0];
    if (!file) {
      return;
    }
    await processLocalFile(file);
  }

  return (
    <main
      className={`app-shell${isDragActive ? " is-drag-active" : ""}`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <header className="app-header">
        <p className="app-eyebrow">Editor Model v0</p>
        <h1>Basic Editor Demo</h1>
        <div className="app-status-bar" aria-label="Document status">
          <span className="app-status-pill">
            <strong>Name</strong> {sourceLabel}
          </span>
          <span className="app-status-pill">
            <strong>Source</strong> {formatSourceType(sourceType)}
          </span>
          <span className="app-status-pill">
            <strong>Status</strong> {error ? "Error" : isLoading ? "Loading" : document ? "Loaded" : "Idle"}
          </span>
          <span className={`app-status-pill${isDirty ? " is-dirty" : ""}`}>
            <strong>Changes</strong> {isDirty ? "Dirty" : "Clean"}
          </span>
        </div>
        <div className="app-controls">
          <FixtureSelector
            selectedFixtureId={selectedFixtureId}
            disabled={isLoading}
            onChange={setSelectedFixtureId}
          />
          <label className="fixture-selector">
            <span>Upload JSON</span>
            <input
              aria-label="Upload JSON"
              type="file"
              accept=".json,application/json"
              disabled={isLoading}
              onChange={handleFileUpload}
            />
          </label>
          <label className="fixture-selector">
            <span>Import HWP/DOCX</span>
            <input
              aria-label="Import HWP/DOCX"
              type="file"
              accept=".hwp,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              disabled={isLoading}
              onChange={handleImportUpload}
            />
          </label>
        </div>
      </header>

      {error ? <div className="app-error">{error}</div> : null}
      {!error && isLoading ? <div className="app-loading">Loading fixture...</div> : null}
      {isDragActive ? (
        <div className="app-drop-overlay" aria-label="Drop zone">
          <div className="app-drop-card">
            <strong>Drop a file to load it</strong>
            <span>.json, .hwp, .hwpx, .docx</span>
          </div>
        </div>
      ) : null}
      {document && !isLoading ? (
        <EditorSurface
          key={editorSessionKey}
          initialDocument={document}
          originalIr={originalIr}
          autosaveKey={autosaveKey}
          onDirtyChange={setIsDirty}
        />
      ) : null}
    </main>
  );
}

function formatSourceType(sourceType: SourceType): string {
  switch (sourceType) {
    case "fixture":
      return "Fixture";
    case "editor-model-json":
      return "EditorModel JSON";
    case "ir-json":
      return "IR JSON";
    case "hwp":
      return "HWP";
    case "docx":
      return "DOCX";
  }
}

function hasFiles(event: React.DragEvent<HTMLElement>): boolean {
  return Array.from(event.dataTransfer.types).includes("Files");
}
