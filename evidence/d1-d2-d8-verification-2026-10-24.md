# D1, D2 and D8 independent verification — 2026-10-24

Candidate examined: `origin/codex/ademix` at `17e476b`.

## D1 — independent calculations: PASS

The verification recomputes the core values without using the engine projection
helper, then compares the results with the engine:

- one-way travel: `3.2 km / 25 km/h × 60 = 7.68 min`;
- no-queue cycle: `6 + 7.68 + 1 + 7.68 = 22.36 min`;
- loading capacity: `77 t × 60 / 6 = 770 t/h`;
- dump-bay capacity: `77 t × 60 / 1 = 4,620 t/h`;
- baseline requirement: `ceil(770 × 22.36 / (77 × 60)) = 4 trucks`.

Completed engine cycles also reconcile to recorded waiting plus the independently
calculated loading, two travel legs and dumping durations. This distinguishes the
22.36-minute free cycle from the longer queue-inclusive observed cycle.

Command:

```text
python -m unittest discover -s ademix/simulator -p "test_independent_verification.py" -v
```

## D2 — long-run repeated-shift stability: PASS

One deterministic engine ran eight eight-hour shifts, alternating baseline,
breakdown, road restriction and crusher slowdown with fixed/smart policy changes.
Every shift was followed by fixed/baseline reset and one recovery hour: 72
simulated hours total.

The check requires zero mass-balance error, non-negative bounded ROM inventory,
monotonic production, unique queues, at most one truck in each exclusive
resource, valid payloads, no stale breakdown/blockage after reset, and bounded
event/history structures. All requirements passed.

## D8 — complete asset dependency check: FAIL; visual-owner action required

PASS:

- all source-level runtime model/texture references are repository-local;
- referenced paths exist with exact case;
- seven GLBs and three dirt textures are non-empty;
- the three dirt textures are referenced by `GroundMaterial.ts` and recorded in
  `DATA_LICENSES.md`;
- no runtime model/texture URL points to an external CDN.

FAIL:

Five Kenney plant GLBs contain the relative image dependency
`Textures/colormap.png`, but `ademix/frontend/public/models/Textures/colormap.png`
is absent:

- `plant-hopper.glb`;
- `plant-crusher.glb`;
- `plant-conveyor.glb`;
- `plant-conveyor-slope.glb`;
- `plant-stairs.glb`.

The missing file exists in the already-pinned CC0 source at
`shorepine/kenney`, commit `3694c6879e487c108f55677be7dd2ca75b07cc3b`, path
`3d/factory/Textures/colormap.png` (11.5 KB). Professor + Claude own the
frontend asset path, so this verification branch does not silently add or alter
their visual assets. After they add the exact file and record its SHA-256 in
`DATA_LICENSES.md`, rerun:

```text
python -m unittest discover -s ademix/data -p "verify_asset_dependencies.py" -v
```

Do not mark D8 complete until all three checks pass and the browser console/network
review shows no asset-loading error on the final combined candidate.
