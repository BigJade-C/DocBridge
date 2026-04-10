# DocBridge Roadmap

## Phase 1 - Engine Completion

- HWP parser
- IR v1
- DOCX writer (paragraph path)
- sample validation (001 to 008)

Status: completed

---

## Phase 2 - Multi-Format Import Foundation

- DOCX import adapter
- HWP import hardening
- IR normalization across HWP and DOCX

Goal:
- open both HWP and DOCX in the same canonical pipeline

---

## Phase 3 - Viewer

- IR -> EditorModel
- render:
  - paragraph
  - table
  - image
- read-only mode

Goal:
- view imported HWP and DOCX documents in the browser

---

## Phase 4 - Basic Editor

- text editing
- bold
- font size
- alignment
- add / remove paragraph

Goal:
- edit documents in a common web editor

---

## Phase 5 - Export

- EditorModel -> IR
- IR -> DOCX
- IR -> HWPX

Goal:
- save edited documents back to standard formats

---

## Phase 6 - Advanced Blocks

- table editing
- image replace / resize
- numbering editing
- header / footer editing

---

## Phase 7 - Style Expansion

- color
- font family
- spacing
- indent
- richer field support

---

## Phase 8 - Expansion

- PDF export
- binary HWP export research
- collaboration
- comments
- review workflow

---

## MVP Release

MVP is reached when the system supports:

- HWP import
- DOCX import
- browser viewing
- basic editing
- DOCX export

---

## Guiding Principle

Always prioritize:

1. structural correctness
2. editing stability
3. multi-format interoperability

Not:

- pixel-perfect rendering
- full parity with every desktop editor
