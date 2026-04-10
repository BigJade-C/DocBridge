import type { EditorDocument } from "./types";
import { getFixtureOption } from "./fixtures";

export type LoadedFixture = {
  fixtureId: string;
  document: EditorDocument;
  originalIr: object;
};

export async function loadFixture(fixtureId: string): Promise<LoadedFixture> {
  const fixture = getFixtureOption(fixtureId);
  if (!fixture) {
    throw new Error(`Unknown fixture: ${fixtureId}`);
  }

  const [editorResponse, irResponse] = await Promise.all([
    fetch(fixture.editorPath),
    fetch(fixture.irPath),
  ]);

  if (!editorResponse.ok) {
    throw new Error(`Failed to load editor fixture: ${editorResponse.status}`);
  }
  if (!irResponse.ok) {
    throw new Error(`Failed to load IR fixture: ${irResponse.status}`);
  }

  return {
    fixtureId,
    document: (await editorResponse.json()) as EditorDocument,
    originalIr: (await irResponse.json()) as object,
  };
}
