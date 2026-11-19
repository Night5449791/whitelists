#!/usr/bin/env python3
import curses
import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PlayerWhitelist.json')

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

state = {'dirty': False}


def save():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    state['dirty'] = False


def prompt(stdscr, text, default=''):
    curses.curs_set(1)
    h, w = stdscr.getmaxyx()
    hint = text + ((' [' + default + ']') if default else '') + ': '
    stdscr.addnstr(h - 1, 0, ' ' * (w - 1), w - 1, curses.A_REVERSE)
    stdscr.addnstr(h - 1, 0, hint[:w - 1], w - 1, curses.A_REVERSE)
    stdscr.refresh()
    curses.echo()
    try:
        value = stdscr.getstr(h - 1, len(hint), 200).decode('utf-8')
    finally:
        curses.noecho()
        curses.curs_set(0)
    return value if value else default


def confirm(stdscr, text):
    return prompt(stdscr, text + ' (y/N)', 'n').lower().startswith('y')


def draw_menu(stdscr, title, items, selected, info=None):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(0, 0, title, w - 1, curses.A_BOLD)
    if info:
        stdscr.addnstr(1, 0, info, w - 1, curses.A_DIM)
    start = max(0, selected - (h - 4))
    for i in range(start, min(len(items), start + h - 3)):
        marker = '> ' if i == selected else '  '
        attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
        stdscr.addnstr(i - start + 3, 0, (marker + str(items[i]))[:w - 1], w - 1, attr)
    stdscr.addnstr(h - 2, 0, '[up/down] move  [enter] edit  [n] new  [d] delete  [s] save  [q] back', w - 1, curses.A_DIM)
    stdscr.refresh()


def scroll_list(stdscr, title, items, info=None, selected=0):
    while True:
        draw_menu(stdscr, title, items, selected, info)
        key = stdscr.getch()
        if key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(items) - 1, selected + 1) if items else 0
        else:
            return key, selected


def edit_value(stdscr, label, value, cast=str):
    raw = prompt(stdscr, label, str(value))
    try:
        return cast(raw)
    except (ValueError, TypeError):
        return value


def edit_hashes(stdscr, user):
    hashes = user.get('hashes') or ([user['hash']] if 'hash' in user else [])
    sel = 0
    while True:
        key, sel = scroll_list(stdscr, 'HASHES', hashes, 'n add, d delete, q back', sel)
        if key in (ord('q'), 27):
            break
        if key == ord('s'):
            save()
        elif key == ord('n'):
            value = prompt(stdscr, 'new hash')
            if value:
                hashes.append(value)
                user.pop('hash', None)
                user['hashes'] = hashes
                state['dirty'] = True
        elif key == ord('d') and hashes:
            del hashes[sel]
            user['hashes'] = hashes
            state['dirty'] = True


def edit_tags(stdscr, tags):
    sel = 0
    while True:
        labels = [t.get('text', '') + ' ' + str(t.get('color', [])) for t in tags]
        key, sel = scroll_list(stdscr, 'TAGS', labels, 'n add, d delete, q back', sel)
        if key in (ord('q'), 27):
            break
        if key == ord('s'):
            save()
        elif key == ord('n'):
            text = prompt(stdscr, 'tag text')
            color_raw = prompt(stdscr, 'color r,g,b', '255,255,255')
            try:
                color = [int(x.strip()) for x in color_raw.split(',')][:3]
            except ValueError:
                color = [255, 255, 255]
            if text:
                tags.append({'text': text, 'color': color})
                state['dirty'] = True
        elif key == ord('d') and tags:
            del tags[sel]
            state['dirty'] = True


def edit_user(stdscr, user_id, user):
    sel = 0
    while True:
        hashes = user.get('hashes') or ([user['hash']] if 'hash' in user else [])
        lines = [
            'ID: ' + user_id,
            'Level: ' + str(user.get('level', 1)),
            'Attackable: ' + str(user.get('attackable', False)),
            'Note: ' + str(user.get('note', '')),
            'Hashes: ' + str(len(hashes)),
            'Tags: ' + str(len(user.get('tags', []))),
        ]
        key, sel = scroll_list(stdscr, 'EDIT USER', lines, 'enter edit, q back', sel)
        if key in (ord('q'), 27):
            return
        if key == ord('s'):
            save()
        elif key in (10, 13):
            if sel == 1:
                user['level'] = edit_value(stdscr, 'level', user.get('level', 1), int)
            elif sel == 2:
                user['attackable'] = not user.get('attackable', False)
            elif sel == 3:
                user['note'] = prompt(stdscr, 'note', user.get('note', ''))
            elif sel == 4:
                edit_hashes(stdscr, user)
            elif sel == 5:
                edit_tags(stdscr, user.setdefault('tags', []))
            state['dirty'] = True


def edit_users(stdscr):
    users = data.setdefault('WhitelistedUsers', {})
    sel = 0
    while True:
        ids = list(users.keys())
        key, sel = scroll_list(stdscr, 'WHITELISTED USERS', ids, 'enter edit, n new, d delete, q back', sel)
        if key in (ord('q'), 27):
            return
        if key == ord('s'):
            save()
        elif key == ord('n'):
            uid = prompt(stdscr, 'user id')
            if uid:
                users[uid] = {'hashes': [], 'attackable': False, 'level': 1, 'time': 0, 'tags': []}
                state['dirty'] = True
        elif key == ord('d') and ids:
            if confirm(stdscr, 'delete ' + ids[sel] + '?'):
                del users[ids[sel]]
                state['dirty'] = True
        elif key in (10, 13) and ids:
            edit_user(stdscr, ids[sel], users[ids[sel]])


def edit_tag_users(stdscr):
    section = data.setdefault('WhitelistedTags', {})
    sel = 0
    while True:
        ids = list(section.keys())
        key, sel = scroll_list(stdscr, 'WHITELISTED TAGS', ids, 'enter edit, n new, d delete, q back', sel)
        if key in (ord('q'), 27):
            return
        if key == ord('s'):
            save()
        elif key == ord('n'):
            uid = prompt(stdscr, 'user id')
            if uid:
                section[uid] = []
                state['dirty'] = True
        elif key == ord('d') and ids:
            if confirm(stdscr, 'delete ' + ids[sel] + '?'):
                del section[ids[sel]]
                state['dirty'] = True
        elif key in (10, 13) and ids:
            edit_tags(stdscr, section.setdefault(ids[sel], []))
            state['dirty'] = True


def edit_blacklist(stdscr):
    section = data.setdefault('BlacklistedUsers', {})
    sel = 0
    while True:
        ids = list(section.keys())
        items = [i + ': ' + str(section[i]) for i in ids]
        key, sel = scroll_list(stdscr, 'BLACKLISTED USERS', items, 'enter edit, n new, d delete, q back', sel)
        if key in (ord('q'), 27):
            return
        if key == ord('s'):
            save()
        elif key == ord('n'):
            uid = prompt(stdscr, 'user id')
            reason = prompt(stdscr, 'reason')
            if uid:
                section[uid] = reason
                state['dirty'] = True
        elif key == ord('d') and ids:
            if confirm(stdscr, 'delete ' + ids[sel] + '?'):
                del section[ids[sel]]
                state['dirty'] = True
        elif key in (10, 13) and ids:
            section[ids[sel]] = prompt(stdscr, 'reason', str(section[ids[sel]]))
            state['dirty'] = True


def edit_announcement(stdscr):
    ann = data.setdefault('Announcement', {})
    sel = 0
    while True:
        lines = [
            'Text: ' + str(ann.get('text', '')),
            'Expire time: ' + str(ann.get('expiretime', 0)),
            'Targets: ' + str(ann.get('targets', 'all')),
        ]
        key, sel = scroll_list(stdscr, 'ANNOUNCEMENT', lines, 'enter edit, q back', sel)
        if key in (ord('q'), 27):
            return
        if key == ord('s'):
            save()
        elif key in (10, 13):
            if sel == 0:
                ann['text'] = prompt(stdscr, 'text', ann.get('text', ''))
            elif sel == 1:
                ann['expiretime'] = edit_value(stdscr, 'expiretime', ann.get('expiretime', 0), int)
            elif sel == 2:
                ann['targets'] = prompt(stdscr, 'targets', ann.get('targets', 'all'))
            state['dirty'] = True


def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    sections = ['WhitelistedUsers', 'WhitelistedTags', 'BlacklistedUsers', 'Announcement', 'KillVape', 'rand']
    sel = 0
    while True:
        lines = []
        for name in sections:
            val = data.get(name)
            lines.append(name + ' = ' + str(val) if name in ('KillVape', 'rand') else name + ' (' + str(len(val)) + ' entries)')
        key, sel = scroll_list(stdscr, 'INHALER WHITELIST EDITOR', lines, 'enter edit, s save, q quit', sel)
        if key in (ord('q'), 27):
            if not state['dirty'] or confirm(stdscr, 'unsaved changes, quit anyway?'):
                break
        elif key == ord('s'):
            save()
        elif key in (10, 13):
            name = sections[sel]
            if name == 'WhitelistedUsers':
                edit_users(stdscr)
            elif name == 'WhitelistedTags':
                edit_tag_users(stdscr)
            elif name == 'BlacklistedUsers':
                edit_blacklist(stdscr)
            elif name == 'Announcement':
                edit_announcement(stdscr)
            elif name == 'KillVape':
                data['KillVape'] = not data.get('KillVape', False)
                state['dirty'] = True
            elif name == 'rand':
                data['rand'] = edit_value(stdscr, 'rand', data.get('rand', 0.0), float)
                state['dirty'] = True


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    if state['dirty']:
        save()
        print('Saved ' + DATA_FILE)
