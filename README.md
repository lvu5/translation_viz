# <img src="web/src/assets/favicon.svg" height=30> Last Translation Benchmark

This platform gathers inputs (text, video, audio, images, documents) that are challenging for modern machine translation systems.
Contributors submit these inputs alongside machine translation outputs and a verification rule.
With 10 approved submissions, contributors are eligible for inclusion in the upcoming research publication.

There are three user roles:
- **Contributor** suggests inputs (text, images, and speech), auto-translate them, defines a verification method, and submits.
- **Reviewer** browses pending submissions and returns, accepts, or comments.
- **Admin** with the ability to create and modify users.
Each account is associated with a magic link that can be used to login from anywhere.

If you're interested in contributing, register at [last-translation-benchmark.vilda.net](https://last-translation-benchmark.vilda.net).
Make sure you read the instructions beforehand.

> Example from English to Czech translation: \
> **Source**: "_what's the difference between jail and prison?_" \
> **Translation (Google Translate)**: "_jaký je rozdíl mezi vězením a vězením?_" \
> **Translation (Human)**: "_jaký je rozdíl mezi vazební věznicí a vězením?_" \
> **Verification rule**: "_The words for the "jail" and "prison" shouldn't be identical."_

<img width="1000" alt="Last Translation Benchmark poster" src="https://github.com/user-attachments/assets/f0971f5c-fc95-4d48-9f13-a01934b4913d" />

## Development

```bash
# requires python >=3.12, node >= 20
npm install --prefix web
npm run build --prefix web/
# use this one when developing
pip install -e ".[dev]" && pre-commit install -c .github/.pre-commit-config.yaml
# use this one when not developing
pip install -e .
# prints login URLs
python3 server
```

The `server/` contains source code for the server.
The `web/` is the frontend code (TypeScript) which, when built, goes to `server/static/` to be served by the server.
The public dashboard map combines live accepted-submission data with the reviewed locations in `server/affiliation_locations.json`.

### Standalone affiliation map

The map can be hosted independently on GitHub Pages and embedded in the main
website. GitHub Pages serves static files, so the hosted map does not run
FastAPI, `uvicorn`, or a database. A GitHub Actions build fetches the live
read-only public dashboard, combines it with the location registry, and writes a
same-origin snapshot for the browser.

Build and preview the Pages site locally:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install "httpx>=0.27"
npm install --prefix web
npm run build:pages --prefix web
.venv/bin/python scripts/build_static_dashboard.py
python3 -m http.server 8080 --directory site
```

Open [http://localhost:8080](http://localhost:8080). The generated `site/`
directory is intentionally ignored by Git; GitHub Actions rebuilds it for every
deployment.

To publish:

1. Push `main` to GitHub.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.
4. Open the `Deploy affiliation map to GitHub Pages` workflow to follow the
   first deployment.

For `lvu5/translation_viz`, the default Pages URL is:

```text
https://lvu5.github.io/translation_viz/
```

The project lead can embed the map-only layout with:

```html
<iframe
  src="https://lvu5.github.io/translation_viz/?embed=1"
  title="Last Translation Benchmark contributor affiliation map"
  loading="lazy"
  style="width:100%;height:760px;border:0"
></iframe>
```

The Pages workflow runs after the six-hour affiliation update, so
accepted-submission totals and contributors refresh without database access. A
normal push to `main` deploys immediately as well.

### Affiliation map maintenance

The website does not call ROR, geocode affiliations, or write location records
while serving users. Signup and admin workflows are unchanged. Map points,
aliases, and logo domains come only from
`server/affiliation_locations.json`, which can be reviewed like any other code
change.

An optional maintenance command compares the current public dashboard with the
static registry and queries [ROR](https://ror.org/) for affiliations that are
not yet listed:

```bash
# Preview unambiguous ROR matches without changing files
python3 scripts/update_affiliation_locations.py

# Write reviewed matches to the static JSON file
python3 scripts/update_affiliation_locations.py --write
```

Only a unique exact match against a ROR display name, alias, or acronym is
written automatically. For combined values such as `PSL University, INRIA
Paris`, the script also searches each comma- or semicolon-separated name in
order and uses the first unique match. The script uses ROR's city coordinates.
Anything it cannot resolve remains visible automatically under **Other
affiliations**, so no manual JSON entry is required. Set `ROR_CLIENT_ID` in the
environment, or pass `--client-id`, if the deployment has one. This maintenance
command does not need database access and is not part of the live request path.

The `Update affiliation locations` workflow runs this command every six hours
and can also be started manually from the repository's **Actions** page. When
ROR produces new matches, it commits the registry update to the default branch.
After the updater completes successfully, the Pages workflow creates a fresh
data snapshot and deploys it. Unresolved names continue to appear under **Other
affiliations**. The repository must give GitHub Actions read/write workflow
permissions, and its branch protection rules must allow this workflow to push.
An optional `ROR_CLIENT_ID` repository secret identifies the updater to ROR.

You can specify the `--host`, `--port` and `--host-public` arguments when starting the server. 
The last is used to show the login URLs.

### Environment variables

Create `config.toml` based on `config.template.toml`
- `CONTRIBUTOR_QUOTA_DEFAULT` default "credits" for new users
- `DB_PATH` path to the persistent database file (will be created automatically)
- `EMAIL_*` configuration of email sending

Some API services need API keys:
- `OPENROUTER_API_KEY`: enables real LLM translation and verification
- `LARA_API_ID` and `LARA_API_SECRET`: enables Lara API-based translation
- `GOOGLE_TRANSLATE_API_KEY`: enables API-based Google Translate


### Instructions

The instructions in [web/src/assets/instructions.html](web/src/assets/instructions.html) are based on upstream document written in Typst and should not be edited locally in this repo.

## License

The source code in this repository is licensed under [MIT](LICENSE), and the data under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.en).

## Contributing

We welcome bugreports, hands-on, and research contributions.
AI-generated PRs are fine as long as you verify everything and take ownership of the changes.
This effort is organized by a collective of researchers from ETH Zurich, JHU, CUNI, UvA, KIT, and many others.
Reach out to [last-translation-benchmark@vilda.net](mailto:last-translation-benchmark@vilda.net) with inquiries.

## Citation

The Last Translation Benchmark is still in preparation.
If you need to cite this project, please use this temporary BibTeX:
```bibtex
@misc{last-translation-benchmark,
title={Last Translation Benchmark},
author={Vilém Zouhar and Niyati Bafna and Maike Züfle and Patrícia Schmidtová and Bhavitvya Malik and Sara Rajaee and Leshem Choshen and Gabriele Sarti and Marek Šuppa and Orfeas Menis and Jingwei Ni and Yu Fan and Jan Niehues and Mukund Choudhary and Michelle Wastl and Pinzhen Chen and Alon Lavie and Ondřej Bojar and Sara Papi and Fabian Retkowski and Orfeas Menis Mastromichalakis and Javier García Gilabert and Eliya Habba and Maria Lymperaiou and Dominik Macháček and Sophia Conrad and Sergey Troshin and Jannis Vamvas and Marco Gaido and Sankalan Pal Chowdhury and Malik Marmonier and Koel Dutta Chowdhury and Samuel Simko and Rachel Bawden and Peng Cui and Lukas Edman and Jirui Qi and David Stap and Blanka Kövér and Benoît Sagot and Ruta Binkyte and Ondrej Klejch and Ona de Gibert and Isabelle Caroline Rose Cretton and Bastian Bunzeck and Seth Aycock and Juri Opitz and Evgeniia Tokarchuk and Wafa Aissa and Shaomu Tan and Pavel Stepachev and Nathaniel Berger and Mateusz Lango and Heejin Do and Hanna Yukhymenko and Beni Egressy and Avijit Thawani},
year={2026},
url={https://last-translation-benchmark.vilda.net/},
note={In preparation},
}
```
