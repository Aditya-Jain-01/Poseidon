---
name: Poseidon
description: An approachable, offline-first workbench for chat, agents, and knowledge.
colors:
  white-canvas: "#ffffff"
  pale-sidebar: "#f9f9f8"
  ink: "#0b0d0f"
  ink-secondary: "#34383c"
  blue-action: "#006dbd"
  pixel-blue: "#08a4fb"
  charcoal-canvas: "#101114"
  charcoal-surface: "#1c1e22"
  cyan-action: "#74c9ff"
typography:
  display:
    fontFamily: "Instrument Serif, Georgia, serif"
    fontSize: "clamp(5rem, 7vw, 7.6rem)"
    fontWeight: 400
    lineHeight: 0.94
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  control: "8px"
  composer: "14px"
  panel: "16px"
components:
  button-primary:
    backgroundColor: "{colors.blue-action}"
    textColor: "{colors.white-canvas}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
---

# Poseidon interface

<!-- impeccable:design-schema 1 -->

## Overview
An editorial workbench for long sessions. Chat is the central work surface; navigation and inspection stay quiet until needed. The reference is the generous white space, oversized italic serif, black type, and electric-blue pixel texture in the user's [andreas.vision](https://andreas.vision/) screenshots. The app keeps its operational controls and content.

## Colors
- White is the main canvas, with near-black type and quiet gray separators. Electric blue belongs to the pixel artwork; a darker blue serves readable links and actions.
- Dark mode uses charcoal surfaces, white type, and cyan actions. Status colors remain semantic.

## Typography
The empty chat headline uses bundled Instrument Serif Italic. App controls and long-form content use the local system sans stack. Paths and IDs use monospace. The serif is reserved for expressive welcome moments so it does not slow scanning on task screens.

## Layout
The chat headline and composer lead the empty session. Pixel texture frames the edges while the center stays open. Secondary actions form a quiet list. Brain questions lead its reading path, followed by source entry and graph exploration. Narrow screens collapse into one readable column.

## Elevation & Depth
The composer has a faint neutral shadow. Dense information uses separators more often than cards. The pixel field reveals once on entry and stops moving when reduced motion is requested.

## Shapes
Controls use soft corners and visible keyboard focus. Pixel artwork retains crisp square edges.

## Components
The agent roster is a denser operational surface inspired by the user's Pulse reference. Its layout stays operational while adopting white, black, and blue. Summary counts come from configured agents, checked connections, and assigned tool types. Task volume, spend, and success rate await real measurements. The selected agent's configuration lives in a right detail column.

## Do's and Don'ts
- Keep the welcome expressive and the working views direct.
- Use pixel artwork as a frame, not behind reading text.
- Keep both themes legible and preserve reduced-motion behavior.
- Do not invent operational metrics.
