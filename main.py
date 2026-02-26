#!/usr/bin/env python3
"""
Site Cloner - Downloads a complete webpage into a local folder.
Usage:
    python site_cloner.py [URL]
    python site_cloner.py              (prompts for URL)

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse


COLLECTOR_JS = r"""
async () => {
    var assetIndex = 0;
    var assetMap = new Map();

    function getExt(url) {
        var clean = url.split('?')[0].split('#')[0];
        var match = clean.match(/\.([a-zA-Z0-9]+)$/);
        return match ? match[1] : 'bin';
    }

    function trackAsset(resolvedUrl, origAttr, subfolder) {
        if (!resolvedUrl || resolvedUrl.startsWith('data:') || resolvedUrl.startsWith('blob:')) return;
        if (assetMap.has(resolvedUrl)) {
            if (origAttr && origAttr !== resolvedUrl)
                assetMap.get(resolvedUrl).originals.add(origAttr);
            return;
        }
        var ext = getExt(resolvedUrl);
        var filename = subfolder + '_' + assetIndex++ + '.' + ext;
        var localPath = 'assets/' + filename;
        var entry = { localPath: localPath, originals: new Set() };
        if (origAttr && origAttr !== resolvedUrl)
            entry.originals.add(origAttr);
        assetMap.set(resolvedUrl, entry);
    }

    // --- Images ---
    document.querySelectorAll('img').forEach(function(img) {
        var origSrc = img.getAttribute('src');
        if (img.src) trackAsset(img.src, origSrc, 'img');
        var origSrcset = img.getAttribute('srcset');
        if (origSrcset) {
            origSrcset.split(',').forEach(function(part) {
                var origUrl = part.trim().split(/\s+/)[0];
                if (origUrl) {
                    var resolved = new URL(origUrl, document.baseURI).href;
                    trackAsset(resolved, origUrl, 'img');
                }
            });
        }
    });

    // --- Picture sources ---
    document.querySelectorAll('picture source[srcset]').forEach(function(source) {
        var origSrcset = source.getAttribute('srcset');
        if (origSrcset) {
            origSrcset.split(',').forEach(function(part) {
                var origUrl = part.trim().split(/\s+/)[0];
                if (origUrl) {
                    var resolved = new URL(origUrl, document.baseURI).href;
                    trackAsset(resolved, origUrl, 'img');
                }
            });
        }
    });

    // --- Background images in inline styles ---
    document.querySelectorAll('[style*="url"]').forEach(function(el) {
        var raw = el.getAttribute('style') || '';
        var matches = raw.matchAll(/url\(["']?(.*?)["']?\)/g);
        for (var mt of matches) {
            var origUrl = mt[1];
            if (origUrl && !origUrl.startsWith('data:')) {
                try {
                    var resolved = new URL(origUrl, document.baseURI).href;
                    trackAsset(resolved, origUrl, 'bg');
                } catch (e) {}
            }
        }
    });

    // --- Video, audio, favicon ---
    document.querySelectorAll('video source, video[src], audio source, audio[src], link[rel*="icon"]').forEach(function(el) {
        var resolvedUrl = el.src || el.href;
        var origUrl = el.getAttribute('src') || el.getAttribute('href');
        if (resolvedUrl) trackAsset(resolvedUrl, origUrl, 'media');
    });

    // --- CSS ---
    var css = '';
    for (var sheet of document.styleSheets) {
        try {
            for (var rule of sheet.cssRules) css += rule.cssText + '\n';
        } catch (e) {}
    }
    var urlRegex = /url\(["']?(https?:\/\/[^"')]+)["']?\)/g;
    var mt;
    while ((mt = urlRegex.exec(css)) !== null) {
        trackAsset(mt[1], null, 'css_asset');
    }

    // Replace URLs in CSS with local paths
    var processedCss = css.replace(/url\(["']?(https?:\/\/[^"')]+)["']?\)/g, function(full, url) {
        var entry = assetMap.get(url);
        return entry && entry.localPath ? 'url("../' + entry.localPath + '")' : full;
    });

    // --- Build HTML ---
    var html = document.documentElement.outerHTML;
    for (var [resolvedUrl, entry] of assetMap) {
        if (!entry.localPath) continue;
        html = html.split(resolvedUrl).join(entry.localPath);
        for (var orig of entry.originals) {
            html = html.split(orig).join(entry.localPath);
        }
    }
    html = html.replace('</head>', '<link rel="stylesheet" href="css/styles.css">\n</head>');
    html = '<!DOCTYPE html>\n' + html;

    // Serialize asset list
    var assets = [];
    for (var [url, entry] of assetMap) {
        assets.push({ url: url, localPath: entry.localPath });
    }

    return { html: html, css: processedCss, assets: assets };
}
"""


SCROLL_JS = r"""
async () => {
    await new Promise(function(resolve) {
        var totalHeight = 0;
        var distance = 300;
        var timer = setInterval(function() {
            window.scrollBy(0, distance);
            totalHeight += distance;
            if (totalHeight >= document.body.scrollHeight) {
                clearInterval(timer);
                window.scrollTo(0, 0);
                resolve();
            }
        }, 100);
    });
}
"""


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else input("Enter URL to clone: ").strip()
    if not url:
        print("No URL provided.")
        sys.exit(1)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright is required. Install it with:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    domain = urlparse(url).netloc.replace(":", "_")
    output_dir = Path(f"cloned_{domain}")
    (output_dir / "assets").mkdir(parents=True, exist_ok=True)
    (output_dir / "css").mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        print(f"Loading {url} ...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Warning: page load issue ({e}), continuing anyway...")

        # Scroll to trigger lazy-loaded content
        print("Scrolling page to load lazy content...")
        try:
            await page.evaluate(SCROLL_JS)
            await page.wait_for_timeout(2000)
        except Exception:
            pass

        print("Collecting page data...")
        result = await page.evaluate(COLLECTOR_JS)

        assets = result["assets"]
        total = len(assets)
        print(f"Downloading {total} assets...")

        ok_count = 0
        fail_count = 0
        for i, asset in enumerate(assets, 1):
            local_path = asset.get("localPath")
            if not local_path:
                continue
            try:
                resp = await context.request.get(asset["url"])
                if resp.ok:
                    body = await resp.body()
                    file_path = output_dir / local_path
                    file_path.write_bytes(body)
                    ok_count += 1
                    print(f"  [{i}/{total}] OK  {local_path} ({len(body) / 1024:.1f} KB)")
                else:
                    fail_count += 1
                    print(f"  [{i}/{total}] FAIL ({resp.status}): {asset['url']}")
            except Exception as e:
                fail_count += 1
                print(f"  [{i}/{total}] FAIL: {asset['url']} ({e})")

        # Save CSS
        (output_dir / "css" / "styles.css").write_text(result["css"], encoding="utf-8")
        print("Saved css/styles.css")

        # Save HTML
        (output_dir / "index.html").write_text(result["html"], encoding="utf-8")
        print("Saved index.html")

        await browser.close()

    print(f"\nDone! Site cloned to: {output_dir.resolve()}")
    print(f"Assets: {ok_count} downloaded, {fail_count} failed")


if __name__ == "__main__":
    asyncio.run(main())
