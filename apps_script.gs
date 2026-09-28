/**
 * SKRIP PENYIMPAN ABSENSI QR
 * Tempel di Google Apps Script (script.google.com), isi SHEET_ID dan PIN,
 * lalu Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
 * Salin Web app URL ke Secrets Streamlit: APPS_SCRIPT_URL.
 */
var SHEET_ID = "GANTI_DENGAN_ID_SHEET_ANDA";
var SHEET_NAMA = "Absensi";
var PIN = "ebis2026";   // HARUS sama dengan DOSEN_PIN di Streamlit

function _sheet() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ss.getSheetByName(SHEET_NAMA);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAMA);
    sh.appendRow(["waktu", "mk", "pertemuan", "npm", "nama", "status"]);
  }
  return sh;
}

function _json(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

function _cariBaris(sh, mk, p, npm) {
  var v = sh.getDataRange().getValues();
  for (var i = 1; i < v.length; i++) {
    if (String(v[i][1]) == mk && String(v[i][2]) == String(p) && String(v[i][3]) == String(npm)) {
      return i + 1; // nomor baris di sheet
    }
  }
  return -1;
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000); // cegah absen ganda saat banyak yang menekan bersamaan
  try {
    var d = JSON.parse(e.postData.contents);
    var sh = _sheet();
    var baris = [d.waktu, d.mk, d.pertemuan, "'" + d.npm, d.nama, d.status];

    if (d.aksi === "absen") {
      if (_cariBaris(sh, d.mk, d.pertemuan, d.npm) > 0) return _json({status: "duplikat"});
      sh.appendRow(baris);
      return _json({status: "ok"});
    }
    if (d.aksi === "set") {
      if (String(d.pin) !== PIN) return _json({status: "tolak", pesan: "PIN salah"});
      var r = _cariBaris(sh, d.mk, d.pertemuan, d.npm);
      if (r > 0) sh.getRange(r, 1, 1, 6).setValues([baris]);
      else sh.appendRow(baris);
      return _json({status: "ok", pesan: "Status diperbarui."});
    }
    return _json({status: "error", pesan: "aksi tidak dikenal"});
  } catch (err) {
    return _json({status: "error", pesan: String(err)});
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  var p = (e && e.parameter) ? e.parameter : {};
  if (p.aksi === "rekap") {
    if (String(p.pin) !== PIN) return _json({status: "tolak"});
    var v = _sheet().getDataRange().getValues();
    var head = v.shift();
    return _json(v.map(function (r) {
      var o = {}; head.forEach(function (h, i) { o[h] = String(r[i]); }); return o;
    }));
  }
  return ContentService.createTextOutput("Layanan Absensi QR aktif.");
}
