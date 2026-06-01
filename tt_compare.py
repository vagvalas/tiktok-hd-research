#!/usr/bin/env python3
"""Compare what tikwm exposes vs what yt-dlp's WEB path sees, for a TikTok URL.

Usage: PYTHONPATH=/Users/vaggosval/yt_dlp_tiktok python3 /tmp/tt_compare.py <url> [<url> ...]
"""
import json
import re
import sys
import urllib.parse
import urllib.request

UA = ('com.zhiliaoapp.musically/2023501030 (Linux; U; Android 13; en_US; '
      'Pixel 7; Build/TD1A.220804.031; Cronet/58.0.2991.0)')
WEB_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')


def get(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or {})
    return urllib.request.urlopen(req, timeout=timeout).read()


def tikwm(url):
    api = 'https://www.tikwm.com/api/?hd=1&url=' + urllib.parse.quote(url, safe='')
    d = json.loads(get(api, {'User-Agent': WEB_UA}))
    data = d.get('data') or {}
    return {
        'size': data.get('size'), 'hd_size': data.get('hd_size'),
        'bitrate': data.get('bitrate'), 'width': data.get('width'),
        'height': data.get('height'), 'duration': data.get('duration'),
        'play_host': re.sub(r'/.*', '', re.sub(r'https?://', '', data.get('play') or '')),
        'hd_host': re.sub(r'/.*', '', re.sub(r'https?://', '', data.get('hdplay') or '')),
    }


def web_gears(url):
    html = get(url, {'User-Agent': WEB_UA}).decode('utf-8', 'replace')
    m = re.search(r'id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None, 'no universal data (len %d)' % len(html)
    data = json.loads(m.group(1))
    v = (data.get('__DEFAULT_SCOPE__', {}).get('webapp.video-detail', {})
         .get('itemInfo', {}).get('itemStruct', {}).get('video', {}))
    gears = [{
        'gear': b.get('GearName'), 'qt': b.get('QualityType'),
        'bitrate': b.get('Bitrate'),
        'datasize': (b.get('PlayAddr') or {}).get('DataSize'),
        'urlkey': (b.get('PlayAddr') or {}).get('UrlKey'),
    } for b in v.get('bitrateInfo', [])]
    return {'wh': (v.get('width'), v.get('height')), 'size': v.get('size'),
            'gears': gears}, None


for url in sys.argv[1:]:
    print('=' * 70)
    print(url)
    try:
        t = tikwm(url)
        print('  tikwm: %sx%s  size=%s  hd_size=%s  bitrate=%s  dur=%s'
              % (t['width'], t['height'], t['size'], t['hd_size'], t['bitrate'], t['duration']))
        print('         play_host=%s  hd_host=%s' % (t['play_host'], t['hd_host']))
    except Exception as e:
        print('  tikwm ERROR:', e)
        t = None
    try:
        w, err = web_gears(url)
        if err:
            print('  web:', err)
        else:
            print('  web: %s  size=%s' % (w['wh'], w['size']))
            for g in w['gears']:
                print('       gear=%-14s qt=%-3s bitrate=%-9s datasize=%-9s'
                      % (g['gear'], g['qt'], g['bitrate'], g['datasize']))
            if t and t.get('hd_size') and w['gears']:
                web_best = max(int(g['datasize'] or 0) for g in w['gears'])
                ratio = (t['hd_size'] / web_best) if web_best else 0
                flag = '  <<< MISMATCH (tikwm HD bigger)' if t['hd_size'] > web_best * 1.15 else ''
                print('  >> tikwm hd_size=%s vs web best datasize=%s  (%.2fx)%s'
                      % (t['hd_size'], web_best, ratio, flag))
    except Exception as e:
        print('  web ERROR:', e)
