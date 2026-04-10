# IR v1

## Frozen Structures

IR v1 freezes the current document structure, not the full semantic interpretation of every HWP style field.

The following structures are frozen in v1:

- `Document`
- `Document.header`
- `Document.footer`
- `Document.blocks`
- `Paragraph`
- `Table`
- `ImageBlock`
- `TextRun`
- `ParagraphStyle`
- `CharacterStyle`
- `ListInfo`
- field/text run distinction inside `TextRun`

This means downstream code can rely on these model shapes and their nesting, while individual style semantics may still be refined in later phases.

## Currently Supported Semantic Fields

The parser currently resolves only the style semantics that are verified by samples `001` to `008`.

Supported paragraph-level semantics:

- ordered paragraph blocks
- empty paragraph tracking
- paragraph alignment when confidently inferred
- numbering metadata via `list_info`

Supported character-level semantics:

- visible text ordering through `text_runs`
- `bold` when confidently inferred
- `font_size_pt` when confidently inferred
- field runs with `kind="field"` and `resolved_text` when available

Supported non-paragraph block semantics:

- table row and column structure
- table cell text
- merged-cell span metadata (`colspan`, `rowspan`)
- image binary stream reference and basic image metadata
- header/footer block separation from main body blocks

## Intentionally Deferred Style Semantics

The following are intentionally not frozen semantically in v1:

- full paragraph style inheritance
- full character style inheritance
- complete numbering semantics
- border, spacing, indent, and line-height interpretation
- floating or anchored object layout
- complete field/control taxonomy beyond the currently verified cases
- exact meaning of unresolved style table payloads

These may be added later without changing the v1 model layout.

## Preservation Rules

Even when style meaning is not fully resolved, the IR must preserve source references for future phases.

The following must continue to be retained:

- `style_ref`
- numbering and field reference ids
- source indexes and source paths
- `raw` style-related and control-related payloads where already available

This is important because Phase 2 and later will expand semantics by reusing the same IR structure instead of redesigning the model.

## Why v1 Is Still Provisional

IR v1 freezes the container shape so that writer work can start safely.

It does **not** claim that all style meanings are final. The current parser is still sample-driven, and future samples may let us interpret more fields with confidence. The contract for v1 is therefore:

- structure is stable
- supported resolved fields stay supported
- unresolved style and control references remain preserved for future expansion

## Phase 1 DOCX Writer Scope

The Phase 1 DOCX writer targets only the currently proven paragraph path:

- paragraph blocks
- text runs
- paragraph alignment
- bold
- font size
- resolved field text when available

The writer intentionally skips unsupported block types such as tables and images with explicit logging, so Phase 2 can extend writer coverage without changing IR v1.
