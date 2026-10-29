# Steam Workshop listing

- `description.bbcode`: the full Workshop page text (Steam BBCode). Paste it into the item's description on Steam after the first upload; the in-game uploader only sends the short `Description` from `src/DeepFrontier/manifest.json`.
- `thumbnail.png`: the 640×640 preview (under Steam's 1 MB limit), from an in-game capture.
- `screenshots/`: gallery images to add on the Workshop page (Edit images & videos).

## Uploading

1. Build and install: `powershell -ExecutionPolicy Bypass -File tools/build_deep_frontier.ps1`, then `pwsh tools/verify_deep_frontier_package.ps1 -Build <n>`.
2. Copy `workshop/thumbnail.png` to `Documents\Timberborn\Mods\DeepFrontier\thumbnail.png`. The game's uploader reads `thumbnail.png` from the mod folder.
3. In Timberborn, open the Mods screen, select Deep Frontier and upload it. The game writes `workshop_data.json` (the Workshop item id) into the mod folder; keep that file so later uploads update the same item.
4. Set the required mods as Workshop dependencies: `python tools/workshop_dependencies.py` shows the 17 items it maps from `manifest.json` RequiredMods (through your subscribed copies), and `--apply` adds them to the item with Steam running. The game's uploader does not send them; with them set, Steam lists them under Required items and offers to subscribe to them with Deep Frontier. Run it again whenever `RequiredMods` gains a mod.
5. On Steam, set the description from `description.bbcode` and add the screenshots.
6. For an update, bump `Version` in `src/DeepFrontier/manifest.json` before building, and paste `changenotes-<version>.bbcode` into the item's Change Notes (Steam keeps them per update). `CHANGELOG.md` at the repository root holds the full notes.

To retake screenshots from a save: copy the save into the "Memory Test" settlement, then run `powershell -ExecutionPolicy Bypass -File tools/start_memory_load.ps1 -Build <n> -Label showcase -Save "<copy>" -Showcase -RunSeconds 400` (images land in `outputs/showcase`).
