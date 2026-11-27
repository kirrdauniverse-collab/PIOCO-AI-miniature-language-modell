#!/usr/bin/env python3
# Váz-generátor a micro-ai-models-for-retro-computers repóhoz:
# 17 modell × 28 gép almappa jelző-README-vel + modellek fő README-je.
# Futtatás az ÚJ repó gyökeréből: python3 eszkozok/uj_repo_vaz_generator.py
MODELS=["chatgpt","mistral","grok","meta","glm","kimi","qwen","deepseek","claude",
        "copilot","manus","ernie","gemini","antigravity","windsurf","kiro","opencode"]
MACH=["zx-81","zx-spectrum","zx-spectrum-128","commodore-vic-20","commodore-16",
      "commodore-64","commodore-128","amiga-500","amiga-1200","atari-800xl","atari-st",
      "atari-falcon","bbc","tvc-64","primo","ht-1080z","apple-ii","macintosh",
      "nokia-3650","nokia-6600","java-mobile","nintendo-nes","super-nintendo",
      "playstation","playstation-2","sega-saturn","sega-megadrive-2","colecovision"]
import os
for m in MODELS:
    for g in MACH:
        d=os.path.join(m,g); os.makedirs(d,exist_ok=True)
        open(os.path.join(d,"README.md"),"w").write(
            f"# {g} — {m} port\n\nReserved workspace for the **{m}** model's port to **{g}**.\n"
            "No port yet. When work starts, put the sources, build tools, tests and cassette/tape files here.\n")
    open(os.path.join(m,"README.md"),"w").write(
        f"# {m}\n\nWork directory of the **{m}** model.\n\nEach machine gets its own subfolder (e.g. `{m}/zx-81/`).\n"
        "House rules:\n- Work only inside your own model folder.\n"
        "- One machine = one subfolder; the port contains only machine-specific code (engine, cassette, tests).\n"
        "- Shared knowledge (dictionary, corpus, logs) stays in the model root.\n"
        "- Keep a `CHANGELOG.md` in the model root: version, error description, fix.\n")
print("OK: %d modell x %d gep vaz kesz" % (len(MODELS), len(MACH)))
