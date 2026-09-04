"""The service worker's safety rules, which are mostly about what it must NOT do.

The app is a family pool whose locking and pick-visibility rules live in Postgres RLS.
A cache is the one thing that can quietly serve a result those policies already decided
you should not see, or hold a pick open past a kickoff. So the interesting assertions
here are negative: the worker touches same-origin GETs and nothing else.

These read static/sw.js as text rather than executing it. That is deliberate and it is
the limit of what this file proves: it catches the rules being edited away, not a logic
bug in the caching itself. Behaviour was checked in the browser against the deployed
site, which is the only place a worker actually runs.
"""
from __future__ import annotations

import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = os.path.join(ROOT, "static", "sw.js")
MAIN = os.path.join(ROOT, "src", "main.jsx")


@pytest.fixture(scope="module")
def sw():
    with open(SW, encoding="utf-8") as f:
        return f.read()


def code(text):
    """The source with comments stripped, so a rule described in prose is not mistaken
    for a rule the worker enforces."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


def test_the_worker_ships_with_the_site():
    """static/ is vite's publicDir, so anything in it lands at the site root. A worker
    served from a subdirectory would be scoped to that subdirectory and control nothing."""
    assert os.path.exists(SW), "static/sw.js is missing"
    with open(os.path.join(ROOT, "vite.config.js"), encoding="utf-8") as f:
        assert "publicDir: 'static'" in f.read()


def test_only_same_origin_gets_are_intercepted(sw):
    """The guard that keeps every Supabase RPC and every ESPN call out of the cache.

    RPCs are POSTs and ESPN is cross-origin, so these two lines are what stop a pick, a
    board another player cannot see yet, or a stale score from ever being stored.
    """
    body = code(sw)
    assert re.search(r"request\.method\s*!==\s*'GET'\s*\)\s*return", body), (
        "the worker no longer bails out of non-GET requests, so a Supabase RPC could be "
        "cached"
    )
    assert re.search(r"url\.origin\s*!==\s*self\.location\.origin\s*\)\s*return", body), (
        "the worker no longer bails out of cross-origin requests, so ESPN scores could "
        "be served stale from cache"
    )


def test_no_supabase_or_espn_host_is_named_anywhere(sw):
    """Belt and braces: naming either host at all would mean someone started handling it."""
    for host in ("supabase.co", "supabase.in", "espn.com"):
        assert host not in sw, (
            "%s appears in the service worker. Data from it must pass through "
            "untouched." % host
        )


def test_only_complete_first_party_responses_are_stored(sw):
    """An opaque or partial response cached as though it were real is how an app starts
    serving blank pages it cannot explain."""
    body = code(sw)
    assert "response.status !== 200" in body
    assert "response.type !== 'basic'" in body


def test_the_document_is_network_first(sw):
    """index.html carries no content hash. Cache-first on it means a deploy is never
    picked up and the family sits on an old build forever."""
    body = code(sw)
    assert "request.mode === 'navigate'" in body
    nav = body[body.index("networkFirstDocument"):]
    assert "await fetch(request)" in nav, "the document must try the network before the cache"


def test_logos_are_not_tied_to_the_cache_version(sw):
    """276 marks, about 12MB, none of which change when the app deploys."""
    body = code(sw)
    logos = re.search(r"const LOGOS\s*=\s*([^\n]+)", body)
    assert logos, "LOGOS cache name is gone"
    assert "VERSION" not in logos.group(1), (
        "the logo cache is versioned, so every deploy re-downloads a week of logos"
    )
    for name in ("SHELL", "ASSETS"):
        line = re.search(r"const %s\s*=\s*([^\n]+)" % name, body)
        assert "VERSION" in line.group(1), "%s must be versioned so a deploy invalidates it" % name


def test_stale_caches_are_dropped_on_activate(sw):
    body = code(sw)
    assert "caches.delete" in body and "KEEP" in body, (
        "nothing prunes old cache versions, so each deploy leaks a copy of the bundle"
    )


def test_the_base_path_is_derived_not_hard_coded(sw):
    """sw.js is copied verbatim by publicDir, so it never sees vite's base. Reading it
    off the worker's own URL is what lets the app move to a custom domain untouched."""
    body = code(sw)
    assert "new URL('./', self.location)" in body
    assert "/motley-pickem/" not in body, "the base path is hard-coded in the worker"


def test_registration_is_production_only(sw):
    """In dev the worker would serve cached modules over the top of an edit, and it would
    sit under the outputs/harness pages whose whole purpose is a stubbed network."""
    with open(MAIN, encoding="utf-8") as f:
        main = f.read()
    assert "import.meta.env.PROD" in main, "the worker would register in dev"
    assert "serviceWorker" in main and "register(" in main
    assert "import.meta.env.BASE_URL}sw.js" in main, (
        "registration must use the app's base path, not a bare /sw.js"
    )


def test_the_manifest_still_describes_an_installable_app():
    """The worker is only half of it: without these the phone never offers to install."""
    with open(os.path.join(ROOT, "static", "manifest.webmanifest"), encoding="utf-8") as f:
        m = json.load(f)
    assert m.get("display") == "standalone"
    assert m.get("start_url") and m.get("scope")
    sizes = {i.get("sizes") for i in m.get("icons", [])}
    assert {"192x192", "512x512"} <= sizes, "a 192 and a 512 icon are the install minimum"
