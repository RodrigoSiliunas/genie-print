# Genie Print — Context for AI Agents

This folder is a screenshot drop target managed by **Genie Print**, a tool that
auto-uploads screenshots from a developer's local machine via SCP. If you are
an AI agent (Claude Code, Cursor, etc.) operating with access to this folder,
this doc explains what you'll see here.

## What lands here, and how

The user takes a screenshot on their local machine (Win+Shift+S, snipping tool,
Lightshot, Print Screen → Paint, etc.). Genie Print detects the new image,
renames it to a sequential name (`Image #1.png`, `Image #2.jpg`, etc.), and
uploads it here over SCP.

**Numbering** is just `max(existing N) + 1` — there is no project meaning to
the number. Deleting older images and uploading more will reuse those numbers.

## How the user references images

After upload, Genie Print copies a string like:

    @/full/path/to/this/folder/Image #N.png

to the user's local clipboard. They paste that into their AI agent prompt to
attach the image as a file reference.

## What this folder is NOT

- These images are **not** part of the project source. They are scratch
  attachments meant for the current conversation.
- The filenames carry no semantic metadata. Don't infer chronology, task
  scope, or feature areas from the number.
- This folder is typically not version-controlled. Don't `git add` images
  from here unless the user explicitly asks.

## Caveats

- If the user references `@Image #N.png` and the file isn't here yet, ask them
  to retake the screenshot — Genie Print may have errored or not been running.
- Multiple workflows can share one folder; numbering is per-folder, so an
  `Image #5.png` from yesterday is unrelated to one named `Image #5.png` today.
- `AGENTS.md` (this file) is uploaded once on the first run and never
  overwritten. If you want to change it on the remote, edit it there directly
  or delete it locally so the next watcher run reuploads.

---

Genie Print: https://github.com/RodrigoSiliunas/genie-print
