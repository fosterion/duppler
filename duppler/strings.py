"""Localisation strings and helpers (EN / RU)."""

_state: dict = {'lang': 'en'}

STRINGS: dict = {
    'ru': {
        # mode
        'mode_two':          'Две папки',
        'mode_one':          'Одна папка',
        # toolbar
        'folder_a':          'Папка A',
        'folder_b':          'Папка B',
        'browse':            'Выбрать…',
        'method_label':      'Метод:',
        'exact_radio':       'Точный хэш (быстро)',
        'perceptual_radio':  'Визуальное сходство для фото, точный для видео (медленнее)',
        'find_btn':          'Найти дубликаты',
        'cancel_btn':        'Отменить',
        'recursive_check':   'Включая подпапки',
        # results panel
        'scanning':          'Сканирование…',
        'no_dupes':          'Дубликатов не найдено',
        'dupes_count':       'Дубликатов: {n}',
        'shown_of':          'Показано {shown} из {total} дубликатов',
        'load_more_btn':     '  Показать ещё {next_n}  (осталось {rem})  ',
        'done_none':         'Готово — дубликатов нет',
        'done_found':        'Готово — {n} пар',
        'groups_count':      'Групп: {n}',
        'shown_of_grp':      'Показано {shown} из {total} групп',
        'done_groups':       'Готово — {n} групп',
        'group_files':       '{n} файлов',
        'del_all_a':         'Удалить все из A',
        'del_all_b':         'Удалить все из B',
        'scan_file_count':   'Файлов: {n}',
        'scan_file_count2':  'Файлов: {a} + {b}',
        'scan_comparing':    'Сравниваю изображения…',
        'dlg_del_all_title': 'Подтверждение',
        'dlg_del_all_msg':   'Переместить {n} файлов из Папки {which} в корзину?',
        # pair row
        'badge_exact':       '  ✓  точное совпадение  ',
        'badge_perceptual':  '  ≈  визуально похожи  (расстояние {d})  ',
        'card_a_header':     'ПАПКА  A',
        'card_b_header':     'ПАПКА  B',
        'delete':            'Удалить',
        'show_in_explorer':  'Показать в проводнике',
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
        # mode
        'mode_two':          'Two folders',
        'mode_one':          'One folder',
        # toolbar
        'folder_a':          'Folder A',
        'folder_b':          'Folder B',
        'browse':            'Browse…',
        'method_label':      'Method:',
        'exact_radio':       'Exact hash (fast)',
        'perceptual_radio':  'Visual similarity for photos, exact for video (slower)',
        'find_btn':          'Find duplicates',
        'cancel_btn':        'Cancel',
        'recursive_check':   'Include subfolders',
        # results panel
        'scanning':          'Scanning…',
        'no_dupes':          'No duplicates found',
        'dupes_count':       'Duplicates: {n}',
        'shown_of':          'Showing {shown} of {total} duplicates',
        'load_more_btn':     '  Show {next_n} more  ({rem} remaining)  ',
        'done_none':         'Done — no duplicates',
        'done_found':        'Done — {n} pairs',
        'groups_count':      'Groups: {n}',
        'shown_of_grp':      'Showing {shown} of {total} groups',
        'done_groups':       'Done — {n} groups',
        'group_files':       '{n} files',
        'del_all_a':         'Delete all from A',
        'del_all_b':         'Delete all from B',
        'scan_file_count':   'Files: {n}',
        'scan_file_count2':  'Files: {a} + {b}',
        'scan_comparing':    'Comparing images…',
        'dlg_del_all_title': 'Confirm',
        'dlg_del_all_msg':   'Move {n} files from Folder {which} to Recycle Bin?',
        # pair row
        'badge_exact':       '  ✓  exact match  ',
        'badge_perceptual':  '  ≈  visually similar  (distance {d})  ',
        'card_a_header':     'FOLDER  A',
        'card_b_header':     'FOLDER  B',
        'delete':            'Delete',
        'show_in_explorer':  'Show in Explorer',
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
