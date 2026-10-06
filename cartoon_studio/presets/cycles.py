CYCLE_FALLBACKS: dict[str, tuple[str, ...]] = {
    "run": ("run", "walk", "idle"), "walk": ("walk", "walk_in_place", "idle"),
    "walk_in_place": ("walk_in_place", "walk", "idle"), "subtle_breathing": ("idle",),
    "fall": ("fall", "idle"), "take": ("take", "idle"),
}
LOOPING_ACTIONS = frozenset({"idle", "subtle_breathing", "walk_in_place", "walk", "run"})
CYCLE_FPS = {"idle": 4.0, "subtle_breathing": 4.0, "walk_in_place": 10.0, "walk": 10.0, "run": 16.0, "fall": 10.0, "take": 10.0}
