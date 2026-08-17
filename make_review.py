#!/usr/bin/env python3
"""Inline deck.json into review_template.html -> review.html (works from file://)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
deck = json.load(open(os.path.join(HERE, "data/deck.json"), encoding="utf-8"))
tpl = open(os.path.join(HERE, "review_template.html"), encoding="utf-8").read()
payload = json.dumps(deck, ensure_ascii=False).replace("</", "<\\/")
out = os.path.join(HERE, "review.html")
open(out, "w", encoding="utf-8").write(tpl.replace("__DECK_JSON__", payload))
print("wrote", out, f"({os.path.getsize(out)//1024} KB, {len(deck['words'])} words)")
