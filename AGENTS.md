# Agent Guide

## Korean Input Workflow

When the user's input is in Korean, follow this workflow for every response:

1. Internally translate the request into an optimized English prompt.
2. Preserve all technical terms, file paths, variable names, and code identifiers as-is.
3. Restructure the translated prompt into clear, actionable imperative instructions.
4. Briefly show the translated prompt to the user prefixed with `-> `.
5. Immediately execute the requested task after showing the translated prompt.
6. Respond to the user in Korean.

## Implementation Notes

- Do not ask unnecessary clarification questions when a reasonable assumption is possible.
- Keep the visible translated prompt brief and execution-focused.
- Preserve existing repository conventions unless the user explicitly asks otherwise.
