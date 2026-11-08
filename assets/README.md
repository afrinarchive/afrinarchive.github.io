# Local fonts, libraries and CSS

The website serves its fonts, MapLibre 4.3.2, Leaflet 1.9.4, D3 7.9.2,
Font Awesome 6.4.0 and compiled Tailwind 3.4.17 CSS from this folder.
Library and font licenses are included beside the files. The download sources
and SHA-256 checksums are recorded in `vendor/manifest.json`.

After adding or changing Tailwind classes, run from the project folder:

```powershell
npm run build:assets
```

Existing local downloads are reused. Pages regenerated with the old CDN
references are switched back to local files. New Google Fonts requests are
downloaded with all the language subsets supplied by Google, rather than
restricting them to Latin text. Keep the manifest with the downloaded files.

The desktop site updater also runs this command's script before rebuilding
the search index. Its HTML templates reference these local assets directly.

Street maps, map labels, glyphs and terrain now load from `maps/`; see that
folder's README for the saved area and data sources. GoatCounter and Esri
satellite imagery keep their existing outside providers. YouTube and other
external links remain unchanged.
