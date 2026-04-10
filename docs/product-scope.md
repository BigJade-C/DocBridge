# DocBridge Product Scope

## 1. Overview

DocBridge is a multi-format document engine and web-based editor platform that enables users to:

- Import HWP and DOCX documents
- Convert them into a unified internal representation (IR)
- Edit documents in a common web editor
- Export documents back to DOCX and HWPX, and later PDF / HWP

This is not just a file converter.

It is a **multi-format document engine + web editor platform**.

---

## 2. Core Value

- One editor experience for both HWP and DOCX
- Format-agnostic canonical document model (IR)
- Clear separation between import, editing, and export
- Strong compatibility path for Korean document workflows

---

## 3. Target Use Cases

- SaMD / regulatory document authoring
- enterprise internal document workflows
- HWP to web editing migration
- Word-compatible browser-based editing
- document automation pipelines

---

## 4. MVP Scope

### Included

- HWP import
- DOCX import
- IR conversion
- Web document viewer
- Basic editing:
  - paragraph text
  - bold
  - font size
  - alignment
- Table rendering
- Image rendering
- DOCX export

### Deferred

- HWPX export
- binary HWP export
- collaborative editing
- track changes
- comments
- advanced layout (floating objects)
- native PDF layout engine

---

## 5. Product Positioning

DocBridge =

> “A multi-format document engine with a common web editor for HWP and DOCX”

---

## 6. Non-Goals for MVP

- pixel-perfect rendering
- full MS Word feature parity
- full Hangul feature parity
- perfect round-trip fidelity for all advanced controls

The MVP focuses on **structural fidelity**, not layout perfection.
