#!/usr/bin/env python3
"""Save the site's satellite pictures into assets/maps/satellite.

Source: Copernicus Sentinel-2 level 2A, one cloud-free day, read from the public
Earth Search collection on Amazon. Only the area in map-data-config.json is read
(roughly 500 MB). Visitors never contact the source; they only see our copies.
Needs: pip install rasterio pillow numpy

    python scripts/build-satellite-tiles.py            build everything missing
    python scripts/build-satellite-tiles.py --test     one quick overview picture
"""
import json
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "scripts/map-data-config.json").read_text(encoding="utf-8"))
OUT = ROOT / "assets/maps/satellite"
DAY = CONFIG["satelliteDate"]
WEST, SOUTH, EAST, NORTH = CONFIG["bounds"]
HALF = 20037508.342789244
TOP, LOW, BLOCK = 14, 8, 10          # most detailed, least detailed, working-block zoom
EMPTY = np.array([0x8F, 0x7F, 0x63], dtype="uint8")  # background colour in js/local-maps.js
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MULTIRANGE="YES",
           GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_HTTP_MAX_RETRY="6",
           GDAL_HTTP_RETRY_DELAY="2", GDAL_CACHEMAX=512)


def tile_of(lng, lat, zoom):
    n = 2 ** zoom
    x = (lng + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y)


def box(x, y, zoom):
    size = 2 * HALF / 2 ** zoom
    return (-HALF + x * size, HALF - (y + 1) * size, -HALF + (x + 1) * size, HALF - y * size)


def scenes():
    url = ("https://earth-search.aws.element84.com/v1/search?collections=sentinel-2-l2a"
           f"&bbox={WEST},{SOUTH},{EAST},{NORTH}&datetime={DAY}T00:00:00Z/{DAY}T23:59:59Z&limit=50")
    found = {}
    for item in json.load(urllib.request.urlopen(url, timeout=60))["features"]:
        zone = item["id"].split("_")[1]
        if zone.startswith("37"):
            found.setdefault(zone, item)
    # The two scenes that hold nearly everything come first.
    return [found[z] for z in sorted(found, key=lambda z: (z[-1] != "A", z))]


def read_band(items, band, bounds, width, height):
    out = np.zeros((height, width), dtype="uint16")
    with rasterio.Env(**ENV):
        for item in items:
            if out.all():
                break
            # The test picture is small, so it reads the source's reduced copy.
            coarse = {"overview_level": 3} if (bounds[2] - bounds[0]) / width > 80 else {}
            with rasterio.open(item["assets"][band]["href"], **coarse) as src:
                with WarpedVRT(src, crs="EPSG:3857", transform=from_bounds(*bounds, width, height),
                               width=width, height=height, src_nodata=0, nodata=0,
                               resampling=Resampling.cubic) as vrt:
                    data = vrt.read(1)
            out = np.where(out == 0, data, out)
    return out


def picture(items, bounds, width, height):
    with ThreadPoolExecutor(3) as pool:
        bands = list(pool.map(lambda b: read_band(items, b, bounds, width, height), ("red", "green", "blue")))
    raw = np.stack(bands, axis=-1)
    missing = (raw == 0).any(axis=-1)
    value = raw.astype("float32") / 10000
    # Remove a little haze per colour, then a gentle curve that keeps pale
    # limestone from burning out and lifts the dark olive groves.
    value -= np.array([0.005, 0.012, 0.018], dtype="float32")
    np.clip(value, 0, None, out=value)
    white = 0.46
    curve = np.log1p(value * 5) / math.log1p(white * 5)
    curve = np.clip(curve, 0, 1) ** 1.12
    grey = curve.mean(axis=-1, keepdims=True)
    curve = np.clip(grey + (curve - grey) * 0.88, 0, 1)
    image = (curve * 255 + 0.5).astype("uint8")
    image[missing] = EMPTY
    return image, missing


def save(image, zoom, x, y):
    path = OUT / str(zoom) / str(x) / f"{y}.webp"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path, "WEBP", quality=80, method=6)


def halve(image):
    h, w = image.shape[:2]
    return (image.reshape(h // 2, 2, w // 2, 2, 3).astype("uint16").sum(axis=(1, 3)) // 4).astype("uint8")


def main():
    items = scenes()
    print("Scenes:", [item["id"] for item in items])
    x0, y0 = tile_of(WEST, NORTH, TOP)
    x1, y1 = tile_of(EAST, SOUTH, TOP)
    if "--test" in sys.argv:
        left, _, _, top = box(x0, y0, TOP)
        _, bottom, right, _ = box(x1, y1, TOP)
        width = 1000
        image, missing = picture(items, (left, bottom, right, top), width, int(width * (top - bottom) / (right - left)))
        Image.fromarray(image).save(sys.argv[-1])
        print("missing share", missing.mean())
        return

    scale = 2 ** (TOP - BLOCK)
    size = 256 * scale
    tiny = {}
    total_missing = 0
    work = OUT.parent / "satellite_blocks"
    work.mkdir(exist_ok=True)
    for bx in range(x0 // scale, x1 // scale + 1):
        for by in range(y0 // scale, y1 // scale + 1):
            cache = work / f"{bx}_{by}.npy"
            tx0, tx1 = max(x0, bx * scale), min(x1, bx * scale + scale - 1)
            ty0, ty1 = max(y0, by * scale), min(y1, by * scale + scale - 1)
            if cache.exists():
                tiny[bx, by] = np.load(cache)
                continue
            left, _, _, top = box(tx0, ty0, TOP)
            _, bottom, right, _ = box(tx1, ty1, TOP)
            part, missing = picture(items, (left, bottom, right, top), (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256)
            total_missing += int(missing.sum())
            full = np.empty((size, size, 3), dtype="uint8")
            full[:] = EMPTY
            oy, ox = (ty0 - by * scale) * 256, (tx0 - bx * scale) * 256
            full[oy:oy + part.shape[0], ox:ox + part.shape[1]] = part
            level, zoom = full, TOP
            while True:
                count = level.shape[0] // 256
                step = 2 ** (TOP - zoom)
                jobs = [(i, j) for i in range(count) for j in range(count)
                        if (bx * count + i) * step <= x1 and (bx * count + i + 1) * step > x0
                        and (by * count + j) * step <= y1 and (by * count + j + 1) * step > y0]
                with ThreadPoolExecutor(6) as pool:
                    list(pool.map(lambda ij: save(level[ij[1] * 256:ij[1] * 256 + 256, ij[0] * 256:ij[0] * 256 + 256],
                                                  zoom, bx * count + ij[0], by * count + ij[1]), jobs))
                if zoom == BLOCK:
                    break
                level, zoom = halve(level), zoom - 1
            tiny[bx, by] = level
            np.save(cache, level)
            print(f"Block {bx}/{by} done, missing pixels {int(missing.sum())}", flush=True)

    current = tiny
    for zoom in range(BLOCK - 1, LOW - 1, -1):
        parents = {}
        for (x, y), image in current.items():
            parent = parents.setdefault((x // 2, y // 2), np.tile(EMPTY, (512, 512, 1)).astype("uint8"))
            parent[(y % 2) * 256:(y % 2) * 256 + 256, (x % 2) * 256:(x % 2) * 256 + 256] = image
        current = {key: halve(image) for key, image in parents.items()}
        for (x, y), image in current.items():
            save(image, zoom, x, y)
    for leftover in work.glob("*.npy"):
        leftover.unlink()
    work.rmdir()
    files = list(OUT.rglob("*.webp"))
    print(f"Saved {len(files)} pictures, {sum(f.stat().st_size for f in files) / 1e6:.1f} MB, missing pixels {total_missing}")


if __name__ == "__main__":
    main()
