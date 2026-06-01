# TikTok HD / Source-Quality Investigation

Goal: get the **highest-quality TikTok video** into yt-dlp — ideally the uploaded
*original* (what "HD downloader" sites advertise) — figure out the native method,
and land it as a yt-dlp PR (no third-party API dependency, per maintainer policy).

> Status: **investigation ~90% done. Blocked on one input (a valid `iid`) to confirm the
> remaining quality gap.** See [What's left](#whats-left-to-the-goal).

---

## TL;DR

- ❌ **The true uploaded original (~100 MB) is gone for everyone.** TikTok patched the trick
  (`aweme/v1/play?ratio=default`); `aweme/v1/play` now requires a `file_id` that maps to a
  **transcoded** file, not the source. The sites that did this are broken.
- ✅ **Best reachable quality today = the mobile/app API `bit_rate` ladder** (best h264).
  yt-dlp **already parses this** (`_parse_aweme_video_app`) — but its mobile path is **dead**.
- ❌ **yt-dlp's mobile path is broken**: stale app version (`35.1.3`) + unsigned request
  (`X-Argus: ''`) → TikTok replies `429 / empty`, so yt-dlp silently falls back to the **web path**.
- ⚠️ The **web path** (`__UNIVERSAL_DATA__ → video.bitrateInfo`) is a *trimmed* gear set. For many
  videos it already matches what tikwm serves — but it can lack the high-bitrate gears the mobile
  API has (e.g. a `normal_1080_0` h264).

**The realistic, mergeable goal** is no longer "fetch the original" — it's
**restore yt-dlp's signed mobile-API path** (app `39.8.2` + real signing) so it again pulls the
mobile `bit_rate` ladder. This also fixes yt-dlp issue
[#13134](https://github.com/yt-dlp/yt-dlp/issues/13134).

---

## Real example & measured data

Test URL: **`https://www.tiktok.com/@travelsbyjill/video/7371547116210048288`** (54 s, portrait)

| Source / path | Format | Size | Bitrate |
|---|---|---|---|
| yt-dlp **default pick** (web path, current master) | `bytevc1_1080p` (h265, 1080×1920) | **9.68 MiB** (10,149,689 B) | 1498 kbps |
| yt-dlp alt (web path) | `h264_540p` (576×1024) | 9.88 MiB (10,362,301 B) | 1529 kbps |
| **tikwm `?hd=1`** → `hd_size` | h265 1080p (same file) | **9.68 MiB** (10,149,689 B) | — |
| **tikwm** → `size` | h264 540p (same file) | 9.88 MiB (10,362,301 B) | — |
| TikTok uploaded **original** (~100 MB, h264 1080p high-bitrate) | — | **unreachable** (patched) | — |

> tikwm's "HD" (9.68 MiB) is **byte-identical** to what current yt-dlp already downloads.
> Confirmed the same parity on `@alex_selekos/video/7645243669045382422` (1080p h265 = 13.25 MiB
> on both) and `@alexandra_mitsi/video/7486187445596245270` (540p source = 2.58 MiB on both).
> **tikwm is not a source of higher quality than yt-dlp** — both top out at the same transcoded
> renditions. The only thing the mobile API may add is a **higher-bitrate 1080p h264** the web
> path omits — that's the gap we still need to measure (needs a valid device; see below).

Reproduce: `python3 tt_compare.py "<tiktok url>"` (prints tikwm `hd_size` vs web gear ladder).

---

## How the HD sites work (and why it's mostly moot now)

1. **Web path** — scrape `__UNIVERSAL_DATA_FOR_REHYDRATION__` from the page → `video.bitrateInfo`.
   Limited, trimmed gear set. yt-dlp's default today.
2. **Mobile/app API** — `POST aweme/v1/multi/aweme/detail` (or `feed`) → full `video.bit_rate`
   ladder (best h264 + h265 gears). **Requires a registered device + request signing**
   (`x-gorgon`, `x-khronos`, `x-ladon`, `x-argus`). This is what the still-working sites use.
3. **The old "original" trick** — `aweme/v1/play?ratio=default` returned the un-transcoded source.
   **Patched**: now needs `file_id` → transcoded file only. Dead for everyone.

---

## Getting a working device (the one input we need)

The mobile API needs a valid **`device_id` + `install_id` (`iid`)** pair, issued by TikTok at
device registration. Two ways:

### Option A — Capture from a real TikTok app (reliable) ✅ recommended
1. Run the **TikTok Android app** on an emulator (Android Studio AVD / Genymotion) or a phone.
2. Intercept its traffic with **HTTP Toolkit** (easiest — auto Frida SSL-unpinning on emulators),
   or mitmproxy / PCAPdroid (TikTok pins certs → needs root + Frida unpinning or a patched APK).
3. Watch requests to `api16-normal-c-useast1a.tiktokv.com/aweme/v1/...` and copy the query params:
   `iid=…`, `device_id=…` (also `cdid`, `openudid`). Use them as a pair.
   They stay valid until TikTok rotates/bans them.

### Option B — Self-register via `/service/2/device_register/` (fragile, gated)
Reverse-engineered & PoC'd here (`tt_register_poc.py`). Uses
[SignerPy](https://github.com/is-L7N/SignerPy) `ttencrypt` (body cipher) + `Gorgon` (signing).
- **Result:** `HTTP 200` + valid JSON `{"server_time":…,"device_id":0,"install_id":0}` — TikTok
  **decrypted the body and verified the signature** (the crypto pipeline is correct), but returned
  `device_id:0` = device-profile **rejected**. Newer profiles hit `HTTP 307` region-redirects.
- **Why it's hard:** the device-profile constants (`version_code`, `sig_hash`, `git_hash`,
  current region host) rotate frequently and the working values are gated/sold. This is the
  same fragility that broke yt-dlp's app path (#13134).

### Working request shape (app 39.8.2, needs a real `iid`)
```python
# pip install SignerPy pycryptodome
from SignerPy import sign, get
import requests, time

iid = "REPLACE_WITH_A_REAL_IID"          # from Option A
device_id = "REPLACE_WITH_PAIRED_DEVICE_ID"
params = { 'aid':'1233','app_name':'musical_ly','version_name':'39.8.2','version_code':'390802',
           'manifest_version_code':'2023508030','update_version_code':'2023508030',
           'device_platform':'android','os':'android','channel':'googleplay','device_type':'Pixel 7',
           'device_brand':'Google','os_version':'13','resolution':'1080*2400','dpi':'420','region':'US',
           'sys_region':'US','carrier_region':'US','iid':iid,'device_id':device_id }
data = { 'aweme_ids':'[7371547116210048288]','request_source':'0' }
params = get(params); params['iid']=iid; params['device_id']=device_id
headers = { 'User-Agent':'com.zhiliaoapp.musically/2023508030 (Linux; U; Android 13; en_US; '
            'Pixel 7; Build/TD1A.220804.031; Cronet/58.0.2991.0)',
            'Content-Type':'application/x-www-form-urlencoded', **sign(params=params, payload=data) }
r = requests.post('https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/multi/aweme/detail/',
                  params=params, headers=headers, data=data); print(r.status_code, len(r.content))
# With a bogus iid → HTTP 200 but EMPTY body. With a valid iid → full JSON incl. video.bit_rate.
```

---

## What's left to the goal

- [ ] **1. Obtain a valid `iid` + `device_id`** (Option A capture). ← only blocker right now.
- [ ] **2. Measure the gap:** run `tt_signed_poc.py` / the snippet above and compare the mobile
      `bit_rate` ladder vs the web path. Confirm whether the mobile API yields a higher-bitrate
      1080p h264 the web path lacks (and by how many MB).
- [ ] **3. If the gap is real → implement in `yt_dlp/extractor/tiktok.py`:**
      bump `_APP_INFO_DEFAULTS` to app `39.8.2` / manifest `2023508030`, and add a **clean-room
      pure-Python signer** (gorgon/khronos/ladon/argus) so `_call_api` produces valid headers
      (replacing the current empty `X-Argus: ''`). yt-dlp already parses the result.
- [ ] **4. Tests + PR** (frame as native, no third-party dep; cites #4138 / #13134 / #14172).

### The hard question for a shippable PR
A captured `iid` proves the gap **but can't ship** — yt-dlp can't ask every user to capture one.
A real feature needs **runtime device registration** (Option B), i.e. owning the
gorgon/ladon/argus + `device_register` stack whose magic constants rotate constantly. That
maintenance burden is exactly what yt-dlp maintainers have resisted. **Decision pending:** is the
quality gain (a bigger 1080p h264) worth that ongoing maintenance? Answer after step 2.

---

## How it would be implemented — and why it can't use one shared device

### The only architecture that works: per-user runtime registration
yt-dlp would have to **register a fresh device on each user's machine at first use** — i.e. do the
`/service/2/device_register/` call locally, get a `device_id` + `iid` for *that* user, cache it, and
sign subsequent `aweme/v1/...` calls (gorgon/khronos/ladon/argus) with it. Each user then looks like
**one normal app install on one normal IP** — load is distributed, nothing is shared.

### Why a single shared `iid` (baked into yt-dlp for everyone) does NOT work
- **Open source = public credential.** Anything hardcoded in `tiktok.py` is on GitHub for all to see,
  including TikTok. A shared `device_id`/`iid` is not a secret — it can be blocked instantly.
- **One device, the whole world = textbook abuse → fast ban.** TikTok rate-limits per `device_id`.
  A single ID hit from thousands of IPs at once is flagged as a bot farm in hours or less
  (we already saw `ratelimit triggered` from unregistered probes).
- **Single point of failure.** When that ID is banned, the feature breaks for **every** yt-dlp user
  at once — then a new ID must be shipped in a release, only to be banned again. Endless.

### Why tiktokdownloader.io / tikwm CAN do it (and yt-dlp can't copy them)

| | tiktokdownloader.io / tikwm | yt-dlp |
|---|---|---|
| Runs on | their **own servers** (central) | **each user's machine** (decentralized) |
| Devices | a **rotated pool** of many registered devices | one shared, or one-per-user |
| IPs | their servers + **proxies** they control | each user's home IP |
| Maintenance | **babysat 24/7**, re-register banned devices | only whatever ships in a release |
| The IDs | server-side, **users never see them** | source is **public** |

They run a **managed, rotating fleet** behind proxies and quietly re-register banned devices —
server-side. yt-dlp is a standalone client with **no backend**: it can't host a device pool, can't
proxy, can't centrally re-register. Making yt-dlp phone home to a central service would violate its
"no backend / no tracking" design — maintainers won't do it.

### The catch (why this still isn't done)
Per-user registration is viable *only* if yt-dlp carries the registration algorithm itself —
the ttencrypt body + gorgon/ladon/argus signing + the **current** `version_code` / `sig_hash` /
region-host constants. TikTok **rotates those constantly** to break exactly this, so the code would
need updating every few weeks, forever. That ongoing maintenance burden is the real reason yt-dlp's
app path has been left broken ([#13134](https://github.com/yt-dlp/yt-dlp/issues/13134)) rather than
chased.

**One line:** a shared/personal single `iid` fails (public + single bannable point of failure);
per-user runtime registration is the only design that works, but it forces yt-dlp to maintain a
constantly-rotating signing/registration stack.

---

## Files in this folder

| File | Purpose |
|---|---|
| `tt_compare.py` | For a URL, print tikwm `hd_size`/bitrate vs the web `bitrateInfo` gear ladder; flag mismatches. |
| `tt_signed_poc.py` | Call the app API (`feed` / `multi/aweme/detail`) with SignerPy signing; dump the `bit_rate` ladder. Currently `429` without a registered device. |
| `tt_register_poc.py` | `/service/2/device_register/` PoC (ttencrypt body + gorgon). Reaches `HTTP 200` but `device_id:0` (gated constants). |

Dependencies for the PoCs: [`SignerPy`](https://github.com/is-L7N/SignerPy) + `pycryptodome`
(`pip install SignerPy pycryptodome`). SignerPy is used **only for investigation** — a yt-dlp PR
would need a clean-room reimplementation, not a dependency.

### Sources
- yt-dlp issues [#4138](https://github.com/yt-dlp/yt-dlp/issues/4138),
  [#13134](https://github.com/yt-dlp/yt-dlp/issues/13134),
  [#14172](https://github.com/yt-dlp/yt-dlp/issues/14172);
  PR [#9575](https://github.com/yt-dlp/yt-dlp/pull/9575) (bytevc2 deprioritization).
- [SignerPy](https://github.com/is-L7N/SignerPy),
  [xtekky/TikTok-Device-Registration](https://github.com/xtekky/TikTok-Device-Registration).
