# HWP Parser

Minimal foundation for exploring Hangul Word Processor containers.

Current scope:

- open `.hwp` files with `olefile`
- open `.hwpx` files as ZIP containers
- print internal stream or entry structure
- extract selected streams or entries into a debug folder
- emit a simple JSON summary

Out of scope for now:

- full HWP parsing
- DOCX generation
