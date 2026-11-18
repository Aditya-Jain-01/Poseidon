# Poseidon

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
The primary user is a person working from a desktop over long sessions. Everyday chat is the main entry point; the Brain is a supporting knowledge workspace.

## Product Purpose
Poseidon is an offline-first assistant that helps the user work with conversations, local memory, agents, and an Obsidian-readable knowledge base. Success means the user can ask, organize evidence, and carry out tasks from one workspace.

## Operating Context
The user works in chat, inspects agent activity, manages model settings, and files source notes into a local Brain. The Brain keeps original notes in `memory-store/brain/raw` and generated topic pages in `memory-store/brain/wiki`. Telegram is an optional channel.

## Capabilities and Constraints
- React and vanilla CSS frontend; Python backend.
- Local-first data and model use. Remote Brain inference requires an explicit setting.
- Chat, Brain, Gateway, Settings, and an optional inspector coexist in the desktop app.
- Brain ingestion, questions with source references, health checks, and a source-to-topic graph are implemented.
- Normal chat does not yet automatically read or write the Brain.

## Brand Commitments
The product name is Poseidon. The user wants an interface that feels like a calm workbench during hours of use, with everyday chat setting the visual direction.

## Evidence on Hand
The current application and its screens are the source of product behavior. No external testimonials, usage metrics, or brand identity system have been provided.

## Product Principles
- Keep the primary chat task clear.
- Make evidence and agent actions inspectable.
- Preserve the local-first default.
- Keep secondary tools available without crowding the daily workflow.
