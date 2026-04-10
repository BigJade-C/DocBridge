# IR Draft

## Current Scope

The current Internal Representation (IR) is intentionally minimal and only models features that are already supported by verified parser behavior in:

- `001_text_only`
- `002_paragraph_style`
- `003_table_basic`

The IR currently supports:

- an ordered `Document.blocks` sequence
- paragraph blocks
- basic table blocks
- visible text preservation
- empty paragraph tracking
- paragraph alignment when resolved
- paragraph style references
- text runs
- character bold when resolved
- character font size in points when resolved
- character style references
- table row and column counts
- ordered table cells
- cell text extraction

## Current Structure

- `Document` contains an ordered list of blocks
- `Paragraph` and `Table` are the currently supported block types
- `Paragraph` contains:
  - `text_runs`
  - `paragraph_style`
  - `is_empty`
  - `paragraph_type`
- `TextRun` contains:
  - `text`
  - `character_style`
- `Table` contains:
  - `rows`
  - `row_count`
  - `column_count`
- `TableRow` contains:
  - `cells`
- `TableCell` contains:
  - `text`
  - source row and column indexes
- `ParagraphStyle` contains:
  - `alignment`
  - `style_ref`
- `CharacterStyle` contains:
  - `bold`
  - `font_size_pt`
  - `style_ref`

## What Is Intentionally Not Supported Yet

The IR does not yet model:

- images
- numbering structures
- header and footer regions
- merged cells
- final normalized style inheritance
- final document layout semantics
- DOCX output

Those features are intentionally excluded because the parser has not yet verified enough evidence from samples `003` to `008`.

## Growth Path For Samples 003 To 008

The IR is designed so future block types can be added without rewriting the document model:

- `Table` can be added as another block type beside `Paragraph`
- existing `Table` can grow to include merged-cell metadata, borders, and cell spans
- `Image` can be attached either as a block or an inline run once evidence is strong enough
- numbering can extend paragraph metadata without changing document ordering
- header and footer content can be added as separate document sections later
- merged cells can live inside future table-specific models rather than forcing paragraph changes

Because `Document` already stores an ordered block list, expanding beyond paragraphs should not require a major structural rewrite.

## Why The IR Is Still Provisional

The current IR is a draft, not a frozen final schema.

Reasons:

- current parser coverage is still sample-driven
- several style meanings are inferred conservatively rather than fully proven
- future samples may reveal block types or relationships that should reshape the final model
- we want to avoid freezing a speculative schema too early

For now the goal is to provide a clean, typed, testable structure that matches verified behavior and is easy to inspect in JSON during development.
