# DocBridge Architecture

## 1. High-Level Structure

The system is divided into four layers:

```text
core         -> canonical IR, validators, transforms
importers    -> HWP -> IR, DOCX -> IR
exporters    -> IR -> DOCX, IR -> HWPX, later PDF / HWP
editor/web   -> editor model, UI, rendering, editing
```

---

## 2. Data Flow

```text
HWP file   -> HWP Import Adapter  -> IR
DOCX file  -> DOCX Import Adapter -> IR

IR -> Editor Model -> Web Editor -> Editor Model -> IR

IR -> DOCX Export Adapter
IR -> HWPX Export Adapter
IR -> PDF Export Adapter (later)
```

---

## 3. Modules

### core
- canonical IR models
- validators
- normalization
- style and asset abstractions
- document-level transforms

### importers
- HWP parser and IR converter
- DOCX parser and IR converter

### exporters
- DOCX writer
- HWPX writer
- later: binary HWP research path
- later: PDF export

### editor/web
- editor model
- viewer
- editing operations
- toolbar and UI

### server
- upload / import API
- document persistence
- asset storage
- export API
- autosave / document state

---

## 4. Storage Strategy

- IR JSON -> canonical document storage
- Editor Model JSON -> editing session state
- Binary assets -> separate storage (images / embedded files)

---

## 5. Key Principle

IR is the **single source of truth** for cross-format conversion.

The editor should not directly edit HWP or DOCX structures.
It should edit a format-independent document model.

---

## 6. Extension Points

- DOCX import improvements
- HWPX export
- binary HWP export research
- PDF export
- collaboration
- comments / review features
