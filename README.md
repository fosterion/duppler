# Duppler

A desktop tool for finding and removing duplicate photos and videos — even if the files were renamed by cloud storage.

![Screenshot](assets/screenshot1.png)

## Use case

You have two folders with overlapping content: one is a phone backup, the other is downloaded from cloud storage. The files are the same but have different names. Duppler finds matching pairs, shows a preview, and lets you delete files straight to the Recycle Bin.

Supports `.jpg` / `.jpeg` / `.mp4`.

## Install

```
pip install -r requirements.txt
```

## Run

```
python -m duppler
```

## Modes

**Two folders** — compare files across two directories (A vs B). Each duplicate pair is shown side by side with a preview. You can delete individual files or all files from one folder at once.

**One folder** — find duplicates within a single directory. Results are grouped by similarity.

Both modes support recursive scanning (include subfolders).

## Methods

**Exact hash (fast)** — groups files by size, then compares blake2b checksums. 100% accurate for byte-identical files.

**Visual similarity (slower)** — uses perceptual hashing (pHash) for photos and exact hash for video. Catches images re-compressed or stripped of metadata by cloud services.

## Other

- UI language: EN / RU (switch in the top-right corner)
- Preferences (last used folders, language) are saved to `%APPDATA%\Duppler\prefs.json`
- Deletion goes to the Windows Recycle Bin — nothing is permanently removed
