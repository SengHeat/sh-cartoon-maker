cartoon-maker/
│
├── README.md
├── TASKS.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── cartoon_engine.py
│
├── cartoon_studio/
│   ├── __init__.py
│   │
│   ├── engine/
│   │   ├── runner.py
│   │   ├── loader.py
│   │   ├── validator.py
│   │   ├── context.py
│   │   └── registry.py
│   │
│   ├── animation/
│   │   ├── locomotion.py
│   │   ├── walk.py
│   │   ├── run.py
│   │   ├── jump.py
│   │   ├── gestures.py
│   │   ├── face.py
│   │   ├── ears.py
│   │   ├── tail.py
│   │   └── flight.py
│   │
│   ├── characters/
│   │   ├── base.py
│   │   ├── registry.py
│   │   │
│   │   ├── kiko/
│   │   │   ├── rig.py
│   │   │   ├── controls.py
│   │   │   ├── expressions.py
│   │   │   ├── visemes.py
│   │   │   ├── presets.py
│   │   │   └── validator.py
│   │   │
│   │   ├── tavi/
│   │   │   ├── rig.py
│   │   │   ├── controls.py
│   │   │   ├── expressions.py
│   │   │   ├── visemes.py
│   │   │   ├── presets.py
│   │   │   └── validator.py
│   │   │
│   │   ├── luma/
│   │   │   ├── rig.py
│   │   │   ├── controls.py
│   │   │   ├── expressions.py
│   │   │   ├── flight.py
│   │   │   ├── presets.py
│   │   │   └── validator.py
│   │   │
│   │   ├── boko/
│   │   │   ├── rig.py
│   │   │   ├── controls.py
│   │   │   ├── expressions.py
│   │   │   ├── presets.py
│   │   │   └── validator.py
│   │   │
│   │   └── zuri/
│   │       ├── rig.py
│   │       ├── controls.py
│   │       ├── expressions.py
│   │       ├── visemes.py
│   │       ├── presets.py
│   │       └── validator.py
│   │
│   ├── blender/
│   │   ├── scene.py
│   │   ├── camera.py
│   │   ├── lighting.py
│   │   ├── materials.py
│   │   ├── rigging.py
│   │   ├── render.py
│   │   └── io.py
│   │
│   ├── environments/
│   │   ├── jungle.py
│   │   ├── forest.py
│   │   ├── village.py
│   │   └── generic.py
│   │
│   ├── props/
│   ├── renderers/
│   ├── audio/
│   ├── lipsync/
│   └── utils/
│
├── assets/
│   ├── characters/
│   │   ├── kiko/
│   │   │   ├── reference/
│   │   │   │   └── kiko.png
│   │   │   ├── textures/
│   │   │   ├── materials/
│   │   │   ├── models/
│   │   │   └── external/
│   │   │
│   │   ├── tavi/
│   │   │   ├── reference/
│   │   │   ├── textures/
│   │   │   ├── materials/
│   │   │   ├── models/
│   │   │   └── external/
│   │   │
│   │   ├── luma/
│   │   │   ├── reference/
│   │   │   ├── textures/
│   │   │   ├── materials/
│   │   │   ├── models/
│   │   │   └── external/
│   │   │
│   │   ├── boko/
│   │   │   ├── reference/
│   │   │   ├── textures/
│   │   │   ├── materials/
│   │   │   ├── models/
│   │   │   └── external/
│   │   │
│   │   └── zuri/
│   │       ├── reference/
│   │       ├── textures/
│   │       ├── materials/
│   │       ├── models/
│   │       └── external/
│   │
│   ├── environments/
│   ├── props/
│   ├── audio/
│   ├── sfx/
│   └── music/
│
├── projects/
│   ├── characters/
│   │   ├── kiko/
│   │   │   ├── blends/
│   │   │   │   ├── master/
│   │   │   │   │   ├── KIKO_master_v1_1.blend
│   │   │   │   │   └── KIKO_master_v2.blend
│   │   │   │   ├── tests/
│   │   │   │   └── backups/
│   │   │   ├── reports/
│   │   │   └── review/
│   │   │
│   │   ├── tavi/
│   │   │   ├── blends/
│   │   │   │   ├── master/
│   │   │   │   ├── tests/
│   │   │   │   └── backups/
│   │   │   ├── reports/
│   │   │   └── review/
│   │   │
│   │   ├── luma/
│   │   │   ├── blends/
│   │   │   │   ├── master/
│   │   │   │   ├── tests/
│   │   │   │   └── backups/
│   │   │   ├── reports/
│   │   │   └── review/
│   │   │
│   │   ├── boko/
│   │   │   ├── blends/
│   │   │   │   ├── master/
│   │   │   │   ├── tests/
│   │   │   │   └── backups/
│   │   │   ├── reports/
│   │   │   └── review/
│   │   │
│   │   └── zuri/
│   │       ├── blends/
│   │       │   ├── master/
│   │       │   ├── tests/
│   │       │   └── backups/
│   │       ├── reports/
│   │       └── review/
│   │
│   └── episodes/
│       ├── runaway_fruit/
│       │   ├── scene.blend
│       │   ├── story.json
│       │   ├── shots/
│       │   └── reports/
│       │
│       └── episode_002/
│
├── scenes/
│   ├── tests/
│   │   ├── kiko_run_5s.json
│   │   ├── kiko_acting_8s.json
│   │   ├── tavi_walk_5s.json
│   │   ├── luma_flight_5s.json
│   │   ├── boko_walk_5s.json
│   │   └── zuri_run_5s.json
│   │
│   └── episodes/
│       ├── runaway_fruit.json
│       └── episode_002.json
│
├── schemas/
│   ├── scene.schema.json
│   ├── character.schema.json
│   ├── action.schema.json
│   └── episode.schema.json
│
├── stories/
│   ├── runaway_fruit.json
│   └── episode_002.json
│
├── presets/
│   ├── characters/
│   │   ├── kiko.json
│   │   ├── tavi.json
│   │   ├── luma.json
│   │   ├── boko.json
│   │   └── zuri.json
│   │
│   ├── cameras/
│   ├── lighting/
│   └── render/
│
├── output/
│   ├── tests/
│   │   ├── kiko/
│   │   ├── tavi/
│   │   ├── luma/
│   │   ├── boko/
│   │   └── zuri/
│   │
│   ├── previews/
│   └── production/
│
├── review/
│   ├── characters/
│   │   ├── kiko/
│   │   ├── tavi/
│   │   ├── luma/
│   │   ├── boko/
│   │   └── zuri/
│   └── episodes/
│
├── tools/
│   ├── inspect_rig.py
│   ├── render_turnaround.py
│   ├── validate_character.py
│   └── migrate_project.py
│
├── archive/
│   ├── rejected/
│   ├── old_blends/
│   ├── old_scripts/
│   └── experiments/
│
├── docs/
│   ├── PROJECT_STRUCTURE.md
│   ├── CHARACTER_PIPELINE.md
│   ├── ANIMATION_ENGINE.md
│   └── PRODUCTION_PIPELINE.md
│
└── tests/
├── engine/
├── animation/
├── characters/
│   ├── test_kiko.py
│   ├── test_tavi.py
│   ├── test_luma.py
│   ├── test_boko.py
│   └── test_zuri.py
└── schemas/