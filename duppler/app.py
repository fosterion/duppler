"""Duppler — duplicate-file finder. UI entry point."""

import sys
import os
import json
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .strings import STRINGS, t, set_lang, get_lang
from . import scanner, recycler


# ── prefs ─────────────────────────────────────────────────────────────────────

# prefs.json lives at the repo root (one level above the package directory)
_PREFS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'prefs.json',
)


def _load_prefs() -> dict:
    try:
        with open(_PREFS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_prefs(data: dict) -> None:
    try:
        with open(_PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# Load saved language before anything is rendered
_prefs_cache = _load_prefs()
if _prefs_cache.get('lang') in ('ru', 'en'):
    set_lang(_prefs_cache['lang'])


# ── dependency check ──────────────────────────────────────────────────────────

def _check_deps() -> None:
    missing = []
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append('Pillow')

    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(t('dep_title'), t('dep_msg', pkgs=' '.join(missing)))
        sys.exit(1)


_check_deps()


# ── tooltip ──────────────────────────────────────────────────────────────────

class Tooltip:
    """Shows a tooltip after 900 ms of hovering over a widget."""

    def __init__(self, widget: tk.Widget, text: str):
        self._widget = widget
        self._text   = text
        self._win    = None
        self._job    = None
        widget.bind('<Enter>',    self._on_enter, add='+')
        widget.bind('<Leave>',    self._on_leave, add='+')
        widget.bind('<Button>',   self._on_leave, add='+')

    def _on_enter(self, _event) -> None:
        self._job = self._widget.after(900, self._show)

    def _on_leave(self, _event) -> None:
        if self._job:
            self._widget.after_cancel(self._job)
            self._job = None
        self._hide()

    def _show(self) -> None:
        if self._win:
            return
        x = self._widget.winfo_rootx() + 10
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._win = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        tk.Label(
            tw, text=self._text, justify='left',
            bg='#ffffdd', fg='#222222',
            font=('Segoe UI', 8),
            relief='solid', bd=1,
            padx=6, pady=4,
        ).pack()

    def _hide(self) -> None:
        if self._win:
            self._win.destroy()
            self._win = None


# ── constants ─────────────────────────────────────────────────────────────────

THUMB_W, THUMB_H = 110, 110
PAGE_SIZE = 100

BG_EVEN = '#f7f7f7'
BG_ODD  = '#ffffff'

CARD_A_BG     = '#ddeeff'
CARD_A_BORDER = '#99bbdd'
CARD_A_HEADER = '#336699'

CARD_B_BG     = '#fff3dd'
CARD_B_BORDER = '#ddbb88'
CARD_B_HEADER = '#996633'

BADGE_EXACT = '#27ae60'
BADGE_PERC  = '#e67e22'

DEL_BG  = '#e74c3c'
DEL_FG  = '#ffffff'
DEL_ACT = '#c0392b'


# ── utilities ─────────────────────────────────────────────────────────────────

def _fmt_size(n: int) -> str:
    if n < 1024:
        return f'{n} {"Б" if get_lang() == "ru" else "B"}'
    elif n < 1024 ** 2:
        return f'{n / 1024:.1f} KB'
    elif n < 1024 ** 3:
        return f'{n / 1024 ** 2:.1f} MB'
    else:
        return f'{n / 1024 ** 3:.2f} GB'


def _short_path(path: str, maxlen: int = 55) -> str:
    if len(path) <= maxlen:
        return path
    drive = os.path.splitdrive(path)[0]
    name  = os.path.basename(path)
    return drive + os.sep + '…' + os.sep + name


# ── FolderPicker ──────────────────────────────────────────────────────────────

class FolderPicker(ttk.LabelFrame):
    def __init__(self, parent, label_key: str, on_change=None, **kw):
        super().__init__(parent, text=t(label_key), **kw)
        self._label_key = label_key
        self._var = tk.StringVar()
        self._on_change = on_change
        ttk.Entry(self, textvariable=self._var, state='readonly').pack(
            side='left', fill='x', expand=True, padx=5, pady=5
        )
        self._btn = ttk.Button(self, text=t('browse'), command=self._browse, width=10)
        self._btn.pack(side='right', padx=(0, 5), pady=5)

    def _browse(self) -> None:
        initial = self._var.get() or '/'
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self._var.set(path)
            if self._on_change:
                self._on_change()

    def get(self) -> str:
        return self._var.get()

    def set(self, path: str) -> None:
        self._var.set(path)

    def update_lang(self) -> None:
        self.config(text=t(self._label_key))
        self._btn.config(text=t('browse'))


# ── PairRow ───────────────────────────────────────────────────────────────────

class PairRow(tk.Frame):
    def __init__(self, parent, pair: scanner.DuplicatePair, index: int, on_delete, **kw):
        bg = BG_EVEN if index % 2 == 0 else BG_ODD
        super().__init__(parent, bg=bg, **kw)
        self.pair = pair
        self._img_ref_a = None
        self._img_ref_b = None

        # badge
        if pair.match_type == 'exact':
            badge_txt, badge_clr = t('badge_exact'), BADGE_EXACT
        else:
            badge_txt = t('badge_perceptual', d=pair.phash_distance)
            badge_clr = BADGE_PERC

        tk.Label(self, text=badge_txt, bg=badge_clr, fg='white',
                 font=('Segoe UI', 7), anchor='w').pack(fill='x', side='top')

        # body
        body = tk.Frame(self, bg=bg)
        body.pack(fill='x', side='top', padx=6, pady=6)

        cards = tk.Frame(body, bg=bg)
        cards.pack(fill='both', expand=True)
        cards.columnconfigure(0, weight=1, uniform='col')
        cards.columnconfigure(2, weight=1, uniform='col')

        lbl_a = self._build_card(
            cards, pair.file_a,
            t('card_a_header'), CARD_A_BG, CARD_A_BORDER, CARD_A_HEADER,
            col=0, on_del=lambda: on_delete(self, 'a'),
        )
        tk.Frame(cards, bg='#dddddd', width=1).grid(
            row=0, column=1, sticky='ns', padx=4, pady=4
        )
        lbl_b = self._build_card(
            cards, pair.file_b,
            t('card_b_header'), CARD_B_BG, CARD_B_BORDER, CARD_B_HEADER,
            col=2, on_del=lambda: on_delete(self, 'b'),
        )

        self._start_thumb(pair.file_a, lbl_a, 'a')
        self._start_thumb(pair.file_b, lbl_b, 'b')

    @staticmethod
    def _build_card(parent, fi: scanner.FileInfo,
                    header: str, bg: str, border: str, hdr_fg: str,
                    col: int, on_del) -> tk.Label:
        outer = tk.Frame(parent, bg=border, padx=1, pady=1)
        outer.grid(row=0, column=col, sticky='nsew', pady=2)
        card = tk.Frame(outer, bg=bg, padx=8, pady=6)
        card.pack(fill='both', expand=True)

        tk.Label(card, text=header, bg=bg, fg=hdr_fg,
                 font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        tk.Frame(card, bg=border, height=1).pack(fill='x', pady=(2, 6))

        pb = tk.Frame(card, bg='#bbbbbb', padx=1, pady=1)
        pb.pack(pady=(0, 6))
        pbg = tk.Frame(pb, bg='white', width=THUMB_W + 4, height=THUMB_H + 4)
        pbg.pack()
        pbg.pack_propagate(False)
        thumb_lbl = tk.Label(pbg, bg='white', anchor='center')
        thumb_lbl.place(relx=0.5, rely=0.5, anchor='center')

        tk.Label(card, text=fi.name, bg=bg, anchor='w',
                 font=('Segoe UI', 9, 'bold'),
                 wraplength=240, justify='left').pack(anchor='w')
        tk.Label(card, text=_fmt_size(fi.size), bg=bg, anchor='w',
                 font=('Segoe UI', 8), fg='#555555').pack(anchor='w')
        short = _short_path(fi.path)
        path_lbl = tk.Label(card, text=short, bg=bg, anchor='w',
                            font=('Segoe UI', 7), fg='#999999')
        path_lbl.pack(anchor='w', pady=(1, 6))
        if short != fi.path:
            Tooltip(path_lbl, fi.path)

        btn_row = tk.Frame(card, bg=bg)
        btn_row.pack(anchor='w', pady=(0, 2))

        tk.Button(
            btn_row, text=t('delete'), command=on_del,
            bg=DEL_BG, fg=DEL_FG,
            activebackground=DEL_ACT, activeforeground=DEL_FG,
            font=('Segoe UI', 8, 'bold'),
            relief='flat', cursor='hand2', bd=0,
            padx=10, pady=4,
        ).pack(side='left')

        tk.Button(
            btn_row, text=t('show_in_explorer'),
            command=lambda p=fi.path: subprocess.run(
                ['explorer', '/select,', os.path.normpath(p)]
            ),
            bg=bg, fg='#336699',
            activebackground=bg, activeforeground='#1a4a8a',
            font=('Segoe UI', 8, 'underline'),
            relief='flat', cursor='hand2', bd=0,
            padx=8, pady=4,
        ).pack(side='left')

        return thumb_lbl

    def _start_thumb(self, fi: scanner.FileInfo, lbl: tk.Label, slot: str) -> None:
        if fi.ext in scanner.IMAGE_EXTENSIONS:
            threading.Thread(
                target=self._load_thumb_async,
                args=(fi.path, lbl, slot),
                daemon=True,
            ).start()
        else:
            lbl.config(text='🎬', font=('Segoe UI', 26))

    def _load_thumb_async(self, path: str, lbl: tk.Label, slot: str) -> None:
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.after(0, self._apply_thumb, photo, lbl, slot)
        except Exception:
            pass

    def _apply_thumb(self, photo, lbl: tk.Label, slot: str) -> None:
        if slot == 'a':
            self._img_ref_a = photo
        else:
            self._img_ref_b = photo
        lbl.config(image=photo, text='')


# ── ResultsPanel ──────────────────────────────────────────────────────────────

class ResultsPanel(ttk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._all_pairs: list = []
        self._rows: list      = []
        self._scan_done       = False
        self._build()

    def _build(self) -> None:
        self._hdr = ttk.Frame(self)
        self._hdr.pack(side='top', fill='x', padx=10, pady=(6, 2))
        self._count_lbl = ttk.Label(self._hdr, text='', font=('Segoe UI', 9))
        self._count_lbl.pack(side='left')

        self._del_bar = tk.Frame(self, bg=self.winfo_toplevel().cget('bg'))
        self._del_bar.columnconfigure(0, weight=1, uniform='dcol')
        self._del_bar.columnconfigure(1, weight=1, uniform='dcol')
        self._del_a_btn = tk.Button(
            self._del_bar, text=t('del_all_a'), command=lambda: self._delete_all('a'),
            bg=CARD_A_HEADER, fg='white',
            activebackground='#1e4d80', activeforeground='white',
            font=('Segoe UI', 8, 'bold'),
            relief='flat', cursor='hand2', bd=0,
            padx=10, pady=5,
        )
        self._del_a_btn.grid(row=0, column=0, sticky='ew', padx=(10, 4), pady=(0, 4))
        self._del_b_btn = tk.Button(
            self._del_bar, text=t('del_all_b'), command=lambda: self._delete_all('b'),
            bg=CARD_B_HEADER, fg='white',
            activebackground='#7a5228', activeforeground='white',
            font=('Segoe UI', 8, 'bold'),
            relief='flat', cursor='hand2', bd=0,
            padx=10, pady=5,
        )
        self._del_b_btn.grid(row=0, column=1, sticky='ew', padx=(4, 10), pady=(0, 4))

        body = ttk.Frame(self)
        body.pack(fill='both', expand=True)

        self._canvas = tk.Canvas(body, highlightthickness=0, bg=BG_ODD)
        sb = ttk.Scrollbar(body, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)

        self._inner = tk.Frame(self._canvas, bg=BG_ODD)
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor='nw')

        self._inner.bind('<Configure>', lambda _: self._canvas.configure(
            scrollregion=self._canvas.bbox('all')
        ))
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfig(
            self._win, width=e.width
        ))
        self._canvas.bind('<Enter>',
            lambda _: self._canvas.bind_all('<MouseWheel>', self._on_wheel))
        self._canvas.bind('<Leave>',
            lambda _: self._canvas.unbind_all('<MouseWheel>'))

        self._load_btn = tk.Button(
            self._inner, text='', command=self._load_more,
            bg='#4a90d9', fg='white',
            activebackground='#357abd', activeforeground='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat', cursor='hand2', bd=0,
            padx=20, pady=10,
        )

    def _on_wheel(self, event) -> None:
        self._canvas.yview_scroll(int(-1 * event.delta / 120), 'units')

    # ── public ────────────────────────────────────────────────────

    def add_pair(self, pair: scanner.DuplicatePair) -> None:
        self._all_pairs.append(pair)
        if len(self._rows) < PAGE_SIZE:
            self._render_one(pair)
        self._refresh()

    def mark_scan_done(self) -> None:
        self._scan_done = True
        self._refresh()

    def clear(self) -> None:
        self._load_btn.pack_forget()
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._all_pairs.clear()
        self._scan_done = False
        self._refresh()

    def set_header(self, text: str) -> None:
        self._count_lbl.config(text=text)

    def rebuild_rows(self) -> None:
        shown = len(self._rows)
        self._load_btn.pack_forget()
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        for pair in self._all_pairs[:shown]:
            self._render_one(pair)
        self._del_a_btn.config(text=t('del_all_a'))
        self._del_b_btn.config(text=t('del_all_b'))
        self._refresh()

    def _delete_all(self, which: str) -> None:
        paths = list(dict.fromkeys(
            p.file_a.path if which == 'a' else p.file_b.path
            for p in self._all_pairs
            if os.path.exists(p.file_a.path if which == 'a' else p.file_b.path)
        ))
        if not paths:
            return
        label = 'A' if which == 'a' else 'B'
        if not messagebox.askyesno(
            t('dlg_del_all_title'),
            t('dlg_del_all_msg', n=len(paths), which=label),
        ):
            return
        errors = []
        for path in paths:
            try:
                recycler.send_to_trash(path)
            except Exception as exc:
                errors.append(f'{path}\n{exc}')
        if errors:
            messagebox.showerror(t('dlg_err_title'), '\n\n'.join(errors[:5]))
        # Remove pairs whose deleted-side file was in our list
        path_set = set(paths)
        surviving = [
            p for p in self._all_pairs
            if (p.file_a.path if which == 'a' else p.file_b.path) not in path_set
        ]
        self._all_pairs[:] = surviving
        self._load_btn.pack_forget()
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        for pair in self._all_pairs[:PAGE_SIZE]:
            self._render_one(pair)
        self._refresh()

    # ── internals ─────────────────────────────────────────────────

    def _render_one(self, pair: scanner.DuplicatePair) -> None:
        self._load_btn.pack_forget()
        row = PairRow(self._inner, pair, len(self._rows), on_delete=self._on_delete)
        row.pack(fill='x', pady=(0, 2))
        self._rows.append(row)

    def _load_more(self) -> None:
        start = len(self._rows)
        end   = min(start + PAGE_SIZE, len(self._all_pairs))
        for i in range(start, end):
            self._render_one(self._all_pairs[i])
        self._refresh()
        self._canvas.yview_moveto(0.0)

    def _on_delete(self, row: 'PairRow', which: str) -> None:
        path = row.pair.file_a.path if which == 'a' else row.pair.file_b.path
        if not os.path.exists(path):
            self._remove_row(row)
            return
        try:
            recycler.send_to_trash(path)
            self._remove_row(row)
        except Exception as exc:
            messagebox.showerror(t('dlg_err_title'), t('dlg_err_msg', path=path, exc=exc))

    def _remove_row(self, row: 'PairRow') -> None:
        if row.pair in self._all_pairs:
            self._all_pairs.remove(row.pair)
        if row in self._rows:
            self._rows.remove(row)
        row.pack_forget()
        row.destroy()
        while len(self._rows) < PAGE_SIZE and len(self._rows) < len(self._all_pairs):
            self._render_one(self._all_pairs[len(self._rows)])
        self._refresh()

    def _refresh(self) -> None:
        shown  = len(self._rows)
        total  = len(self._all_pairs)
        unseen = total - shown

        if total == 0:
            self._count_lbl.config(text=t('no_dupes'))
            self._del_bar.pack_forget()
        else:
            if unseen > 0:
                self._count_lbl.config(text=t('shown_of', shown=shown, total=total))
            else:
                self._count_lbl.config(text=t('dupes_count', n=total))
            self._del_bar.pack(fill='x', after=self._hdr)

        self._load_btn.pack_forget()
        if unseen > 0 and self._scan_done:
            next_n = min(unseen, PAGE_SIZE)
            self._load_btn.config(text=t('load_more_btn', next_n=next_n, rem=unseen))
            self._load_btn.pack(pady=12)


# ── App ───────────────────────────────────────────────────────────────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('Duppler')
        root.minsize(900, 600)
        root.geometry('1160x760')

        style = ttk.Style()
        if 'vista' in style.theme_names():
            style.theme_use('vista')

        self._q: queue.Queue = queue.Queue()
        self._cancel = threading.Event()
        self._scanning = False

        self._build_ui()
        self._restore_folders()
        root.after(50, self._poll)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        top.pack(fill='x')

        row1 = ttk.Frame(top)
        row1.pack(fill='x')

        self._pick_a = FolderPicker(row1, 'folder_a', on_change=self._save_prefs)
        self._pick_a.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self._pick_b = FolderPicker(row1, 'folder_b', on_change=self._save_prefs)
        self._pick_b.pack(side='left', fill='x', expand=True, padx=(0, 10))

        lang_frame = tk.Frame(row1, bg=self.root.cget('bg'))
        lang_frame.pack(side='right', anchor='center')
        self._btn_en = self._lang_btn(lang_frame, 'EN', lambda: self._switch_lang('en'))
        self._btn_en.pack(side='left')
        self._btn_ru = self._lang_btn(lang_frame, 'RU', lambda: self._switch_lang('ru'))
        self._btn_ru.pack(side='left', padx=(2, 0))
        self._update_lang_btns()

        row2 = ttk.Frame(top)
        row2.pack(fill='x', pady=(8, 4))

        self._method_lbl = ttk.Label(row2, text=t('method_label'))
        self._method_lbl.pack(side='left')

        self._strategy = tk.StringVar(value='exact')
        self._radio_exact = ttk.Radiobutton(
            row2, text=t('exact_radio'), variable=self._strategy, value='exact',
        )
        self._radio_exact.pack(side='left', padx=(4, 14))
        self._radio_perc = ttk.Radiobutton(
            row2, text=t('perceptual_radio'), variable=self._strategy, value='perceptual',
        )
        self._radio_perc.pack(side='left', padx=(0, 14))

        self._recursive = tk.BooleanVar(value=False)
        self._recursive_chk = ttk.Checkbutton(
            row2, text=t('recursive_check'), variable=self._recursive,
        )
        self._recursive_chk.pack(side='left', padx=(0, 14))

        self._scan_btn = ttk.Button(row2, text=t('find_btn'), command=self._toggle_scan)
        self._scan_btn.pack(side='right')

        prog_row = ttk.Frame(top)
        prog_row.pack(fill='x', pady=(2, 0))
        self._progress = ttk.Progressbar(prog_row, maximum=100)
        self._progress.pack(side='left', fill='x', expand=True)
        self._status_lbl = ttk.Label(prog_row, text='', width=40, anchor='e')
        self._status_lbl.pack(side='right', padx=(8, 0))

        ttk.Separator(self.root).pack(fill='x')

        self._results = ResultsPanel(self.root)
        self._results.pack(fill='both', expand=True)

    @staticmethod
    def _lang_btn(parent, text: str, cmd) -> tk.Button:
        return tk.Button(
            parent, text=text, command=cmd,
            font=('Segoe UI', 8, 'bold'),
            relief='flat', cursor='hand2', bd=0,
            padx=8, pady=3,
        )

    def _update_lang_btns(self) -> None:
        active   = dict(bg='#2c3e50', fg='white',
                        activebackground='#34495e', activeforeground='white')
        inactive = dict(bg='#dce1e7', fg='#555555',
                        activebackground='#c8cfd8', activeforeground='#333333')
        self._btn_en.config(**(active if get_lang() == 'en' else inactive))
        self._btn_ru.config(**(active if get_lang() == 'ru' else inactive))

    def _switch_lang(self, lang: str) -> None:
        if lang == get_lang():
            return
        set_lang(lang)
        self._update_lang_btns()
        self._apply_lang()
        self._save_prefs()

    def _apply_lang(self) -> None:
        self._pick_a.update_lang()
        self._pick_b.update_lang()
        self._method_lbl.config(text=t('method_label'))
        self._radio_exact.config(text=t('exact_radio'))
        self._radio_perc.config(text=t('perceptual_radio'))
        self._recursive_chk.config(text=t('recursive_check'))
        if not self._scanning:
            self._scan_btn.config(text=t('find_btn'))
        self._results.rebuild_rows()

    def _restore_folders(self) -> None:
        if _prefs_cache.get('folder_a') and os.path.isdir(_prefs_cache['folder_a']):
            self._pick_a.set(_prefs_cache['folder_a'])
        if _prefs_cache.get('folder_b') and os.path.isdir(_prefs_cache['folder_b']):
            self._pick_b.set(_prefs_cache['folder_b'])

    def _save_prefs(self) -> None:
        _save_prefs({
            'folder_a': self._pick_a.get(),
            'folder_b': self._pick_b.get(),
            'lang':     get_lang(),
        })

    def _toggle_scan(self) -> None:
        if self._scanning:
            self._cancel.set()
            self._scan_btn.config(state='disabled')
            return

        a = self._pick_a.get()
        b = self._pick_b.get()

        if not a or not b:
            messagebox.showwarning(t('dlg_pick_title'), t('dlg_pick_msg'))
            return
        if not os.path.isdir(a):
            messagebox.showwarning(t('dlg_dir_title'), t('dlg_dir_msg', path=a))
            return
        if not os.path.isdir(b):
            messagebox.showwarning(t('dlg_dir_title'), t('dlg_dir_msg', path=b))
            return
        if os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b)):
            messagebox.showwarning(t('dlg_same_title'), t('dlg_same_msg'))
            return

        self._results.clear()
        self._cancel.clear()
        self._scanning = True
        self._scan_btn.config(text=t('cancel_btn'))
        self._btn_en.config(state='disabled')
        self._btn_ru.config(state='disabled')
        self._progress.config(value=0)
        self._status_lbl.config(text='')
        self._results.set_header(t('scanning'))

        threading.Thread(
            target=scanner.scan,
            args=(a, b, self._strategy.get(),
                  self._cb_progress, self._cb_result, self._cb_done,
                  self._cancel),
            kwargs={'recursive': self._recursive.get()},
            daemon=True,
        ).start()

    def _cb_progress(self, done: int, total: int, name: str) -> None:
        self._q.put(('prog', done, total, name))

    def _cb_result(self, pair: scanner.DuplicatePair) -> None:
        self._q.put(('pair', pair))

    def _cb_done(self, count: int) -> None:
        self._q.put(('done', count))

    def _poll(self) -> None:
        try:
            for _ in range(30):
                msg = self._q.get_nowait()
                kind = msg[0]

                if kind == 'prog':
                    _, done, total, name = msg
                    pct = int(done / total * 100) if total else 0
                    self._progress.config(value=pct)
                    short = os.path.basename(name)[:28] if name else ''
                    self._status_lbl.config(text=f'{done} / {total}   {short}')

                elif kind == 'pair':
                    self._results.add_pair(msg[1])

                elif kind == 'done':
                    count = msg[1]
                    self._scanning = False
                    self._scan_btn.config(text=t('find_btn'), state='normal')
                    self._btn_en.config(state='normal')
                    self._btn_ru.config(state='normal')
                    self._update_lang_btns()
                    self._progress.config(value=100 if count else 0)
                    self._results.mark_scan_done()
                    if count == 0:
                        self._status_lbl.config(text=t('done_none'))
                        self._results.set_header(t('no_dupes'))
                    else:
                        self._status_lbl.config(text=t('done_found', n=count))

        except queue.Empty:
            pass

        self.root.after(50, self._poll)


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
