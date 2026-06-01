#!/usr/bin/env python3
"""PoC: register a TikTok device via SignerPy (ttencrypt body + gorgon sig),
then call aweme/v1/feed with the registered device_id/iid and dump bit_rate gears."""
import sys, time, json, hashlib, random, uuid, binascii
import urllib.request, urllib.parse, urllib.error

sys.path.insert(0, '/tmp/SignerPy')
from SignerPy import ttencrypt
from SignerPy.gorgon import Gorgon

REG_HOST = 'log-va.tiktokv.com'
API_HOST = 'api16-normal-c-useast1a.tiktokv.com'

# TikTok Lite (musically_go) — matches xtekky public demo structure
APP = {'aid': 1340, 'version': '16.9.4', 'version_code': '160904',
       'git_hash': '37aa18a', 'sig_hash': '194ce93da8b94895fc844eb88e8d995c',
       'release_build': 'd5fb1b3_20210910'}


def openudid():
    return binascii.hexlify(random.randbytes(8)).decode()


def gen_device():
    return {
        'device_model': 'SM-G9550', 'resolution': '1600x900', 'device_brand': 'samsung',
        'openudid': openudid(), 'google_aid': str(uuid.uuid4()), 'clientudid': str(uuid.uuid4()),
        'cdid': str(uuid.uuid4()), 'req_id': str(uuid.uuid4()),
        'install_time': int(round(time.time() * 1000)) - random.randint(13999, 15555),
        'rom': str(random.randint(700000000, 799999999)), 'tz_name': 'America/New_York', 'tz_offset': -14400,
    }


def reg_params(dev):
    return urllib.parse.urlencode({
        'ac': 'wifi', 'channel': 'googleplay', 'aid': APP['aid'], 'app_name': 'musically_go',
        'version_code': APP['version_code'], 'version_name': APP['version'], 'device_platform': 'android',
        'ab_version': APP['version'], 'ssmix': 'a', 'device_type': dev['device_model'],
        'device_brand': dev['device_brand'], 'language': 'en', 'os_api': 25, 'os_version': '7.1.2',
        'openudid': dev['openudid'], 'manifest_version_code': APP['version_code'], 'resolution': dev['resolution'],
        'dpi': 320, 'update_version_code': APP['version_code'], '_rticket': int(time.time() * 1000),
        'storage_type': 0, 'app_type': 'normal', 'sys_region': 'US', 'pass-route': 1, 'pass-region': 1,
        'timezone_name': dev['tz_name'], 'timezone_offset': dev['tz_offset'], 'carrier_region_v2': 310,
        'cpu_support64': 'false', 'host_abi': 'armeabi-v7a', 'ts': int(time.time()), 'build_number': APP['version'],
        'region': 'US', 'uoo': 0, 'app_language': 'en', 'carrier_region': 'US', 'locale': 'en', 'op_region': 'US',
        'ac2': 'wifi', 'cdid': dev['cdid'], 'tt_data': 'a',
    })


def reg_payload(dev):
    return {'magic_tag': 'ss_app_log', 'header': {
        'display_name': 'TikTok Lite', 'update_version_code': APP['version_code'],
        'manifest_version_code': APP['version_code'], 'app_version_minor': '', 'aid': APP['aid'],
        'channel': 'googleplay', 'package': 'com.zhiliaoapp.musically.go', 'app_version': APP['version'],
        'version_code': APP['version_code'], 'sdk_version': '2.12.1-rc.6-lite', 'sdk_target_version': 29,
        'git_hash': APP['git_hash'], 'os': 'Android', 'os_version': '7.1.2', 'os_api': 25,
        'device_model': dev['device_model'], 'device_brand': dev['device_brand'],
        'device_manufacturer': dev['device_brand'], 'cpu_abi': 'armeabi-v7a', 'release_build': APP['release_build'],
        'density_dpi': 320, 'display_density': 'xhdpi', 'resolution': dev['resolution'], 'language': 'en',
        'timezone': -4, 'access': 'wifi', 'not_request_sender': 0, 'carrier': 'Android', 'mcc_mnc': '31002',
        'rom': dev['rom'], 'rom_version': f"beyond {dev['rom']} release-keys", 'cdid': dev['cdid'],
        'sig_hash': APP['sig_hash'], 'gaid_limited': 0, 'google_aid': dev['google_aid'],
        'openudid': dev['openudid'], 'clientudid': dev['clientudid'], 'region': 'US', 'tz_name': dev['tz_name'],
        'tz_offset': dev['tz_offset'], 'sim_region': 'us', 'oaid_may_support': False, 'req_id': dev['req_id'],
        'apk_first_install_time': dev['install_time'], 'is_system_app': 0, 'sdk_flavor': 'global',
    }, '_gen_time': int(round(time.time() * 1000))}


def register():
    dev = gen_device()
    params = reg_params(dev)
    payload = ttencrypt.Enc().encrypt(data=json.dumps(reg_payload(dev)))
    if isinstance(payload, str):
        payload = bytes.fromhex(payload)
    unix = int(time.time())
    g = Gorgon(params=params, unix=unix, payload=payload, version=4404).get_value()
    headers = {
        'x-ss-stub': hashlib.md5(payload).hexdigest().upper(), 'accept-encoding': 'gzip',
        'passport-sdk-version': '17', 'sdk-version': '2', 'x-ss-req-ticket': str(int(time.time()) * 1000),
        'x-gorgon': g['x-gorgon'], 'x-khronos': g['x-khronos'],
        'content-type': 'application/octet-stream;tt-data=a', 'host': REG_HOST,
        'connection': 'Keep-Alive', 'user-agent': 'okhttp/3.10.0.1',
    }
    url = f'https://{REG_HOST}/service/2/device_register/?{params}'
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        body = r.read()
        print('REGISTER HTTP', r.status, 'bytes', len(body))
        print('  body head:', body[:300].decode('utf-8', 'replace'))
        d = json.loads(body)
        return dev, d.get('device_id'), d.get('install_id')
    except urllib.error.HTTPError as e:
        print('REGISTER HTTPError', e.code, e.read()[:200])
    except Exception as e:
        print('REGISTER ERR', repr(e))
    return dev, None, None


if __name__ == '__main__':
    dev, did, iid = register()
    print('device_id=%s install_id=%s' % (did, iid))
