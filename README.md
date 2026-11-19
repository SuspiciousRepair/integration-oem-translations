# OEM translations for the Geely EX2 / Geometry E head unit

Better text for the car's own apps (Energy, Wi-Fi and Bluetooth, Settings) in
Portuguese, English, Spanish and Thai. The factory apps show some lines in
Chinese, some in English inside other languages, and some with the wrong
meaning (for example "Saúde" where the car means "Healthy").

This repo holds **text only**. It is used by the **OEM translations**
integration of [Drive Assist](https://github.com/SuspiciousRepair/drive_assist)
(Config > Integrations).

## How the car uses it

1. In Drive Assist, tap **Install**. The car downloads `manifest.json` and the
   files in `apps/` from this repo.
2. The car makes a patched copy of each listed app, from the copy it has.
   Only the app's text table (`resources.arsc`) changes. The code is not
   touched.
3. The copy is put in front of the original with a bind mount. The original
   file in `/system` is never changed.
4. **Remove** takes the copies away. A reboot also gives the car its factory
   text back until the integration puts the copies in front again.
5. If a patched app crashes, the car removes that app's copy by itself.

## Files

- `manifest.json`: the apps to patch, and the file for each.
- `apps/<package>.json`: one object per language, `{"pt": {"string_name": "text"}, ...}`.
  Each language goes in its own slot: Portuguese in `pt`, English in `en`.
  The default (fallback) slot is never changed. A line the app does not have
  is skipped.

## Rules for a change

- Each language in its own slot. Never put one language into another's slot.
- Fix the meaning, not only the Chinese. Say what the line means on screen.
- Keep the length near the original. The car's screens do not wrap long text well.
- Do not add placeholders (`%s`, `%d`) that the original line does not have.
  Do not remove the ones it has.

## Tools (for authors, not used by the car)

Python 3, no extra packages:

```bash
python3 tools/scan_arsc.py App.apk pt en es th       # lines that still show Chinese
python3 tools/scan_untranslated.py App.apk           # lines left in English in pt/es/th
python3 tools/patch_arsc.py App.apk apps/<pkg>.json out.apk   # make a patched copy to test
```

Pull an app from the car with `adb pull /system/app/AutoEnergy/AutoEnergy.apk`.

## License

GPL-3.0, the same as Drive Assist. The text in `apps/` is our own translation
work. No file from the car is stored here.
