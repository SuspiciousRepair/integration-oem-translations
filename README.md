# OEM translations for the Geely EX2 / Geometry E head unit

Better text for the car's own apps (Energy, Wi-Fi and Bluetooth, Settings) in
Portuguese, English, Spanish and Thai. The factory apps show some lines in
Chinese, some in English inside other languages, and some with the wrong
meaning (for example "Saúde" where the car means "Healthy").

This repo holds **text only**. It is used by the **OEM translations**
integration of [Drive Assist](https://github.com/SuspiciousRepair/drive_assist)
(Config > Integrations).

## How the car uses it

Nothing is downloaded. Drive Assist builds the text into its helper app, from
one commit of this repo (`tools/pin-oem-translations.sh` in Drive Assist), so
a change here reaches cars with the next Drive Assist release.

The car checks two things, and trusts nothing else:

1. **The known patch.** Only the text built into the signed helper app.
2. **The known file.** Before patching, the car hashes its own copy of each
   app. Only an apk whose SHA-256 is in `apk_sha256` is patched. Any other
   build of the app (for example after a system update) is left alone.

Then:

- The car makes a patched copy of each known app. Only the app's text table
  (`resources.arsc`) changes; the code is not touched.
- The copy is put in front of the original with a bind mount. The original
  file in `/system` is never changed.
- **Remove** takes the copies away. A reboot drops them too; the integration
  makes them again, with the same two checks, while it is on.
- If a patched app crashes, the car removes that app's copy by itself.

Today the hashes are the apps of system 1111 (`SW0E22H0128H111100000`).

## Files

- `manifest.json`: the apps to patch, the file for each, and `apk_sha256`: the SHA-256 of the factory apk the text was
  made for (`adb shell sha256sum /system/app/AutoEnergy/AutoEnergy.apk`, with
  nothing mounted over it). The car hashes its own apk first; an app whose
  hash is not listed is left untouched.
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
