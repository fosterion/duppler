"""Localisation strings and helpers (EN / RU)."""

_state: dict = {'lang': 'en'}

STRINGS: dict = {
    'ru': {
        # toolbar
        'folder_a':          'Папка A',
        'folder_b':          'Папка B',
        'browse':            'Выбрать…',
        'method_label':      'Метод:',
        'exact_radio':       'Точный хэш (быстро)',
        'perceptual_radio':  'Визуальное сходство для фото, точный для видео (медленнее)',
        'find_btn':          'Найти дубликаты',
        'cancel_btn':        'Отменить',
        # results panel
        'scanning':          'Сканирование…',
        'no_dupes':          'Дубликатов не найдено',
        'dupes_count':       'Дубликатов: {n}',
        'shown_of':          'Показано {shown} из {total} дубликатов',
        'load_more_btn':     '  Показать ещё {next_n}  (осталось {rem})  ',
        'done_none':         'Готово — дубликатов нет',
        'done_found':        'Готово — {n} пар',
        # pair row
        'badge_exact':       '  ✓  точное совпадение  ',
        'badge_perceptual':  '  ≈  визуально похожи  (расстояние {d})  ',
        'card_a_header':     'ПАПКА  A',
        'card_b_header':     'ПАПКА  B',
        'delete':            'Удалить',
        # dialogs
        'dlg_pick_title':    'Выбери папки',
        'dlg_pick_msg':      'Укажи обе папки для сравнения.',
        'dlg_dir_title':     'Ошибка',
        'dlg_dir_msg':       'Папка не найдена:\n{path}',
        'dlg_same_title':    'Одинаковые папки',
        'dlg_same_msg':      'Папки A и B должны быть разными.',
        'dlg_err_title':     'Ошибка удаления',
        'dlg_err_msg':       'Не удалось переместить в корзину:\n{path}\n\n{exc}',
        # dep check
        'dep_title':         'Отсутствуют зависимости',
        'dep_msg':           'Установи пакеты командой:\n\n    pip install {pkgs}\n\nДля режима «Визуальное сходство»:\n    pip install imagehash',
    },
    'en': {
        # toolbar
        'folder_a':          'Folder A',
        'folder_b':          'Folder B',
        'browse':            'Browse…',
        'method_label':      'Method:',
        'exact_radio':       'Exact hash (fast)',
        'perceptual_radio':  'Visual similarity for photos, exact for video (slower)',
        'find_btn':          'Find duplicates',
        'cancel_btn':        'Cancel',
        # results panel
        'scanning':          'Scanning…',
        'no_dupes':          'No duplicates found',
        'dupes_count':       'Duplicates: {n}',
        'shown_of':          'Showing {shown} of {total} duplicates',
        'load_more_btn':     '  Show {next_n} more  ({rem} remaining)  ',
        'done_none':         'Done — no duplicates',
        'done_found':        'Done — {n} pairs',
        # pair row
        'badge_exact':       '  ✓  exact match  ',
        'badge_perceptual':  '  ≈  visually similar  (distance {d})  ',
        'card_a_header':     'FOLDER  A',
        'card_b_header':     'FOLDER  B',
        'delete':            'Delete',
        # dialogs
        'dlg_pick_title':    'Select folders',
        'dlg_pick_msg':      'Please select both folders.',
        'dlg_dir_title':     'Error',
        'dlg_dir_msg':       'Folder not found:\n{path}',
        'dlg_same_title':    'Same folder',
        'dlg_same_msg':      'Folders A and B must be different.',
        'dlg_err_title':     'Delete error',
        'dlg_err_msg':       'Failed to move to Recycle Bin:\n{path}\n\n{exc}',
        # dep check
        'dep_title':         'Missing dependencies',
        'dep_msg':           'Install packages with:\n\n    pip install {pkgs}\n\nFor Visual Similarity mode:\n    pip install imagehash',
    },
}


def get_lang() -> str:
    return _state['lang']


def set_lang(lang: str) -> None:
    _state['lang'] = lang


def t(key: str, **kw) -> str:
    s = STRINGS.get(_state['lang'], STRINGS['en']).get(key, key)
    return s.format(**kw) if kw else s
