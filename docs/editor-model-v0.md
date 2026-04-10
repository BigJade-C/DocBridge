# Editor Model v0

## 1. Purpose

Editor Model is designed for:

- fast rendering
- safe editing
- cursor / selection handling
- partial updates
- a common editing experience for HWP and DOCX imports

It is **not** identical to the canonical IR.

IR is the conversion model.
Editor Model is the interaction model.

---

## 2. Core Structure

```json
{
  "type": "doc",
  "children": []
}
```

---

## 3. Node Types

### Paragraph

```json
{
  "type": "paragraph",
  "id": "p1",
  "attrs": {
    "alignment": "left"
  },
  "children": [
    {
      "type": "text",
      "text": "문서 제목",
      "marks": [
        { "type": "bold" },
        { "type": "fontSize", "value": 15 }
      ]
    }
  ]
}
```

---

### Table

```json
{
  "type": "table",
  "id": "t1",
  "rows": [
    {
      "cells": [
        {
          "colspan": 2,
          "rowspan": 1,
          "children": [
            {
              "type": "paragraph",
              "id": "p2",
              "attrs": {
                "alignment": "left"
              },
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

---

### Image

```json
{
  "type": "image",
  "id": "img1",
  "attrs": {
    "src": "/assets/bin0001.png",
    "width": 444,
    "height": 517,
    "alt": "그림입니다."
  }
}
```

---

## 4. Marks

Initial marks:

- bold
- fontSize

Later:

- color
- underline
- italic
- strike
- fontFamily

---

## 5. Required Properties

- every node must have a stable `id`
- all nodes must be serializable
- no implicit structure
- the model must remain format-neutral

---

## 6. Transform Rules

### IR -> EditorModel

- Paragraph -> paragraph node
- Table -> table node
- Image -> image node

### EditorModel -> IR

- reconstruct canonical blocks
- preserve supported styles
- preserve `style_ref` where possible via attributes / metadata

---

## 7. Design Principles

- minimal but extensible
- explicit structure
- stable IDs for editing
- format-neutral editing
- safe round-trip through IR
