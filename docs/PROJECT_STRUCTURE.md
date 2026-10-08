# cartoon-maker — Project Structure

**Guiding principle:** build for **one real character (KIKO)** now, with a
**clearly repeatable pattern** so adding a second character later is a copy, not a
redesign. Do **not** pre-create empty folders for characters that don't exist yet
— empty scaffolding rots and drifts from reality. The multi-character design lives
in the *pattern*, not in pre-built empty trees.

Two hard boundaries keep this clean:

- **`assets/` = inputs you bring in** (reference art, textures, external/image-to-3D
  models). Things that originate outside Blender.
- **`projects/` = working files you generate** (`.blend` masters, tests, renders,
  reports). Things Blender produces.

- **`cartoon_studio/` = code** (the reusable engine). Stable; you edit it rarely.
- **`scenes/`, `presets/`, `stories/` = data** (JSON). This is what you edit daily
  to control the engine.

---

## Top level

```
cartoon-maker/
│
├── README.md                      # what this project is, how to run it
├── TASKS.md                       # running task list
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── KIKO_MASTER_IMPLEMENTATION_PLAN.md   # the 14-stage roadmap (source of truth)
├── KIKO_IMPLEMENTATION_STATUS.md        # live checklist the agent updates per stage
│
├── cartoon_engine.py              # single entry point: blender ... -- <scene.json>
│
├── cartoon_studio/                # CODE — the reusable engine (see below)
├── assets/                        # INPUTS — references, textures, external models
├── projects/                      # OUTPUTS — .blend working files, renders, reports
├── scenes/                        # DATA — per-shot JSON the engine runs
├── presets/                       # DATA — reusable character/camera/light/render JSON
├── schemas/                       # JSON schemas that validate scenes/presets
├── stories/                       # DATA — multi-shot episode scripts
├── tools/                         # standalone helper scripts (inspect, turnaround)
├── docs/                          # documentation
├── tests/                         # automated tests
└── archive/                       # rejected / superseded work (never auto-deleted)
```

---

## `cartoon_studio/` — the engine (code)

This is character-agnostic. Character-specific knowledge lives in small per-character
modules, but you only create a character folder when that character is real.

```
cartoon_studio/
├── __init__.py
│
├── engine/                        # orchestration — reads JSON, drives Blender
│   ├── runner.py                  #   top-level run loop
│   ├── loader.py                  #   loads .blend + assets named in JSON
│   ├── validator.py               #   validates JSON against schemas/, fails loud
│   ├── context.py                 #   shared run state
│   └── registry.py                #   maps action/character names -> handlers
│
├── animation/                     # action library — character-agnostic
│   ├── locomotion.py              #   shared phase logic (contact/down/passing/up/air)
│   ├── run.py
│   ├── walk.py
│   ├── jump.py
│   ├── gestures.py                #   nod, wave, point, crouch, look_around, etc.
│   ├── face.py                    #   expression + (later) viseme driving
│   ├── ears.py                    #   ear chain follow-through
│   └── tail.py                    #   tail chain follow-through
│
├── blender/                       # thin wrappers over bpy — reused everywhere
│   ├── scene.py
│   ├── camera.py
│   ├── lighting.py
│   ├── materials.py
│   ├── rigging.py
│   ├── render.py
│   └── io.py                      #   load/save/append .blend, ffmpeg encode
│
├── characters/                    # per-character modules — ONE folder per REAL character
│   ├── base.py                    #   Character base class (interface all chars implement)
│   ├── registry.py                #   discovers available characters
│   │
│   └── kiko/                      #   the ONLY character folder that exists now
│       ├── rig.py                 #   bone names, chains, IK targets for KIKO_RIG_armature
│       ├── controls.py            #   animator controls / constraint setup
│       ├── expressions.py         #   FACE_/POSE_ library
│       ├── visemes.py             #   viseme shape-key map (built in Stage 3)
│       ├── presets.py             #   default params
│       └── validator.py           #   deformation QA checks specific to KIKO
│
├── environments/                  # start with generic; add named ones when used
│   ├── generic.py                 #   ground plane + neutral bg (used by all tests)
│   └── jungle.py                  #   only because Runaway Fruit already uses it
│
├── lipsync/                       # Khmer lip-sync (Stage 10) — stub until then
├── audio/                         # audio handling (ties to your VoxCPM2 output)
└── utils/
```

> **When Tavi becomes real:** `cp -r cartoon_studio/characters/kiko cartoon_studio/characters/tavi`,
> then edit. Not before. Same for `flight.py`-type specials — add the module to the
> character that needs it, don't pre-scatter empty ones.

---

## `assets/` — inputs (things you bring in)

```
assets/
├── characters/
│   └── kiko/                      # only KIKO exists
│       ├── reference/
│       │   └── kiko.png           # the authoritative concept art (Stage 5 input)
│       ├── textures/
│       ├── materials/
│       ├── models/                # your own source models
│       └── external/              # image-to-3D output (Meshy/Tripo) lands here
│
├── environments/
├── props/
├── audio/                         # Khmer narration from the VoxCPM2 pipeline
├── sfx/
└── music/
```

---

## `projects/` — outputs (things Blender generates)

```
projects/
├── characters/
│   └── kiko/                      # only KIKO exists
│       ├── blends/
│       │   ├── master/
│       │   │   ├── KIKO_master_v1_1.blend   # protected — never overwrite
│       │   │   └── KIKO_master_v2.blend     # additive expressive rig (Stage 3)
│       │   ├── tests/
│       │   │   ├── KIKO_run_test_5s.blend
│       │   │   └── KIKO_acting_test_8s.blend
│       │   └── backups/                     # timestamped safety copies
│       ├── reports/
│       │   └── kiko_project_audit.md         # Stage 1 output
│       └── review/                           # validation contact sheets per stage
│
└── episodes/
    └── runaway_fruit/
        ├── scene.blend
        ├── story.json
        ├── shots/
        └── reports/
```

---

## `scenes/` — per-shot JSON (what you edit daily)

```
scenes/
├── tests/
│   ├── kiko_run_5s.json           # the Stage 2 locomotion gate
│   └── kiko_acting_8s.json        # the Stage 4 acting gate
└── episodes/
    └── runaway_fruit.json
```

> Add `tavi_*.json` etc. only once Tavi exists.

---

## `presets/` — reusable JSON building blocks

```
presets/
├── characters/
│   └── kiko.json                  # KIKO default params, referenced by scenes
├── cameras/                       # named camera setups (side, 3-4, tracking)
├── lighting/                      # named light rigs (neutral_test, cinematic)
└── render/                        # named render profiles (preview_480, prod_1080)
```

---

## `schemas/` — validation (keeps JSON honest)

```
schemas/
├── scene.schema.json
├── character.schema.json
├── action.schema.json
└── episode.schema.json
```

The engine's `validator.py` checks every scene/preset against these and **fails
loudly** on a missing/invalid field — no silent wrong renders.

---

## `stories/` — episode scripts (multi-shot)

```
stories/
├── runaway_fruit.json
└── episode_002.json
```

---

## `output/` vs `projects/.../review/`

Keep render deliverables and QA review images distinct:

```
output/
├── tests/
│   └── kiko/                      # preview.mp4 / contact_sheet.jpg / verification.json
├── previews/
└── production/
```

- `output/` = videos and verification JSON (the deliverables + gate evidence).
- `projects/characters/kiko/review/` = still QA sheets for rig/visual inspection.

> One `kiko/` subfolder under `output/tests/`. Add siblings when new characters are real.

---

## `tools/` — standalone helpers

```
tools/
├── inspect_rig.py                 # dump bones / shape keys / actions from a .blend
├── render_turnaround.py           # quick turntable of any character
├── validate_character.py          # run a character's deformation QA
└── migrate_project.py             # one-off structure migrations
```

---

## `archive/` — never auto-deleted

```
archive/
├── rejected/
│   └── rejected_kiko_clay_v001/   # the closed procedural-sculpt experiment
├── old_blends/
├── old_scripts/
└── docs/
```

> Per the master plan: rejected work is **kept**, not deleted, and never reused as a
> production base. Removal only on explicit request.

---

## `tests/` — automated tests

```
tests/
├── engine/
├── animation/
├── characters/
│   └── test_kiko.py               # only KIKO
└── schemas/
```

---

## What changed from the original proposal, and why

1. **Collapsed 5 characters to 1 (KIKO) everywhere.** Tavi/Luma/Boko/Zuri folders
   were empty scaffolding for characters that don't exist. The repeatable *pattern*
   is documented instead, so adding one later is a `cp -r`. Empty folders rot.

2. **Crisp `assets/` ↔ `projects/` boundary.** Inputs you bring in vs. files Blender
   generates. The original split reference images and blends by character but blurred
   which tree owned what.

3. **Wired in the master plan + status file + rejected archive.** These are central
   to how the project actually runs but had no home in the original tree.

4. **`environments/` starts minimal** (`generic` + the `jungle` you already use)
   rather than four pre-built biomes.

5. **Separated deliverables (`output/`) from QA review sheets
   (`projects/.../review/`)** so render outputs and inspection images don't mix.

6. **Added a one-line "when it becomes real" rule** at each multiplied point, so the
   growth path is obvious without pre-building it.
