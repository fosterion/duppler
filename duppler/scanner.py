"""
Duplicate-file scanner.
Supports two strategies:
  'exact'      — blake2b hash comparison (works for any file type)
  'perceptual' — perceptual hash for JPG/JPEG, exact hash for MP4

Two scan modes:
  scan()        — compare files across two folders (A vs B)
  scan_single() — find duplicates within one folder
"""

import os
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .strings import t

SUPPORTED_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.mp4'})
IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg'})
PHASH_THRESHOLD = 10   # max Hamming distance to consider images "visually identical"


@dataclass
class FileInfo:
    path: str
    name: str
    size: int
    ext: str   # lowercase, with dot


@dataclass
class DuplicatePair:
    file_a: FileInfo
    file_b: FileInfo
    match_type: str        # 'exact' or 'perceptual'
    phash_distance: int = 0


@dataclass
class DuplicateGroup:
    files: List[FileInfo]
    match_type: str        # 'exact' or 'perceptual'
    phash_distance: int = 0   # max Hamming distance within group


# ── helpers ──────────────────────────────────────────────────────────────────

def _collect(folder: str, recursive: bool = False) -> List[FileInfo]:
    result = []
    if recursive:
        entries = (
            (os.path.join(root, name), name)
            for root, _dirs, files in os.walk(folder)
            for name in files
        )
    else:
        entries = (
            (os.path.join(folder, name), name)
            for name in os.listdir(folder)
        )
    for path, name in entries:
        ext = os.path.splitext(name)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            try:
                size = os.path.getsize(path)
                result.append(FileInfo(path=path, name=name, size=size, ext=ext))
            except OSError:
                pass
    return result


def _hash_partial(path: str) -> Optional[str]:
    try:
        h = hashlib.blake2b()
        with open(path, 'rb') as f:
            h.update(f.read(65536))
        return h.hexdigest()
    except OSError:
        return None


def _hash_full(path: str) -> Optional[str]:
    try:
        h = hashlib.blake2b()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _phash(path: str):
    """Returns imagehash.ImageHash or None."""
    try:
        import imagehash
        from PIL import Image
        return imagehash.phash(Image.open(path))
    except Exception:
        return None


# ── perceptual clustering (single-folder) ─────────────────────────────────────

def _cluster_phashes(hashes: list) -> List[DuplicateGroup]:
    """Union-find clustering: groups images within PHASH_THRESHOLD of each other."""
    n = len(hashes)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if hashes[i][1] - hashes[j][1] <= PHASH_THRESHOLD:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    buckets: dict = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(i)

    result = []
    for indices in buckets.values():
        if len(indices) < 2:
            continue
        group_files = [hashes[i][0] for i in indices]
        max_dist = max(
            hashes[i][1] - hashes[j][1]
            for i in indices for j in indices if i < j
        )
        result.append(DuplicateGroup(
            files=group_files, match_type='perceptual', phash_distance=max_dist,
        ))
    return result


# ── exact matching ────────────────────────────────────────────────────────────

def _scan_exact(
    files_a: List[FileInfo],
    files_b: List[FileInfo],
    result_cb: Callable,
    progress_cb: Callable,
    cancel: threading.Event,
    progress: list,   # [done]
) -> None:
    if not files_a or not files_b:
        # Still advance progress counter for skipped files
        progress[0] += len(files_b)
        return

    by_size: dict = {}
    for f in files_a:
        by_size.setdefault(f.size, []).append(f)

    partial_a: dict = {}
    partial_b: dict = {}
    full_a: dict = {}
    full_b: dict = {}

    for fb in files_b:
        if cancel.is_set():
            return

        progress[0] += 1
        progress_cb(progress[0], fb.name)

        candidates = by_size.get(fb.size)
        if not candidates:
            continue

        if fb.path not in partial_b:
            partial_b[fb.path] = _hash_partial(fb.path)
        hb = partial_b[fb.path]
        if hb is None:
            continue

        for fa in candidates:
            if cancel.is_set():
                return

            if fa.path not in partial_a:
                partial_a[fa.path] = _hash_partial(fa.path)
            ha = partial_a[fa.path]
            if ha != hb:
                continue

            # Partial hashes match → full hash
            if fa.path not in full_a:
                full_a[fa.path] = _hash_full(fa.path)
            if fb.path not in full_b:
                full_b[fb.path] = _hash_full(fb.path)

            ha_full = full_a[fa.path]
            hb_full = full_b[fb.path]
            if ha_full and hb_full and ha_full == hb_full:
                result_cb(DuplicatePair(file_a=fa, file_b=fb, match_type='exact'))


# ── perceptual matching ───────────────────────────────────────────────────────

def _scan_perceptual(
    images_a: List[FileInfo],
    images_b: List[FileInfo],
    result_cb: Callable,
    progress_cb: Callable,
    cancel: threading.Event,
    progress: list,
) -> None:
    if not images_a or not images_b:
        progress[0] += len(images_a) + len(images_b)
        return

    hashes_a = []
    for fa in images_a:
        if cancel.is_set():
            return
        h = _phash(fa.path)
        if h is not None:
            hashes_a.append((fa, h))
        progress[0] += 1
        progress_cb(progress[0], fa.name)

    hashes_b = []
    for fb in images_b:
        if cancel.is_set():
            return
        h = _phash(fb.path)
        if h is not None:
            hashes_b.append((fb, h))
        progress[0] += 1
        progress_cb(progress[0], fb.name)

    if not hashes_a or not hashes_b:
        return

    progress_cb(progress[0], t('scan_comparing'))

    for fa, ha in hashes_a:
        if cancel.is_set():
            return
        for fb, hb in hashes_b:
            dist = ha - hb
            if dist <= PHASH_THRESHOLD:
                result_cb(DuplicatePair(
                    file_a=fa, file_b=fb,
                    match_type='perceptual',
                    phash_distance=dist,
                ))


# ── single-folder scanning ────────────────────────────────────────────────────

def _scan_single_exact(
    files: List[FileInfo],
    result_cb: Callable,
    progress_cb: Callable,
    cancel: threading.Event,
    progress: list,
) -> None:
    by_size: dict = {}
    for f in files:
        by_size.setdefault(f.size, []).append(f)

    multi_sizes = {size for size, grp in by_size.items() if len(grp) > 1}

    by_partial: dict = {}
    for f in files:
        if cancel.is_set():
            return
        progress[0] += 1
        progress_cb(progress[0], f.name)
        if f.size not in multi_sizes:
            continue
        h = _hash_partial(f.path)
        if h:
            by_partial.setdefault(h, []).append(f)

    by_full: dict = {}
    for grp in by_partial.values():
        if len(grp) < 2:
            continue
        for f in grp:
            if cancel.is_set():
                return
            fh = _hash_full(f.path)
            if fh:
                by_full.setdefault(fh, []).append(f)

    for grp in by_full.values():
        if len(grp) >= 2:
            result_cb(DuplicateGroup(files=list(grp), match_type='exact'))


def _scan_single_perceptual(
    files: List[FileInfo],
    result_cb: Callable,
    progress_cb: Callable,
    cancel: threading.Event,
    progress: list,
) -> None:
    mp4s = [f for f in files if f.ext == '.mp4']
    imgs = [f for f in files if f.ext in IMAGE_EXTENSIONS]

    _scan_single_exact(mp4s, result_cb, progress_cb, cancel, progress)
    if cancel.is_set():
        return

    hashes = []
    for f in imgs:
        if cancel.is_set():
            return
        h = _phash(f.path)
        if h is not None:
            hashes.append((f, h))
        progress[0] += 1
        progress_cb(progress[0], f.name)

    for group in _cluster_phashes(hashes):
        if cancel.is_set():
            return
        result_cb(group)


# ── public API ────────────────────────────────────────────────────────────────

def scan(
    folder_a: str,
    folder_b: str,
    strategy: str,                                  # 'exact' | 'perceptual'
    progress_cb: Callable[[int, int, str], None],   # (done, total, current_name)
    result_cb: Callable[[DuplicatePair], None],
    done_cb: Callable[[int], None],                 # (total_found)
    cancel: threading.Event,
    recursive: bool = False,
) -> None:
    files_a = _collect(folder_a, recursive)
    files_b = _collect(folder_b, recursive)
    total = len(files_a) + len(files_b)

    progress_cb(0, total, t('scan_file_count2', a=len(files_a), b=len(files_b)))

    progress = [0]
    found = [0]

    def _result(pair: DuplicatePair):
        found[0] += 1
        result_cb(pair)

    def _prog(done: int, name: str):
        progress_cb(done, total, name)

    if strategy == 'exact':
        _scan_exact(files_a, files_b, _result, _prog, cancel, progress)
    else:
        mp4_a = [f for f in files_a if f.ext == '.mp4']
        mp4_b = [f for f in files_b if f.ext == '.mp4']
        jpg_a = [f for f in files_a if f.ext in IMAGE_EXTENSIONS]
        jpg_b = [f for f in files_b if f.ext in IMAGE_EXTENSIONS]

        _scan_exact(mp4_a, mp4_b, _result, _prog, cancel, progress)
        if not cancel.is_set():
            _scan_perceptual(jpg_a, jpg_b, _result, _prog, cancel, progress)

    done_cb(found[0] if not cancel.is_set() else 0)


def scan_single(
    folder: str,
    strategy: str,                                   # 'exact' | 'perceptual'
    progress_cb: Callable[[int, int, str], None],    # (done, total, current_name)
    result_cb: Callable[[DuplicateGroup], None],
    done_cb: Callable[[int], None],                  # (total_groups_found)
    cancel: threading.Event,
    recursive: bool = False,
) -> None:
    files = _collect(folder, recursive)
    total = len(files)

    progress_cb(0, total, t('scan_file_count', n=total))

    progress = [0]
    found = [0]

    def _result(group: DuplicateGroup) -> None:
        found[0] += 1
        result_cb(group)

    def _prog(done: int, name: str) -> None:
        progress_cb(done, total, name)

    if strategy == 'exact':
        _scan_single_exact(files, _result, _prog, cancel, progress)
    else:
        _scan_single_perceptual(files, _result, _prog, cancel, progress)

    done_cb(found[0] if not cancel.is_set() else 0)
