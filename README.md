# Translation Affiliation Map

Interactive affiliation map for the
[Last Translation Benchmark](https://last-translation-benchmark.vilda.net/).
It is a standalone static website that can be hosted on GitHub Pages and
embedded in another page.

The map combines:

- accepted-submission and contributor totals from the public dashboard API;
- affiliation coordinates, aliases, and logo domains from
  `data/affiliation_locations.json`;
- automatic ROR lookup for newly observed affiliations.

It does not need the benchmark database, FastAPI, `uvicorn`, or a persistent
server.

## Project structure

```text
src/                                  Map UI, styles, and TypeScript types
data/affiliation_locations.json       Affiliation aliases and coordinates
scripts/affiliation_map.py            Combines dashboard rows with locations
scripts/build_static_dashboard.py     Creates the static data snapshot
scripts/update_affiliation_locations.py
                                      Discovers new affiliations through ROR
scripts/cache_affiliation_logos.py    Locks automatic logos into local assets
.github/workflows/                    Scheduled update and Pages deployment
```

## Run locally

Requirements: Node.js 24+ and Python 3.12+.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm install
.venv/bin/python scripts/cache_affiliation_logos.py
CARTO_BASEMAP_KEY=your-carto-key npm run build
.venv/bin/python scripts/build_static_dashboard.py
python3 -m http.server 8080 --directory site
```

Open [http://localhost:8080](http://localhost:8080).

The generated `site/` directory is ignored by Git. The build workflow recreates
it for each deployment.

## Data updates

Preview new unambiguous ROR matches:

```bash
.venv/bin/python scripts/update_affiliation_locations.py
```

Write the matches to the static location registry:

```bash
.venv/bin/python scripts/update_affiliation_locations.py --write
```

The updater tries the complete affiliation value first. For combined values,
such as `PSL University, INRIA Paris`, it then tries each comma- or
semicolon-separated name. Only a unique exact match against a ROR display name,
alias, or acronym is stored automatically. Unresolved affiliations remain
visible under **Other affiliations**.

Cache every currently configured automatic logo:

```bash
.venv/bin/python scripts/cache_affiliation_logos.py
```

Each downloaded image is stored under `src/assets/logos/cache/` and recorded in
its manifest. Later runs reuse that file, so a website or favicon change cannot
silently replace the map icon. Existing `logo_files` entries remain higher
priority and are never overwritten. To intentionally replace one automatic
cached icon, run:

```bash
.venv/bin/python scripts/cache_affiliation_logos.py \
  --affiliation "University of Würzburg" \
  --refresh
```

The `Update affiliation locations` workflow also caches icons for newly added
domains and commits both the locations and local logo assets. After it finishes
successfully, `Deploy affiliation map to GitHub Pages` fetches current dashboard
totals, builds the website, and deploys it.

## Publish on GitHub Pages

1. Add `CARTO_BASEMAP_KEY` under **Settings → Secrets and variables → Actions → Repository secrets**.
2. Push `main` to GitHub.
3. Open **Settings → Pages** in the repository.
4. Under **Build and deployment**, set **Source** to **GitHub Actions**.
5. Run `Deploy affiliation map to GitHub Pages`, or push another commit.

For `lvu5/translation_viz`, the default URL is:

```text
https://lvu5.github.io/translation_viz/
```

The repository must allow GitHub Actions read/write workflow permissions so the
ROR updater can commit location changes. An optional `ROR_CLIENT_ID` repository
secret identifies the updater to ROR.

## Embed

Use `?embed=1` to hide the standalone header:

```html
<iframe
  src="https://lvu5.github.io/translation_viz/?embed=1"
  title="Last Translation Benchmark contributor affiliation map"
  loading="lazy"
  style="width:100%;height:760px;border:0"
></iframe>
```

## License

Source code is licensed under [MIT](LICENSE). Dashboard data remains subject to
the source project's data terms.
