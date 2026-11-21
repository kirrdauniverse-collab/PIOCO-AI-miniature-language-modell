# PIOCO AI — Miniature Language Model

**Pico AI** is an extremely constrained generative language model designed primarily for the **Sinclair ZX81 (16 KB RAM)**.

It aims to provide real (albeit very limited) generation, tokenization, temperature control and multi-load cassette support in a single `.T81` file, instead of hard-coded template answers.

## Current Status

- **Phase 1 (Concept)** — completed  
  See: [`docs/01-KONCEPCIO.md`](docs/01-KONCEPCIO.md)

## Target Platforms (priority order)

1. Sinclair ZX81 16 KB (primary focus)
2. Later: ZX Spectrum 48/128, Commodore 64, Amiga, TVC, Enterprise, Primo, HT1080Z…

## Repository Structure

```
PIOCO-AI-miniature-language-modell/
├── docs/                 # Design documents (Hungarian + English)
├── tools/                # Host-side generators, trainers, packers (Python)
├── src/                  # Z80 source (later)
├── knowledge/            # Knowledge packs
└── releases/             # Ready .T81 files
```

## Important Security Note

If you shared a GitHub Personal Access Token in this conversation, **revoke it immediately** and create a new one with minimal scopes. Tokens in chat history are considered compromised.

## License

To be decided (likely MIT or similar permissive license for retro hobby projects).
