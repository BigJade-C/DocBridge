import { FIXTURE_OPTIONS } from "../fixtures";

type FixtureSelectorProps = {
  selectedFixtureId: string;
  disabled?: boolean;
  onChange: (fixtureId: string) => void;
};

export function FixtureSelector({
  selectedFixtureId,
  disabled = false,
  onChange,
}: FixtureSelectorProps) {
  return (
    <label className="fixture-selector">
      <span>Fixture</span>
      <select
        aria-label="Fixture"
        value={selectedFixtureId}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {FIXTURE_OPTIONS.map((fixture) => (
          <option key={fixture.id} value={fixture.id}>
            {fixture.label}
          </option>
        ))}
      </select>
    </label>
  );
}
