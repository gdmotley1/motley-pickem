/**
 * The two pieces of push that are real code rather than wiring, executed rather than
 * grepped: the base64url conversions in src/lib/push.js, and sameOriginPath in
 * static/sw.js.
 *
 * Both are the kind of thing that looks right and is wrong. A mis-padded key fails at
 * subscribe() time on the phone with an error nobody can read, and a notification click
 * that honours an absolute URL is an open redirect out of the app.
 *
 * Run by tests/test_push.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFile } from 'node:fs/promises'

const ROOT = process.cwd()
const read = (rel) => readFile(path.join(ROOT, rel), 'utf8')

/* Neither file can be imported under bare node: push.js imports api.js, which reaches for
   import.meta.env, and sw.js expects a ServiceWorkerGlobalScope. So each function is
   extracted and evaluated on its own. The match fails loudly if either is renamed, which
   is the point: a silently-skipped check is worse than no check. */
const extract = (src, re, name) => {
  const m = src.match(re)
  assert.ok(m, `${name} not found in the shape this check expects`)
  return m[0]
}

const pushSrc = await read('src/lib/push.js')
const swSrc = await read('static/sw.js')

const urlB64 = new Function(
  `${extract(pushSrc, /function urlBase64ToUint8Array\(base64\) \{[\s\S]*?\n\}/,
             'urlBase64ToUint8Array')}; return urlBase64ToUint8Array`,
)()

const encodeKey = new Function(
  `${extract(pushSrc, /function encodeKey\(subscription, name\) \{[\s\S]*?\n\}/,
             'encodeKey')}; return encodeKey`,
)()

/* sameOriginPath closes over BASE and self.location, so both are supplied here. */
const makeSameOriginPath = (base, origin) =>
  new Function(
    'BASE', 'self',
    `${extract(swSrc, /function sameOriginPath\(url\) \{[\s\S]*?\n\}/, 'sameOriginPath')
    }; return sameOriginPath`,
  )(base, { location: { origin } })

// ---------------------------------------------------------------- key conversion

{
  /* A real VAPID public key: 65 bytes, uncompressed P-256, leading 0x04. Safari rejects
     anything that is not exactly this shape, so the length and first byte are the whole
     assertion. This is the key generated for the project on 2026-09-11; it is public by
     design and ships in the browser bundle. */
  const key = 'BMguuWQq5DnWYVcX7TYBb-dxA-aa1Yo9p8wWfCb0q4F6hXBrq8rjttUKwY8BYBMYT079Uf_54znHOrzrQx7H5T0'
  const bytes = urlB64(key)
  assert.equal(bytes.length, 65, 'an applicationServerKey must be 65 bytes')
  assert.equal(bytes[0], 0x04, 'must be an uncompressed point')
  assert.ok(bytes instanceof Uint8Array, 'subscribe() will not take a plain array')
}

{
  /* The padding is the part that actually breaks. base64url strips '=', and atob throws
     on a length that is not a multiple of four, so every remainder has to be handled.
     A key of length %4 == 3 needs one '=' and %4 == 2 needs two. */
  globalThis.atob = (s) => Buffer.from(s, 'base64').toString('binary')
  for (const raw of [[1], [1, 2], [1, 2, 3], [1, 2, 3, 4], [1, 2, 3, 4, 5]]) {
    const b64url = Buffer.from(raw).toString('base64')
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
    const out = urlB64(b64url)
    assert.deepEqual([...out], raw, `round trip failed for ${raw.length} bytes`)
  }
}

{
  /* The other direction: an ArrayBuffer from getKey() has to come back as base64url with
     no padding and no + or /, or Postgres stores a string the sender cannot use. */
  globalThis.btoa = (s) => Buffer.from(s, 'binary').toString('base64')
  const bytes = new Uint8Array([251, 255, 190, 0, 1, 2]) // forces both + and / in plain b64
  const sub = { getKey: () => bytes.buffer }
  const out = encodeKey(sub, 'p256dh')
  assert.ok(!/[+/=]/.test(out), `encodeKey leaked base64 characters: ${out}`)
  assert.deepEqual([...urlB64(out)], [...bytes], 'encodeKey does not round trip')
  assert.equal(encodeKey({ getKey: () => null }, 'auth'), null,
               'a missing key must be null, not a crash')
}

// ---------------------------------------------------------------- click target

{
  const BASE = '/motley-pickem/'
  const sameOriginPath = makeSameOriginPath(BASE, 'https://gdmotley1.github.io')

  assert.equal(sameOriginPath('/motley-pickem/?tab=picks'), '/motley-pickem/?tab=picks')
  assert.equal(sameOriginPath('/motley-pickem/'), BASE)

  /* Everything below must fall back to BASE. The payload is written by our own database,
     but a notification click opens a window, so this refuses to be the thing that turns a
     bad row into a navigation off the app. */
  for (const hostile of [
    'https://evil.example/steal',
    '//evil.example/steal',
    'javascript:alert(1)',
    '/somewhere-else/',           // same origin, outside the app's scope
    '/motley-pickem-evil/',       // prefix that looks like BASE but is not a path under it
    null,
    undefined,
    42,
    '',
  ]) {
    assert.equal(sameOriginPath(hostile), BASE,
                 `sameOriginPath honoured ${JSON.stringify(hostile)}`)
  }

  /* This one exists because deleting the origin check did NOT fail the cases above, and
     a guard that cannot fail is not a guard. Every hostile value there also fails the
     scope check, so the scope check alone was carrying them. A foreign origin whose PATH
     is inside our scope is the case that separates the two: without the origin check
     this returns '/motley-pickem/?x=1' rather than falling back. */
  assert.equal(sameOriginPath('https://evil.example/motley-pickem/?x=1'), BASE,
               'the origin check is not doing anything')
}

console.log('push_check.mjs: all assertions passed')
