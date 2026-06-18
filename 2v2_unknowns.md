# 2v2 Mode — Unknowns to Verify

## Tower Positions

In 1v1, towers are at fixed positions:
- Command Tower: (-140, ±170)
- Research Tower: (140, ±170)

**Unknown:** In 2v2, does each player on a team have their own pair of towers at different positions,
or do they share the same tower positions? If separate, what are the positions?

Currently the code injects ONE pair of towers per team (same positions as 1v1).
If each player has their own towers, we need 2 pairs per team at different coordinates.

### How to check
Run a 2v2 replay with `units --player <name>` for each of the 4 players and compare
construction positions. If both teammates show the same tower coordinates, they share.
If different — we need per-player tower injection.

## Coordinate Space

**Unknown:** In 2v2, do both teammates share the exact same deployment zone (same Y range),
or does each teammate get a half of their team's side (e.g., left half / right half)?

Currently the code assumes both teammates share the full Y zone on their side.

### How to check
Place units for both teammates across the full X/Y range and check if the game restricts
placement to sub-zones per player.

## Flank Zones

**Unknown:** In 2v2, are flank zones the same as 1v1 (full opponent side available from round 2)?

### How to check
Try placing on flanks in a 2v2 game and check if the rules differ.
