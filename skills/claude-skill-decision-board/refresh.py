#!/usr/bin/env python3
"""決めごとページの元の HTML を、いまの雛形に合わせる。

問い（QUESTIONS）と決まったこと（DECIDED）、プロジェクト名はそのまま残し、
それ以外を雛形のコードに差し替える。何度実行しても同じ結果になる。

使い方: python3 refresh.py <page.html>
"""
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / 'template.html'


def block(src, name):
    m = re.search(rf'^const {name} = \[(?:\]|\n.*?^\])$', src, re.M | re.S)
    if not m:
        sys.exit(f'{name} が見つかりません')
    return m.group(0)


def main():
    page = Path(sys.argv[1])
    old = page.read_text(encoding='utf-8')
    m = re.search(r'<title>(.*?) の決めごと</title>', old)
    if not m:
        sys.exit('タイトルからプロジェクト名が取れません')
    new = TEMPLATE.read_text(encoding='utf-8').replace('{{PROJECT}}', m.group(1))
    for name in ('QUESTIONS', 'DECIDED'):
        new = new.replace(block(new, name), block(old, name), 1)
    if new == old:
        print('雛形と同じです')
        return
    page.write_text(new, encoding='utf-8')
    print('雛形に合わせました')


if __name__ == '__main__':
    main()
