# micro-ai-models-for-retro-computers

Tiny generative AI models (miniature language models) ported to retro and classic computers.
Every AI model has its own top-level work directory; every target machine has its own subfolder inside it.

## Models (top level)
chatgpt · mistral · grok · meta · glm · kimi · qwen · deepseek · claude · copilot · manus · ernie · gemini · antigravity · windsurf · kiro · opencode

## Target machines (subfolder in every model dir)
zx-81 · zx-spectrum · zx-spectrum-128 · commodore-vic-20 · commodore-16 · commodore-64 · commodore-128 · amiga-500 · amiga-1200 · atari-800xl · atari-st · atari-falcon · bbc · tvc-64 · primo · ht-1080z · apple-ii · macintosh · nokia-3650 · nokia-6600 · java-mobile · nintendo-nes · super-nintendo · playstation · playstation-2 · sega-saturn · sega-megadrive-2 · colecovision

## Status (active ports)
| Model | Machine | Status |
| --- | --- | --- |
| mistral | zx-81 | in progress — migrating from PIOCO-AI-miniature-language-modell |
| others | — | not started |

## Rules
- Each model works only in its own folder; one machine = one subfolder.
- Version numbers in delivered filenames (e.g. `MISTRAL_v072.T81`).
- Every delivered file comes with documentation + full source + knowledge table of contents.
