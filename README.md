# Frisbee TrueSkill

The whole app is one file, `index.html`, with no build step. Data is saved in `localStorage`, and Settings → Data can export or import a JSON backup.

## Use it on an iPhone
1. Host `index.html` on any HTTPS static host, such as GitHub Pages or Netlify Drop. "Add to Home Screen" needs a real URL; it won't work on a `file://` page.
2. Open the URL in Safari, tap Share, then **Add to Home Screen**.
3. The Home Screen app and Safari keep **separate** storage. Use Export/Import to move data between them.

## Tests
```bash
python -m http.server 8765
```
Then open http://localhost:8765/tests/tests.html. The test page loads the engine straight out of `index.html`, so there is only one copy of the code.

To regenerate the reference values (needs `pip install trueskill`):
```bash
python tests/make_reference.py
```

## Code layout (for a future Swift port)
- `<script id="rating-engine">` holds pure functions only, with no DOM or storage access (a test enforces this). The main functions:
  - `rateTeams(teams, ranks, env)` is a port of the multi-team TrueSkill factor graph from Python `trueskill` 0.4.5.
  - `computeMarginFactor`, `effectiveWeight` and `applyWeightedUpdate` are the weighting rules.
  - `rateGame(input)` rates one game, and `replayHistory(data)` rebuilds every rating from all saved games.
- `<script id="app">` holds storage, routing and the views.

## Data format (schema v1)
```json
{ "app": "frisbee-trueskill", "version": 1,
  "settings": { "mu", "sigma", "beta", "tau", "drawProbability", "minMargin", "maxMargin",
                "maxWeight", "sigmaFloor", "provisionalGames" },
  "gameTypes": [{ "id", "name", "weight", "target" }],
  "players":   [{ "id", "name", "active", "createdAt" }],
  "games":     [{ "id", "date": "YYYY-MM-DD", "createdAt", "typeId", "scoringTarget",
                  "teams": [{ "playerIds": [], "score" }], "notes" }],
  "prefs": { "lastTeams", "lastTypeId", "showInactive", "draft", "demo" } }
```
Games are replayed in order of `date`, then `createdAt` (ms), then `id`. Ratings are never stored.
