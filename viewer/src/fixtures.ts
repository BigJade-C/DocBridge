export type FixtureOption = {
  id: string;
  label: string;
  editorPath: string;
  irPath: string;
};

export const FIXTURE_OPTIONS: readonly FixtureOption[] = [
  {
    id: "001_text_only",
    label: "001_text_only",
    editorPath: "/fixtures/001_text_only.json",
    irPath: "/fixtures/001_text_only.ir.json",
  },
  {
    id: "003_table_basic",
    label: "003_table_basic",
    editorPath: "/fixtures/003_table_basic.json",
    irPath: "/fixtures/003_table_basic.ir.json",
  },
  {
    id: "008_mixed",
    label: "008_mixed",
    editorPath: "/fixtures/008_mixed.json",
    irPath: "/fixtures/008_mixed.ir.json",
  },
];

export const DEFAULT_FIXTURE_ID = "008_mixed";

export function getFixtureOption(fixtureId: string): FixtureOption | undefined {
  return FIXTURE_OPTIONS.find((fixture) => fixture.id === fixtureId);
}
