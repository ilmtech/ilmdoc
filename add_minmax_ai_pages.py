#!/usr/bin/env python3
"""Adds the "AI Assistant" section (Min/Max 5.4.0) to src/minmax-ps/pages.json, one page per AI video.

Reads the YouTube ids from the AI video folder (out/youtube-ai.json: {"<clip id>": "<yt id>"}),
the timed narration from its work/tl + out/*.srt, and writes src/minmax-ps/<slug>.html.
Safe to run again: the section is replaced, other sections are not touched.

    python3 tools/docsite/add_minmax_ai_pages.py
"""
import json
import subprocess
from pathlib import Path

import import_minmax_pages as base

HERE = Path(__file__).resolve().parent
AI = Path('/home/asha/projects/prestashop/modules/ilmminmaxorderqty/marketplace/video/ai')
OUT = HERE / 'src' / 'minmax-ps'
base.VIDEO = AI  # steps() reads work/tl and out/*.srt from here

CREDITS = ('<p>The AI features use AI answers of your AI plan: one answer for each <b>Build rules</b>, each '
           '<b>Write with AI</b> language and each <b>Get an idea from AI</b>. <b>Check my rules</b> uses one only when '
           'it finds a problem to explain. <b>Set up a rule step by step</b> is free and needs no AI plan. '
           'The line under <b>Create rules with AI</b> shows how many answers are left.</p>')

PAGES = [
    ('create-rules-with-ai', '01-create-rules-with-ai',
     '<p>On the <b>AI Assistant</b> tab, describe your limits in your own words under <b>Create rules with AI</b> and '
     'click <b>Build rules</b>. The AI answers with a preview: one row per rule, with a note. Nothing is saved until you '
     'click <b>Apply selected</b>, and only ticked rows are saved. The rules then appear on the Quantity / Amount Rule '
     'tab like any other rule.</p>\n<p>Write one limit per sentence and use the names of your categories, brands, '
     'suppliers and customer groups.</p>\n' + CREDITS),
    ('check-my-rules', '02-check-my-rules',
     '<p><b>Check my rules</b> looks for rules that can never apply or contradict themselves, for example a maximum that '
     'is not a multiple of the pack size. The AI explains each problem in plain words. The check never changes a rule; '
     'you fix it on the rule table. When no problem is found, no AI answer is used.</p>'),
    ('write-messages-with-ai', '03-write-messages-with-ai',
     '<p>On <b>Configuration &gt; Messages</b>, choose a language and click <b>Write with AI</b>. Every message of that '
     'language is written in one go, keeping placeholders such as {QTY} and {NAME}, and the page saves them. An '
     'optional tone note, such as "friendly and short", steers the wording. Check the texts and change what you like.</p>'),
    ('step-by-step-and-ai-idea', '04-wizard-and-ai-idea',
     '<p><b>Set up a rule step by step</b> asks what to limit, which products, for whom, when, and the numbers, then '
     'shows the rule before it is saved. It needs no AI. <b>Get an idea from AI</b> adds one suggested rule that shops '
     'in the same situation often add; it arrives unticked and is saved only if you tick it.</p>'),
]


def length(mp4):
    s = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp4)]))
    return '%d:%02d' % (int(s) // 60, round(s) % 60)


def main():
    yt = json.loads((AI / 'out' / 'youtube-ai.json').read_text(encoding='utf-8'))
    tree = json.loads((OUT / 'pages.json').read_text(encoding='utf-8'))
    kids = []
    for slug, clip, html in PAGES:
        st = base.steps(clip)
        title = {'create-rules-with-ai': 'Create rules with AI', 'check-my-rules': 'Check my rules',
                 'write-messages-with-ai': 'Write messages with AI',
                 'step-by-step-and-ai-idea': 'Step by step, and an idea from AI'}[slug]
        lead = {'create-rules-with-ai': 'Describe your limits in your own words, check the preview, apply what you tick.',
                'check-my-rules': 'Find rules that can never apply or contradict themselves.',
                'write-messages-with-ai': 'All shopper messages of one language in one go.',
                'step-by-step-and-ai-idea': 'Build a rule by answering questions; ask the AI for one more idea.'}[slug]
        (OUT / f'{slug}.html').write_text(html + '\n', encoding='utf-8')
        kids.append({'slug': slug, 'title': title,
                     'video': {'yt': yt[clip], 'len': length(AI / 'out' / f'{clip}-en.mp4'), 'clip': clip},
                     'lead': lead, 'intro': st[0]['text'], 'steps': st[1:], 'file': f'{slug}.html'})
    (OUT / 'ai-assistant.html').write_text(
        '<p>Version 5.4.0 adds the <b>AI Assistant</b> tab: rules from plain words, a rule check, messages written by AI, '
        'and a free step-by-step rule setup.</p>\n' + CREDITS + '\n', encoding='utf-8')
    section = {'slug': 'ai-assistant', 'title': 'AI Assistant', 'file': 'ai-assistant.html', 'pages': kids}
    pages = [p for p in tree['pages'] if p['slug'] != 'ai-assistant']
    at = next(i for i, p in enumerate(pages) if p['slug'] == 'uninstall-and-delete')
    pages.insert(at, section)
    tree['pages'] = pages
    (OUT / 'pages.json').write_text(json.dumps(tree, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print('AI section:', [k['slug'] for k in kids])


if __name__ == '__main__':
    main()
