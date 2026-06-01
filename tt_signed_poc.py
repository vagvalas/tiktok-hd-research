#!/usr/bin/env python3
"""PoC: call TikTok's app API with SignerPy signing and dump the bit_rate ladder.

Usage: python3 /tmp/tt_signed_poc.py <aweme_id> [<aweme_id> ...]
"""
import sys
import time
import json
import urllib.parse
import urllib.request

sys.path.insert(0, '/tmp/SignerPy')
from SignerPy import sign, get  # noqa: E402

HOST = 'api16-normal-c-useast1a.tiktokv.com'
APP_VERSION = '35.1.3'
MANIFEST = '2023501030'
UA = ('com.zhiliaoapp.musically/%s (Linux; U; Android 13; en_US; Pixel 7; '
      'Build/TD1A.220804.031; Cronet/58.0.2991.0)' % MANIFEST)


def base_params(aweme_id):
    p = {
        'aweme_id': aweme_id,
        'aid': '1233',
        'app_name': 'musical_ly',
        'version_code': '350103',
        'version_name': APP_VERSION,
        'manifest_version_code': MANIFEST,
        'update_version_code': MANIFEST,
        'ab_version': APP_VERSION,
        'build_number': APP_VERSION,
        'device_platform': 'android',
        'os': 'android',
        'channel': 'googleplay',
        'device_type': 'Pixel 7',
        'device_brand': 'Google',
        'os_version': '13',
        'os_api': '29',
        'resolution': '1080*2400',
        'dpi': '420',
        'language': 'en',
        'region': 'US',
        'sys_region': 'US',
        'carrier_region': 'US',
        'app_language': 'en',
        'locale': 'en',
        'timezone_name': 'America/New_York',
        'timezone_offset': '-14400',
        'ac': 'wifi',
        'ssmix': 'a',
    }
    get(p)  # adds _rticket, ts, iid, device_id, cdid, openudid
    return p


def call(ep, aweme_id, data=None):
    params = base_params(aweme_id)
    qs = urllib.parse.urlencode(params)
    sig = sign(params=qs, payload=(urllib.parse.urlencode(data) if data else None), aid=1233)
    headers = {
        'User-Agent': UA,
        'Accept': 'application/json',
        'x-ss-req-ticket': sig.get('x-ss-req-ticket', ''),
        'x-khronos': sig.get('x-khronos', ''),
        'x-gorgon': sig.get('x-gorgon', ''),
        'x-ladon': sig.get('x-ladon', ''),
        'x-argus': sig.get('x-argus', ''),
        'x-ss-stub': sig.get('x-ss-stub', ''),
    }
    url = 'https://%s/aweme/v1/%s/?%s' % (HOST, ep, qs)
    body = urllib.parse.urlencode(data).encode() if data else None
    if body:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        return None, 'HTTP error: %s' % e
    return raw, None


def dump_gears(aweme_id):
    print('=' * 70)
    print('aweme_id', aweme_id)
    for ep, data in [('feed', None),
                     ('multi/aweme/detail', {'aweme_ids': '[%s]' % aweme_id, 'request_source': '0'})]:
        raw, err = call(ep, aweme_id, data)
        if err:
            print('  [%s] %s' % (ep, err))
            continue
        print('  [%s] %d bytes' % (ep, len(raw)))
        head = raw[:200].decode('utf-8', 'replace')
        try:
            d = json.loads(raw)
        except Exception:
            print('     non-JSON head:', head)
            continue
        aw = (d.get('aweme_list') or d.get('aweme_details') or [])
        if not aw:
            print('     no aweme in response; keys=', list(d.keys())[:12],
                  'status_code=', d.get('status_code'), d.get('status_msg'))
            continue
        v = (aw[0] or {}).get('video') or {}
        print('     video %sx%s  duration=%s' % (v.get('width'), v.get('height'),
              (v.get('duration'))))
        for b in v.get('bit_rate', []):
            pa = b.get('play_addr') or {}
            print('     gear=%-18s qt=%-3s bitrate=%-9s data_size=%-10s codec=%s'
                  % (b.get('gear_name'), b.get('quality_type'), b.get('bit_rate'),
                     pa.get('data_size'), 'h265' if (b.get('is_bytevc1') or b.get('is_h265')) else 'h264'))
        for fld in ('play_addr', 'play_addr_h264', 'play_addr_bytevc1', 'download_addr'):
            a = v.get(fld) or {}
            if a:
                print('     %-18s data_size=%-10s %sx%s' % (fld, a.get('data_size'), a.get('width'), a.get('height')))
        return  # one endpoint that worked is enough


for aid in sys.argv[1:]:
    dump_gears(aid)
