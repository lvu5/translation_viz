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

To test the integrated dashboard against the live website's read-only public data,
start the local server with:

```bash
python3 server --public-dashboard-source "https://last-translation-benchmark.vilda.net/api/public-dashboard"
```

Only `/api/public-dashboard` uses the remote data in this mode. Other pages and
write operations continue to use the local database.

### Affiliation location workflow

Contributors choose their affiliation from the ROR search in their profile. When
an accepted, publicly credited contributor has a ROR affiliation that is not in
the reviewed location registry, the server automatically:

1. reads the organization's canonical name, website, domain and city coordinates
   from ROR;
2. asks OpenStreetMap Nominatim for a more precise address candidate;
3. saves the candidate in the main SQLite database as `pending`; and
4. displays it immediately on the public map with a provisional `≈` badge.

The profile also offers **Independent researcher** and **Other / not listed in
ROR**. Independent profiles are deliberately excluded from institution mapping.
Other affiliations retain the entered name but have no automatic map location
until they are matched or reviewed manually.

Contributors can add up to five affiliations. The first remains the primary
affiliation for compatibility with older clients, while the full ordered list is
stored in `affiliations`. Every accepted submission is credited in full to each
listed institution on the map; the dashboard's global submission total still
counts the submission only once, so institution totals intentionally overlap.

An admin can open `/admin`, edit the address or coordinates, use **Geocode
address**, and then choose **Approve exact point**. Approval requires a full
address and `Exact address` precision. The approved point replaces the
provisional point automatically; no edit to `affiliation_locations.json` or
frontend rebuild is needed.

The deployment therefore needs its normal persistent `DB_PATH`. ROR and
Nominatim do not require an API key, although `ROR_CLIENT_ID` is recommended for
identifying this service to ROR. Existing hand-reviewed locations remain in
`server/affiliation_locations.json`; newly discovered and approved locations are
stored in the `affiliation_location_reviews` database table.

The public Nominatim endpoint is rate-limited to one serialized request per
second and candidate results are persisted with the review record. Set
`NOMINATIM_SEARCH_URL` to switch to a hosted or self-hosted compatible service,
and set `NOMINATIM_USER_AGENT` to an application name with a monitored contact.
Deployments using the public endpoint must follow the [Nominatim usage
policy](https://operations.osmfoundation.org/policies/nominatim/).

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
- `ROR_CLIENT_ID`: optional client identification for ROR-powered affiliation search
- `NOMINATIM_SEARCH_URL`: configurable OpenStreetMap-compatible geocoding endpoint
- `NOMINATIM_USER_AGENT`: geocoder client identity including a monitored contact


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
