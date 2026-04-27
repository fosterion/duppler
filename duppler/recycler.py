"""
Send a file to the Windows Recycle Bin via SHFileOperationW (ctypes).

We call the Windows API directly instead of relying on send2trash, because
send2trash tries to convert paths to 8.3 short names via GetShortPathNameW,
which fails on modern Windows when 8.3 name generation is disabled — e.g.
for paths containing Cyrillic or other non-ASCII characters.
"""

import ctypes
import ctypes.wintypes
import os


_shell32 = ctypes.windll.shell32


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ('hwnd',                  ctypes.wintypes.HWND),
        ('wFunc',                 ctypes.wintypes.UINT),
        ('pFrom',                 ctypes.c_wchar_p),
        ('pTo',                   ctypes.c_wchar_p),
        ('fFlags',                ctypes.c_ushort),
        ('fAnyOperationsAborted', ctypes.wintypes.BOOL),
        ('hNameMappings',         ctypes.c_void_p),
        ('lpszProgressTitle',     ctypes.c_wchar_p),
    ]


_FO_DELETE         = 0x0003
_FOF_ALLOWUNDO     = 0x0040   # → Recycle Bin instead of permanent delete
_FOF_NOCONFIRMATION = 0x0010
_FOF_NOERRORUI     = 0x0400
_FOF_SILENT        = 0x0004


def send_to_trash(path: str) -> None:
    """
    Move *path* to the Windows Recycle Bin.
    Raises OSError on failure.
    """
    path = os.path.abspath(path)

    # SHFileOperationW requires a double-null-terminated string.
    # We build a c_wchar buffer with an explicit extra null at the end.
    path_buf = ctypes.create_unicode_buffer(path + '\0')

    op = _SHFILEOPSTRUCTW()
    op.hwnd   = 0
    op.wFunc  = _FO_DELETE
    op.pFrom  = ctypes.cast(path_buf, ctypes.c_wchar_p)
    op.pTo    = None
    op.fFlags = _FOF_ALLOWUNDO | _FOF_NOCONFIRMATION | _FOF_NOERRORUI | _FOF_SILENT
    op.fAnyOperationsAborted = False
    op.hNameMappings         = None
    op.lpszProgressTitle     = None

    result = _shell32.SHFileOperationW(ctypes.byref(op))
    if result != 0:
        raise OSError(f'SHFileOperationW вернул код {result:#x}\nФайл: {path}')
