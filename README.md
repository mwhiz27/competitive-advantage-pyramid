# Competitive Advantage Pyramid — Stated vs Revealed

A single self-contained HTML page that renders a stated-vs-revealed competitive advantage
analysis for one company: two pyramids side by side, a gap analysis, the method, the track
analysis, and a full citation table. No server, no login, no network calls — `dist/index.html`
is one file you can double-click, email, or upload anywhere.

## Files

| File | What it is |
| --- | --- |
| `evidence.json` | **All your content.** This is the only file you normally edit. |
| `template.html` | The page: layout, styling, validation, interactions. Contains the placeholder `__EVIDENCE_JSON__`. |
| `build.py` | Inlines `evidence.json` into `template.html`, validates the data, and checks the output for external URLs. |
| `dist/index.html` | **The deliverable.** Generated — never edit it by hand, your changes get overwritten on the next build. |

## Editing and rebuilding

1. Open `evidence.json` and replace the sample content (everything is prefixed `SAMPLE:` so
   you can see what goes where).
2. Rebuild:

   ```bash
   cd ~/Claude/competitive-advantage-pyramid
   python3 build.py
   ```

3. Open `dist/index.html` in a browser. From WSL:

   ```bash
   explorer.exe "$(wslpath -w dist/index.html)"
   ```

The build prints the same data checks the page shows, then a self-containment check, then the
output size. Exit code is `0` when there are no errors, `1` when there are — but `dist/index.html`
is written either way so you can always look at the result. Use `python3 build.py --strict` to
also fail on warnings.

Other options: `--data FILE`, `--template FILE`, `--out FILE`.

## The data schema

```jsonc
{
  "company": { "name": "", "ticker": "", "track": "large-public | small-private | startup", "analysisDate": "" },
  "method":  { "summary": "", "inclusionRules": [""], "timeWindow": "", "limitations": [""] },
  "elements": [
    {
      "id": "R-B1",                       // your own label; referenced by gaps
      "pyramid": "stated | revealed",
      "layer": "base | middle | top",     // base = values & priorities, middle = resources
                                          // & capabilities, top = activities
      "claim": "short statement shown on the pyramid tile",
      "detail": "1-3 sentences, shown in the detail panel",
      "rcType": "resource | capability | null",   // required on middle, null elsewhere
      "evidence": [
        { "document": "2025 DEF 14A", "section": "CD&A – Annual Incentive Plan",
          "page": "47", "excerpt": "short supporting quote", "url": "", "accessed": "YYYY-MM-DD" }
      ],
      "metric": "optional quantified fact"
    }
  ],
  "gaps": [
    { "id": "G1", "title": "", "statedIds": ["S-B1"], "revealedIds": ["R-B1"],
      "whatDiffers": "", "strategicMeaning": "",
      "classification": "deliberate positioning | misalignment | unclear",
      "classificationReasoning": "" }
  ],
  "trackAnalysis": ""
}
```

Notes on filling it in:

- **IDs are yours to choose**, but the convention in the sample (`S-` / `R-` for the pyramid,
  `B` / `M` / `T` for the layer) makes gap cards and the citation table much easier to read.
- **Order matters**: elements appear on their tier in the order they appear in the file.
- **`url` and `metric` may be empty strings.** `document`, `section` and `page` may not.
- **`page`** is a string, so `"47"`, `"F-7"` and `"11–12"` all work.
- Blank lines in `trackAnalysis` become paragraph breaks on the page.

## Data checks

The page shows a "Data checks" panel on load and `build.py` prints the same results. The two
implementations are deliberate mirrors — if you change a rule in `build.py`, change it in the
`validate()` function inside `template.html` too.

**Errors** (these are what the grading penalises):

- a `revealed` element with no evidence entries
- any evidence entry missing `document`, `section` or `page`
- a `middle`-layer element whose `rcType` is not `resource` or `capability`
- a gap referencing an element ID that does not exist
- duplicate element IDs, an empty `claim`, or an invalid `pyramid`, `layer` or `classification`

**Warnings:**

- a `base` or `top` element that has an `rcType` set
- fewer than 2 gaps
- a `stated` element with no evidence
- an evidence entry with no `excerpt` or no `accessed` date
- a gap whose `statedIds` lists a revealed element (or vice versa), or with no reasoning
- any field still starting with `SAMPLE:` — grouped one line per element so the panel stays short

With the sample data you should see **0 errors and 18 warnings**, all of them the `SAMPLE:`
placeholder notices. They disappear as you replace the content. When the list is longer than
8 items the panel collapses to the first 6 with a "Show all" button; printing always expands it.

## Printing to PDF

- **Print view** — toggles the print layout on screen so you can check it before printing.
  Press `Esc` to leave it.
- **Print / Save PDF** — opens the browser print dialog. Choose "Save as PDF".

The printed document is ordered: header + data checks + both pyramids side by side (page 1),
then every element with all citations expanded (no clicking needed), then the gap cards, then
method, track analysis, and the full citation table. Print colours are forced to a light palette,
so a dark-mode browser still produces a clean PDF, and link URLs are printed after their text.

In Chrome's print dialog, leave "Background graphics" **on** — that is what draws the pyramid
tiers.

## Using the page

- Click any element tile for its detail, metric, and full citations. Click again to deselect.
- Hover or tab to a gap card to highlight the elements it links, in both pyramids at once.
- `◆ G1` on a tile means the element appears in gap G1.
- `R` / `C` badges on middle-layer tiles mark resources and capabilities.
- Click any column heading in the citation table to sort by it; click again to reverse.
- The page follows your system light/dark setting and stacks the pyramids on narrow screens.

## Publishing

`dist/index.html` is completely self-contained: no external scripts, stylesheets, fonts or
images, and no `localStorage`. Upload that one file anywhere that serves static pages
(GitHub Pages, Netlify drop, a course LMS) and it will work with no login and no backend.
`build.py` verifies this on every build and fails the build if any `script`, `link`, `img`
or similar tag ever points off-box.
