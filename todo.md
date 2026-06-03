# TODO — TikTok HD/source native extraction

Status as of **2026-06-03**. See `README.md` for full findings.

## Where we are

- ✅ Quality gap is **real & current**: tikdownloader's "MP4 HD" = `v16.tokcdn.com/<id>_original.mp4`
  (3rd-party mirror) = **HEVC 1080×1920 @ 7.03 Mbps, 93.7 MB**; yt-dlp/web best = HEVC 1080×1920 @
  **1.01 Mbps, 13.25 MB**. Same res+codec, **~7× bitrate** (proven via ffprobe on `alex_selekos/7645243669045382422`).
- ✅ tokcdn caches originals **continuously** (path timestamp = each video's upload date) — not stale.
- ✅ The 7 Mbps file is almost certainly a **high gear in the mobile API `bit_rate` ladder** — web only
  gets `adapt_lowest_1080_1` ("lowest" 1080p); higher siblings exist but aren't served to web. tikwm
  `hd=1` also only returns the lowest, so tikdownloader does a fuller mobile extraction.
- ✅ iOS IPA examined: **TikTok 45.4.0**, code in `MusicallyCore` (746 MB ARM64), signing =
  **metasec/byteaegis** (X-Gorgon/Argus/Ladon/Khronos), net = TTNet/Cronet, `device_register` present.
- ⛔ **BLOCKED:** need a valid `iid` + `device_id` to query the signed mobile API and confirm the gear.

## NEXT — capture iid/device_id (unblocks everything)

- [ ] On Mac: `pip3 install frida-tools` (match device frida-server major version). USB-connect iPhone.
- [ ] Confirm: `frida-ps -Uai | grep -i tiktok` → `com.zhiliaoapp.musically`.
- [ ] Run hook: `frida -U -f com.zhiliaoapp.musically -l tt_capture.js` (hooks boringssl
      `SSL_write`/`SSL_read`, pinning-agnostic — see `tt_capture.js`).
- [ ] Open the target video in TikTok → from the `==== REQUEST ====` block hitting `…tiktokv.com/aweme/v1/…`,
      copy `iid=`, `device_id=`, `cdid=`, `openudid=`, and note `version_name`/`aid`.
- [ ] (Alt: mitmproxy + SSL Kill Switch 2 — but Cronet may bypass proxy/pin; Frida preferred.)

## THEN — confirm the gear is natively reachable

- [ ] Plug captured `iid`+`device_id` into a SignerPy-signed `multi/aweme/detail` call
      (`tt_signed_poc.py`, app 39.8.2/45.4.0) for the test video.
- [ ] Dump the full `video.bit_rate` ladder; check for the ~7 Mbps 1080p gear (`adapt_high_1080`/
      `normal_1080_0`/similar) and compare `data_size` to the 93.7 MB tokcdn file.
- [ ] **Decision gate:**
  - If the 7 Mbps gear IS in the mobile API → native implementation is justified → proceed.
  - If NOT (only tokcdn has it) → it's third-party-only → document and stop (yt-dlp won't depend on 3rd-party).

## IF green-lit — implement in yt-dlp

- [ ] Clean-room **pure-Python** signer: `x-gorgon` / `x-khronos` / `x-ladon` / `x-argus` (+ `x-ss-stub`).
      (Reverse `metasec` in `MusicallyCore` with Ghidra/IDA, or the Android `.so`; do NOT depend on/copy SignerPy.)
- [ ] **Runtime device registration** (`/service/2/device_register/`, ttencrypt body) so each user mints
      their own `device_id`/`iid` and caches it — a shared/baked-in id can't work (public + bannable).
- [ ] Wire into `yt_dlp/extractor/tiktok.py`: bump `_APP_INFO_DEFAULTS` (39.8.2/45.4.0), fix `_call_api`
      to emit real signatures (replace empty `X-Argus: ''`), surface the high `bit_rate` gear as a format.
- [ ] Tests (`_TESTS`), run `python -m yt_dlp -F` on real URLs, lint, PR (cite #4138/#13134/#14172).

## Open risks

- **Maintenance treadmill:** TikTok rotates the algorithm/constants every few weeks → any port rots.
  This is why yt-dlp maintainers have left the app path dead (#13134); merge is not guaranteed.
- **metasec is heavily obfuscated** (iOS variant harder than Android) — extracting it is a major RE effort.
- HD gear may be region/login-gated — verify the captured request isn't authenticated (`sid_tt`).

## Artifacts

- `README.md` — full investigation write-up + evidence.
- `tt_compare.py` — tikwm vs web gear comparator.
- `tt_signed_poc.py` — signed app-API call → dumps `bit_rate` ladder (needs valid iid).
- `tt_register_poc.py` — device_register PoC (200 + parsed, device_id:0 w/o current constants).
- `tt_capture.js` — Frida TLS hook to capture iid/device_id from the app.
- iOS IPA: `/Users/vaggosval/yt_dlp_tiktok/decrypted_ipa` (TikTok 45.4.0).
