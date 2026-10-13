#!/usr/bin/env python3
"""Exercise the actual local exhibit HTML; never contact a provider or backend."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (320, 390, 768, 1280, 1920)
ICON_SHA = "6e2b7d72a3af3d9602b79de41df0194ede6496a9661f057108ec224c0efc92e6"


def run(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=False)
    source = (ROOT / "play.html").read_bytes()
    icon = re.search(rb'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600".*?</svg>', source, re.S)
    requests, outside, writes, errors = [], [], [], []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            requests.append(path)
            if path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(source)
            else:
                self.send_error(404)

        def do_POST(self):
            writes.append(self.path)
            self.send_error(405)

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    report = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "scope": "LOCAL_EXHIBIT_PRESENTATION_AND_CONTROLS_ONLY",
              "source_sha256": hashlib.sha256(source).hexdigest(),
              "accepted_icon_exact": icon is not None and hashlib.sha256(icon.group(0) + b"\n").hexdigest() == ICON_SHA,
              "widths": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=os.environ.get("CHROME_PATH"),
                                    args=["--disable-dev-shm-usage", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        context = browser.new_context(reduced_motion="reduce")

        def route(request):
            if request.request.method != "GET":
                writes.append(request.request.url)
                request.abort()
            elif request.request.url.startswith(origin + "/"):
                request.continue_()
            else:
                outside.append(request.request.url)
                request.abort()

        context.route("**/*", route)
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(origin, wait_until="domcontentloaded")
            boot = page.evaluate("""() => {
                const entry=document.querySelector('.entry'), b=document.querySelector('#boot');
                return {width:b.clientWidth,scrollWidth:b.scrollWidth,
                    menu:document.querySelector('#opgrid').getBoundingClientRect().toJSON(),
                    small:[...document.querySelectorAll('#boot button,#boot summary,#boot a')].filter(e=>e.getBoundingClientRect().height<43.5).map(e=>e.textContent),
                    panel:getComputedStyle(entry).backgroundColor,operatorCount:document.querySelectorAll('#opgrid button').length};
            }""")
            if width in (320, 1280):
                page.screenshot(path=str(output / f"grid-entry-{width}.png"))
            page.locator('#opgrid button').first.focus()
            page.keyboard.press("Space")
            page.wait_for_function("running && document.querySelector('#boot').hidden")
            start = page.evaluate("({gx,gy,t,canvasFocused:document.activeElement===c})")
            page.keyboard.down("d")
            page.wait_for_timeout(160)
            page.keyboard.up("d")
            moved = page.evaluate("({gx,gy})")
            page.locator('#pause').click()
            pause_at = page.evaluate("t")
            page.wait_for_timeout(120)
            pause_stable = page.evaluate("t") == pause_at
            page.locator('#pause').click()
            page.wait_for_function("!paused && document.activeElement===c")
            page.locator('[data-action="e"]').click()
            next_tool = page.evaluate("TOOLS[tool]")
            page.locator('[data-action="r"]').click()
            scan = page.evaluate("scanPulse > 0")
            button = page.locator('[data-key="s"]')
            box = button.bounding_box()
            before_touch = page.evaluate("({gx,gy})")
            page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
            page.mouse.down()
            page.wait_for_timeout(120)
            page.mouse.up()
            after_touch = page.evaluate("({gx,gy,held:keys.s})")
            projection = page.evaluate("""() => ({
                scale:projection.scale,left:projection.x-N*TILE_W*projection.scale/2,
                right:projection.x+N*TILE_W*projection.scale/2,
                top:projection.y,bottom:projection.y+N*TILE_H*projection.scale,
                hudTop:document.querySelector('#hud-top').getBoundingClientRect().bottom,
                hudBottom:document.querySelector('#hud-bottom').getBoundingClientRect().top,
                small:[...document.querySelectorAll('#hud button')].filter(e=>e.getBoundingClientRect().height<43.5||e.getBoundingClientRect().width<43.5).map(e=>e.textContent),
                controlOverflow:document.querySelector('#hud-bottom').scrollWidth>document.querySelector('#hud-bottom').clientWidth,
                pageOverflow:document.documentElement.scrollWidth>innerWidth+1
            })""")
            page.locator('#pause').click()
            if width in (320, 1280):
                page.screenshot(path=str(output / f"grid-play-{width}.png"))
            page.locator('#pause').focus()
            page.keyboard.press("Space")
            resume_native = page.evaluate("!paused && document.activeElement===c")
            page.keyboard.press("Escape")
            escape = page.evaluate("paused && !Object.values(keys).some(Boolean)")
            # End-state transition is a local UI fixture, not a successful extraction claim.
            page.evaluate("finish(false)")
            ended = page.evaluate("document.activeElement.id==='again' && !document.querySelector('#end').hidden")
            page.keyboard.press("Space")
            restarted = page.evaluate("!document.querySelector('#boot').hidden && document.activeElement.matches('#opgrid button')")
            report["widths"].append({"width": width, "boot": boot, "projection": projection,
                "space_deployed": start['canvasFocused'], "wasd_moved": moved['gx']>start['gx'] and moved['gy']<start['gy'],
                "pause_clock_stable": pause_stable, "next_tool": next_tool, "scan_active": scan,
                "touch_hold_moved": after_touch['gx']>before_touch['gx'] and after_touch['gy']>before_touch['gy'] and not after_touch['held'],
                "native_space_resume": resume_native, "escape_clears_keys": escape, "end_focus": ended, "restart_focus": restarted})
        page.emulate_media(forced_colors="active", reduced_motion="reduce")
        page.locator('#opgrid button').first.focus()
        report['forced_colors'] = page.evaluate("""() => ({outline:getComputedStyle(document.activeElement).outlineWidth,
            panel:getComputedStyle(document.querySelector('.entry')).backgroundColor,
            image:getComputedStyle(document.querySelector('#boot')).backgroundImage})""")
        # Storage denial must not prevent local play or trap the results screen.
        page.add_init_script("Storage.prototype.setItem=function(){throw new DOMException('Local denied-storage fixture','SecurityError')}")
        page.reload(wait_until="domcontentloaded")
        page.locator('#opgrid button').first.click()
        page.evaluate("finish(false)")
        report['denied_storage'] = page.locator('#storage-note').inner_text()
        context.close()
        browser.close()
    server.shutdown()
    server.server_close()
    thread.join()
    report.update(page_errors=errors, attempted_writes=writes, blocked_external_requests=outside, requested_paths=sorted(set(requests)))
    passed = report['accepted_icon_exact'] and not errors and not writes and not outside
    for row in report['widths']:
        boot, p = row['boot'], row['projection']
        passed = passed and boot['scrollWidth'] <= boot['width']+1 and not boot['small'] and boot['operatorCount']==8
        passed = passed and p['left']>=0 and p['right']<=row['width'] and p['top']>=p['hudTop'] and p['bottom']<=p['hudBottom']
        passed = passed and not p['small'] and not p['controlOverflow'] and not p['pageOverflow']
        passed = passed and all(row[k] for k in ('space_deployed','wasd_moved','pause_clock_stable','scan_active','touch_hold_moved','native_space_resume','escape_clears_keys','end_focus','restart_focus')) and row['next_tool']=='EXTRACTOR'
    passed = passed and report['forced_colors']['outline']=='3px' and report['forced_colors']['image']=='none' and 'unavailable' in report['denied_storage']
    report['passed'] = bool(passed)
    (output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'widths':len(report['widths']),'errors':errors,'writes':writes,'outside':outside}))
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
