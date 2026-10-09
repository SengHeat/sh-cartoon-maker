# PROJECT_STRUCTURE — Jungle Pop (`cartoon_studio`)

រចនាសម្ព័ន្ធ project សម្រាប់ pipeline ផលិតវីដេអូ 2.5D (+ Blender 3D stage) ដែលផ្ទុក
តួអង្គ **Jungle Pop ទាំង ១៥**។ File នេះគ្រាន់តែជា *map* — វាបង្ហាញថា file មួយណាគួរនៅទីណា។

- **Universe:** Jungle Pop — *Big Adventures. Wild Friends.*
- **Pipeline:** Python + Pillow + FFmpeg (2.5D) · Blender headless (3D stage)
- **Output:** 1920×1080 (16:9) + 1080×1920 (9:16), H.264, Khmer narration + subtitles
- **Source of truth:** `docs/JUNGLE_POP_CHARACTER_HISTORY_KH.md` (Character Bible)

> **Honest gate / ច្រក art:** រចនាសម្ព័ន្ធ + code ទាំងអស់ Codex/Claude Code សាងបាន។
> ប៉ុន្តែ **រូបគំនូរពិត** (character layers, backgrounds) និង **សំឡេង narration ពិត**
> ជាជំហានមនុស្ស/tool — គ្រប់ slot art ចាប់ផ្តើមជា **placeholder** រហូតដល់ដាក់រូបពិតជំនួស។

---

## 1. Top-level tree

```
cartoon_studio/
├── README.md
├── PROJECT_STRUCTURE.md            # file នេះ
├── PRODUCTION.md                   # របៀបសរសេរ story / add character / build
├── TASKS.md  RESUME.md             # autorun loop state (resumable)
├── .gitignore                      # renders/ review/ __pycache__/ .DS_Store
├── requirements.txt
│
├── cartoon_studio/                 # ⟵ Python package (code)
│   ├── engine/
│   │   └── director.py             # choose renderer, drive scenes → frames
│   ├── renderers/
│   │   ├── base_renderer.py        # shared renderer contract
│   │   ├── image_renderer.py       # 2.5D path (default)  ⟵ puppet deform, parallax
│   │   ├── blender_kiko.py         # Blender backend (subprocess → kiko_render.py)
│   │   └── hybrid_renderer.py      # selector: "2.5d" | "blender"
│   ├── models/
│   │   ├── scene.py                # scene schema (renderer field defaults "2.5d")
│   │   └── story.py                # story schema (project → ordered scenes)
│   ├── assets_lib/
│   │   ├── character_package.py    # load/validate a character/ package
│   │   └── registry.py             # read assets/characters/registry.json
│   ├── audio/
│   │   ├── narration.py            # INTEGRATE existing TTS (VoxCPM2 / voice_studio)
│   │   └── mixer.py                # hand tracks to FFmpegEngine
│   ├── subtitles/
│   │   └── khmer_srt.py            # timed Khmer captions + .srt (shaping-safe)
│   ├── compositor/
│   │   └── ffmpeg_engine.py        # ONE ffmpeg route: stitch + mux + burn subs
│   └── cli.py                      # `story.json → final mp4 (+ srt + manifest)`
│
├── assets/
│   ├── characters/                 # ⟵ one package per character (see §2)
│   │   ├── registry.json           # id → path, role, priority, status
│   │   ├── _TEMPLATE/              # copy this to add a new character
│   │   ├── kiko/   tavi/   luma/   boko/   zuri/      # core team (build first)
│   │   ├── vargo/  grib/   momo/   nana/   pip/
│   │   └── mira/   ruko/   fifi/   toto/   jungle_spirit/
│   ├── backgrounds/                # jungle regions, layered for parallax (see §3)
│   │   ├── _TEMPLATE/
│   │   ├── deep_jungle/   waterfall/   ancient_temple/
│   │   ├── caves/         canopy_high/ hidden_path/
│   ├── props/                      # trinkets, compass, gear, floating seeds…
│   ├── audio/
│   │   ├── music/                  # background music beds
│   │   └── sfx/                    # footsteps, rustle, bell…
│   └── fonts/
│       └── NotoSansKhmer-*.ttf     # Khmer-capable font (verify glyph shaping)
│
├── blender/                        # ⟵ 3D stage (recovered assets live here)
│   ├── KIKO_master_v001.blend      # geometry + 100-bone rig + 11 materials
│   ├── kiko_build.py  kiko_geometry.py  kiko_rig.py
│   ├── kiko_materials.py  kiko_costume.py
│   ├── kiko_blockout.py            # standalone blockout (kept runnable)
│   ├── kiko_render.py              # JSON shot → PNG/mp4 + manifest
│   ├── kiko_turntable.py           # silhouette turntable preview
│   └── shots/
│       └── kiko_hero_test.json
│
├── stories/                        # ⟵ production episodes (story.json → video)
│   ├── _schema/story.schema.json
│   ├── templates/                  # one per episode type (see §5)
│   │   ├── comedy.story.json       adventure.story.json  mystery.story.json
│   │   └── emotional.story.json    rival.story.json      villain.story.json
│   └── ep001_<slug>/
│       ├── story.json
│       ├── audio/                  # narration clip per dialogue line (TTS output)
│       └── subtitles/ep001.srt
│
├── projects/                       # test/sample scenes (not full episodes)
│   ├── kiko_2d_test.json
│   └── example_kiko_blender.json
│
├── docs/
│   ├── JUNGLE_POP_CHARACTER_HISTORY_KH.md   # ⟵ the Character Bible (uploaded)
│   ├── KIKO_PRODUCTION_BIBLE.md             # KIKO build spec (export of the doc)
│   ├── character_package_spec.md            # the reusable unit (§2), long form
│   └── visual_style_guide.md                # §6 rules, long form
│
├── tests/
│   ├── test_scene_schema.py   test_story_schema.py
│   ├── test_image_renderer.py test_blender_kiko_backend.py
│   ├── test_audio_timing.py   test_subtitles.py  test_export.py
│
├── renders/                        # OUTPUT — gitignored
└── review/                         # QA stills/clips — gitignored
```

---

## 2. Character package (the reusable unit) — តួម្នាក់ = folder មួយ

គ្រប់តួ (KIKO…JUNGLE SPIRIT) មានទម្រង់ **ដូចគ្នា**។ ដើម្បី add តួថ្មី → copy `_TEMPLATE/`។

```
assets/characters/<id>/
├── character.json      # meta: id, name, role, type, color_identity, priority, status
├── rig.json            # parts[]: {art, parent, pivot[x,y], z, states{…}}
├── layers/             # ⟵ one transparent PNG per body part (placeholder or REAL art)
│   ├── tail_01.png … head.png … ear_l.png … (per the character)
├── states/             # swap art for expressions / lip-sync visemes
│   ├── eyes_open.png  eyes_closed.png
│   └── mouth_closed.png  mouth_mid.png  mouth_open.png
├── thumbnail.png
└── README.md           # EXACT png paths real art replaces + pivot meaning
```

- `status`: `placeholder` → `wip` → `production` (honest; never fake `production`).
- **Swap-in rule:** replacing a PNG at its documented path changes the render with **zero code change**. នេះជាកន្លែងដែលរូបពិតចូល។
- KIKO's existing 2.5D package is the reference; `assets_lib/character_package.py` validates every package against this shape.

---

## 3. Backgrounds & parallax — ព្រៃ Jungle Pop

ព្រៃគឺជា "តួអង្គ" មួយ (តាម bible)។ Background នីមួយៗ = layer ច្រើន មាន **depth tag** សម្រាប់ parallax (plane ក្រោយ រំកិលយឺតជាង plane មុខ = នេះជា "2.5D")។

```
assets/backgrounds/<region>/
├── background.json     # layers[]: {art, depth}  (depth 0=far … 1=near)
├── layers/ sky.png  far_trees.png  mid_trees.png  foreground.png
└── README.md
```

តំបន់ចាប់ផ្តើម (តាម bible): `deep_jungle`, `waterfall`, `ancient_temple`, `caves`, `canopy_high`, `hidden_path`.

---

## 4. Characters in this universe — ១៥ តួ

| # | id | តួនាទី | ប្រភេទ | Priority | Status |
|---|----|--------|--------|:---:|---|
| 1 | `kiko` | តួឯក / អ្នករុករក | fennec-cat × gremlin | 1 | 3D master built; 2.5D wip |
| 2 | `luma` | អ្នកស្ទង់ពីលើ | fantasy bird | 2 | placeholder |
| 3 | `tavi` | ខួរក្បាល / អ្នករៀបផែនការ | jungle creature | 3 | placeholder |
| 4 | `boko` | កម្លាំង / កំប្លែង | bear × ape | 4 | placeholder |
| 5 | `zuri` | Rival / ល្បឿន | feline adventurer | 5 | placeholder |
| 6 | `vargo` | Villain សំខាន់ | dark jaguar | 6 | placeholder |
| 7 | `grib` | អ្នកជួយ villain | mischief creature | 7 | placeholder |
| 8 | `momo` | Mischief | — | 8 | placeholder |
| 9 | `nana` | អ្នកចាស់មានប្រាជ្ញា | — | 9 | placeholder |
| 10 | `pip` | អ្នកច្នៃប្រឌិត | — | 10 | placeholder |
| 11 | `mira` | អ្នកជំនាញធម្មជាតិ / ព្យាបាល | — | 11 | placeholder |
| 12 | `ruko` | អ្នកយាមព្រៃ | — | 12 | placeholder |
| 13 | `fifi` | មិត្តតូច / អារម្មណ៍ | small creature | 13 | placeholder |
| 14 | `toto` | មិត្តឆ្គង / comedy | — | 14 | placeholder |
| 15 | `jungle_spirit` | អាថ៌កំបាំង / lore | plant × animal hybrid | 15 | placeholder |

> **Core team (build reusable production-ready មុនគេ):** KIKO · LUMA · TAVI · BOKO · ZURI.
> កុំ build តួទាំង ១៥ production quality ភ្លាមៗ (តាម bible)។

---

## 5. Episodes & story types

Entry point តែមួយ: `stories/epNNN_<slug>/story.json` → `cli.py` → final mp4 + .srt + manifest.
Template ក្នុង `stories/templates/` ត្រូវនឹង episode types ក្នុង bible:

- **comedy** → KIKO, BOKO, MOMO, GRIB, TOTO, PIP
- **adventure** → KIKO, TAVI, LUMA, ZURI, BOKO
- **mystery** → KIKO, TAVI, NANA, JUNGLE_SPIRIT, VARGO
- **emotional** → KIKO, FIFI, TAVI, BOKO, MIRA
- **rival** → KIKO, ZURI, LUMA
- **villain** → VARGO, GRIB, KIKO, TAVI, ZURI

> កុំបង្ខំឲ្យតួទាំង ១៥ ចូលគ្រប់ episode។

---

## 6. Visual consistency rules (gate before any art is "production")

តួ Jungle Pop ទាំងអស់ត្រូវនៅ universe តែមួយ:

- polished stylized 3D · ភ្នែកធំ expressive · **silhouette ស្គាល់បានដោយមិនពឹងពណ៌**
- materials ទន់ organic · រោម/feathers/skin ជឿបានតាមប្រភេទ · accessories បែប handmade
- តួម្នាក់ៗមាន **color identity** ខ្លាំង
- ❌ smooth plastic · ❌ generic low-poly · ❌ photoreal
- គុណភាព cinematic family animation

(Full version: `docs/visual_style_guide.md`.)

---

## 7. How to add a new character — checklist

1. `cp -r assets/characters/_TEMPLATE assets/characters/<id>`
2. បំពេញ `character.json` តាម bible: តួនាទី · បុគ្គលិកលក្ខណៈ · អត្តសញ្ញាណរូបរាង · ប្រវត្តិ · ចំណុចខ្លាំង/ខ្សោយ · style កំប្លែង · ទំនាក់ទំនង · មុខងារសាច់រឿង · priority
3. បង្កើត placeholder `layers/` + `rig.json` (pivots, z-order) — ឬ Codex generate
4. បន្ថែមទៅ `assets/characters/registry.json`
5. Smoke-test ក្នុង `projects/` scene មួយ
6. ពេលក្រោយ: ដាក់រូបពិតជំនួស placeholder PNG តាម `README.md`

---

## 8. Git safety (សំខាន់ — កុំឲ្យបាត់ម្តងទៀត)

```
git init
printf "renders/\nreview/\n__pycache__/\n*.pyc\n.DS_Store\n" > .gitignore
git add -A && git commit -m "jungle pop: project structure"
# commit រៀងរាល់ session; git stash មុនពេលសម្អាត/delete
```
```
```