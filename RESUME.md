# Resume

- Branch: `autorun`
- Next actionable task: `P7 full pipeline acceptance`
- Continue command: `git checkout autorun && python3 -m pytest -q`
- Continue command: `git checkout autorun && python3 -m pytest -q tests/test_determinism.py && python3 -m cartoon_studio.cli validate projects/kiko_2d_test.json`
- Continue command: `git checkout autorun && python3 -m pytest -q tests/test_render_smoke.py tests/test_audio_integration.py`
- Continue command: `git checkout autorun && python3 -m pytest -q tests/test_project_schema.py tests/test_audio_integration.py`
- Safety: never overwrite any `.blend`; create a `*_backup.blend` copy before any Blender-file mutation.
