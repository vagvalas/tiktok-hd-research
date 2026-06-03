// tt_capture.js — dump TikTok HTTPS traffic at the TLS layer (pinning-agnostic)
// Hooks boringssl SSL_write (plaintext request) and SSL_read (plaintext response)
// inside the app, so TTNet/Cronet cert-pinning doesn't matter.
//
// Run (spawn):   frida -U -f com.zhiliaoapp.musically -l tt_capture.js
// Run (attach):  frida -U TikTok -l tt_capture.js
// Then open the target video in the app and watch for ==== REQUEST ==== blocks.
//
// Goal: grab the /aweme/v1/... request — it contains iid=, device_id=, cdid=,
// openudid= in the query string. Paste those back. (The RESPONSE will look like
// binary because it's gzip'd — that's expected; we don't need it, we re-fetch the
// bit_rate ladder ourselves using the captured iid/device_id.)

function ab2str(ab) {
  var u8 = new Uint8Array(ab), s = '';
  for (var i = 0; i < u8.length; i++) {
    var c = u8[i];
    s += (c === 9 || c === 10 || c === 13 || (c >= 32 && c < 127)) ? String.fromCharCode(c) : '.';
  }
  return s;
}

// Only print traffic we care about
var FILTER = /aweme\/v1\/|tiktokv\.com|device_register|aweme_id|\/feed/;

function hookWrite(addr) {
  Interceptor.attach(addr, {
    onEnter: function (a) {
      try {
        var n = a[2].toInt32();
        if (n <= 0 || n > 300000) return;
        var s = ab2str(a[1].readByteArray(n));
        if (FILTER.test(s)) {
          console.log('\n==================== REQUEST (' + n + ' B) ====================');
          console.log(s);
        }
      } catch (e) {}
    }
  });
}

function hookRead(addr) {
  Interceptor.attach(addr, {
    onEnter: function (a) { this.buf = a[1]; },
    onLeave: function (r) {
      try {
        var n = r.toInt32();
        if (n <= 0 || n > 300000) return;
        var s = ab2str(this.buf.readByteArray(n));
        if (FILTER.test(s)) {
          console.log('\n==================== RESPONSE (' + n + ' B, may be gzip) ====================');
          console.log(s.substring(0, 1500));
        }
      } catch (e) {}
    }
  });
}

['SSL_write', 'SSL_read'].forEach(function (name) {
  var addr = Module.findExportByName('boringssl', name) || Module.findExportByName(null, name);
  console.log('[*] ' + name + ' @ ' + addr);
  if (addr) { (name === 'SSL_write' ? hookWrite : hookRead)(addr); }
});
console.log('[*] hooks installed — now open the target video in TikTok');
