# Kamel Spotlight

Personal movie-library website. Static site (GitHub Pages), no build step.

    sheet (published CSV) --> scripts/build_cache.py --> docs/data/*.json --> docs/ (vanilla JS)

- Rename the site: `docs/js/config.js` (`siteName`).
- Refresh data: `python3 scripts/build_cache.py [csv path or url]`.
- Texts / AR-EN: `docs/js/i18n.js`. Colors: top of `docs/css/style.css`.
- Each file does one thing (data.js loads, search.js searches, views.js draws pages, app.js routes), so editing one part does not break the others.

## Install as an app (PWA)
`docs/manifest.webmanifest` + `docs/sw.js` + icons in `docs/img/`. Needs HTTPS (GitHub Pages is). After changing site files, bump `V` in `docs/sw.js` (e.g. ks-v2) so installed copies refresh.


Note: the source spreadsheet export (data/sheet.csv) is kept private and is not stored in this repository. Put your own copy there to run scripts/build_cache.py.
