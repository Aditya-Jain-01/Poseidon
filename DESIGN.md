---
name: Poseidon
description: A local-first workbench for conversations, agents, and knowledge.
colors:
  canvas-light: "#f7f6f2"
  sidebar-light: "#f3f2ee"
  surface-light: "#fbfaf7"
  ink-light: "#242525"
  action-light: "#2860a4"
  canvas-dark: "#191a1a"
  sidebar-dark: "#222323"
  surface-dark: "#252626"
  ink-dark: "#f1f1ed"
  action-dark: "#8eaee0"
typography:
  display:
    fontFamily: "Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "clamp(26px, 2.2vw, 34px)"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  control: "9px"
  composer: "25px"
  dialog: "28px"
components:
  button-primary:
    backgroundColor: "{colors.action-light}"
    textColor: "#ffffff"
    rounded: "{rounded.control}"
    padding: "10px 17px"
---

# Poseidon interface

<!-- impeccable:design-schema 1 -->

## Direction

Poseidon is an operational workbench for long desktop sessions. The current shell follows the structure in the user's DeepSeek Harness screenshots: one navigation sidebar, a spacious conversation canvas, a wide composer, compact menus, and a large settings dialog. These are layout references, not a source of Poseidon features or branding. Everyday chat remains the primary task.

## Color and type

The light theme uses a warm off-white canvas (`#f7f6f2`), a slightly darker sidebar (`#f3f2ee`), near-black text (`#242525`), and blue actions (`#2860a4`). The dark theme uses a near-black canvas (`#191a1a`), charcoal sidebar (`#222323`), light text (`#f1f1ed`), and a lighter blue action color (`#8eaee0`). Secondary surfaces and thin borders separate controls without turning every section into a card. Status colors communicate actual state.

The interface uses the Segoe UI system stack for headings, controls, and reading. The empty-chat heading is a restrained sans-serif heading, not a large display treatment. Monospace is reserved for paths, identifiers, and code. Do not introduce a new font or color system to imitate a reference screenshot.

## Shell and navigation

A single sidebar holds the Poseidon brand, New Session, Agents, Brain, Gateway, conversation history, and a bottom More menu for Settings and appearance. The main canvas begins beside it with a rounded upper-left corner. The conversation area takes the available width; a right inspector opens when the user asks to inspect a run. The sidebar and inspector can be resized on desktop. At narrow widths, navigation and inspection become overlays so the conversation remains readable.

Navigation labels must name real Poseidon destinations. Do not add visible Plugins, Automation tasks, workspace permissions, or other controls until those actions exist in the product.

## Conversation

An empty session centers a short welcome heading over a wide, two-row composer. The text area occupies the top row; available commands, model settings, and send or stop sit below. The model control reflects the configured model and opens Settings. The plus control opens the existing slash commands. Conversation history uses the same composer width and keeps messages readable rather than stretching text across the canvas.

The composer supports multiline text, keyboard submission, IME composition, and slash-command selection. Menus attach to their trigger and preserve input focus. A reader who scrolls up stays in control of their position; a Jump to latest action returns to the newest message. Tool outputs may collapse their middle lines while retaining the beginning and end. Only show run events and statuses supplied by the backend.

## Settings and secondary views

Settings opens in a centered dialog with a left section list and a scrolling content pane. Its sections are the implemented model, memory, and security settings. On small screens, section tabs become a horizontal row. The Brain and Agents views retain their own task-oriented layouts inside the same shell.

Use separators and spacing for dense information. Reserve cards for content that needs a distinct boundary, such as a settings group, approval, or run receipt. Popovers should be compact, anchored, keyboard reachable, and dismissible.

## Interaction rules

- Keep chat, agent selection, approvals, Brain, and settings discoverable without decorative dashboard metrics.
- Give loading, empty, offline, error, disabled, and approval states clear labels and recovery actions where applicable.
- Preserve visible keyboard focus, sufficient contrast, and reduced-motion behavior.
- Use the interface to describe implemented behavior. A visual control must have a real action behind it.
