"""Read-only fetch of new INBOX mail for the check-inbox skill.

Usage: uv run --env-file .env inbox/fetch.py [--since YYYY-MM-DD]

Never changes the mailbox: EXAMINE (read-only select) + BODY.PEEK only. Per mail it
fetches the From/Subject headers and one text part (html, else plain); attachments
and images are never downloaded. Output goes to a fresh temp dir:
  headers.json  [{uid, date, from, subject}]   oldest first
  <uid>.txt     body as plain text (capped)
"""

import argparse
import base64
import email
import email.policy
import imaplib
import json
import os
import quopri
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tracking.db import connect  # noqa: E402

BODY_CAP = 4000
REQUIRED_ENV = ("IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD")


# --- IMAP response parsing -------------------------------------------------

def parse_sexp(data: bytes):
    """Parse an IMAP parenthesised response into nested lists of str/bytes/None."""
    pos = 0

    def parse_list():
        nonlocal pos
        items = []
        while pos < len(data):
            c = data[pos:pos + 1]
            if c in (b" ", b"\r", b"\n"):
                pos += 1
            elif c == b"(":
                pos += 1
                items.append(parse_list())
            elif c == b")":
                pos += 1
                return items
            elif c == b'"':
                pos += 1
                out = bytearray()
                while data[pos:pos + 1] != b'"':
                    if data[pos:pos + 1] == b"\\":
                        pos += 1
                    out += data[pos:pos + 1]
                    pos += 1
                pos += 1
                items.append(out.decode("utf-8", "replace"))
            elif c == b"{":
                end = data.index(b"}", pos)
                n = int(data[pos + 1:end])
                pos = end + 1
                if data[pos:pos + 2] == b"\r\n":
                    pos += 2
                items.append(data[pos:pos + n])
                pos += n
            else:
                start = pos
                while pos < len(data) and data[pos:pos + 1] not in b" ()":
                    if data[pos:pos + 1] == b"[":  # BODY[HEADER.FIELDS (FROM SUBJECT)]
                        pos = data.index(b"]", pos)
                    pos += 1
                atom = data[start:pos].decode()
                items.append(None if atom.upper() == "NIL" else atom)
        return items

    return parse_list()


def join_fetch(data: list) -> bytes:
    """imaplib splits literals into tuples; glue them back into one byte string."""
    return b"".join(b"".join(d) if isinstance(d, tuple) else d for d in data)


def find_text_part(bs, prefix: str = ""):
    """Return (part, subtype, encoding, charset) of the best text part, or None.

    Prefers text/html over text/plain, skips attachments and nested messages.
    """
    found = {}

    def walk(node, number):
        if isinstance(node[0], list):  # multipart: child parts, then subtype + extension data
            for i, child in enumerate(node):
                if not isinstance(child, list):
                    break
                walk(child, f"{number}.{i + 1}" if number else str(i + 1))
            return
        mtype, subtype = (node[0] or "").lower(), (node[1] or "").lower()
        if mtype != "text" or subtype not in ("html", "plain") or subtype in found:
            return
        disposition = node[9] if len(node) > 9 else None
        if isinstance(disposition, list) and (disposition[0] or "").lower() == "attachment":
            return
        params = node[2] or []
        charset = next((params[i + 1] for i in range(0, len(params) - 1, 2) if params[i].lower() == "charset"), None)
        found[subtype] = (number or "1", subtype, (node[5] or "7bit").lower(), charset or "utf-8")

    walk(bs, prefix)
    return found.get("html") or found.get("plain")


def decode_part(raw: bytes, encoding: str, charset: str) -> str:
    if encoding == "base64":
        raw = base64.b64decode(raw)
    elif encoding == "quoted-printable":
        raw = quopri.decodestring(raw)
    try:
        return raw.decode(charset, "replace")
    except LookupError:  # unknown charset name
        return raw.decode("utf-8", "replace")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "head"}
    BLOCK = {"p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"}

    def __init__(self):
        super().__init__()
        self.parts, self.skipping = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Text content only; nothing is rendered, no URL (images, pixels) is requested."""
    p = _TextExtractor()
    p.feed(html)
    text = "".join(p.parts)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t\xa0]+", " ", text)).strip()


def parse_internaldate(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%d-%b-%Y %H:%M:%S %z").astimezone(timezone.utc)


# --- main --------------------------------------------------------------------

def last_mail_at() -> datetime:
    conn = connect()
    try:
        (value,) = conn.execute("SELECT last_mail_at FROM inbox_state").fetchone()
    finally:
        conn.close()
    return datetime.fromisoformat(value)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", help="read mail received on/after this date (YYYY-MM-DD) instead of the stored stamp")
    args = ap.parse_args()

    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")

    after = (datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
             if args.since else last_mail_at())
    search_day = (after - timedelta(days=1)).strftime("%d-%b-%Y")  # SINCE is day-granular

    imap = imaplib.IMAP4_SSL(os.environ["IMAP_HOST"], 993)
    try:
        imap.login(os.environ["IMAP_USER"], os.environ["IMAP_PASSWORD"])
        imap.select("INBOX", readonly=True)  # EXAMINE: server refuses flag changes
        _, found = imap.uid("SEARCH", None, "SINCE", search_day)
        uids = found[0].split()
        mails = []
        if uids:
            _, data = imap.uid("FETCH", b",".join(uids),
                               "(UID INTERNALDATE BODYSTRUCTURE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            tokens = parse_sexp(join_fetch(data))
            for i in range(0, len(tokens) - 1, 2):  # "<seq> (<key> <value> ...)"
                fields = dict(zip(tokens[i + 1][::2], tokens[i + 1][1::2]))
                date = parse_internaldate(fields["INTERNALDATE"])
                if date <= after:
                    continue
                header_key = next(k for k in fields if k.startswith("BODY["))
                raw_hdr = fields[header_key] or b""
                if isinstance(raw_hdr, str):  # short headers may come as a quoted string
                    raw_hdr = raw_hdr.encode()
                hdr = email.message_from_bytes(raw_hdr, policy=email.policy.default)
                try:
                    part = find_text_part(fields["BODYSTRUCTURE"])
                except (IndexError, TypeError, AttributeError):
                    part = None  # unusual structure: triage on headers only
                mails.append({"uid": fields["UID"], "date": date.isoformat(),
                              "from": str(hdr["from"] or ""), "subject": str(hdr["subject"] or ""), "_part": part})

        out = Path(tempfile.mkdtemp(prefix="inbox-"))
        mails.sort(key=lambda m: m["date"])
        for m in mails:
            text = ""
            if part := m.pop("_part"):
                number, subtype, encoding, charset = part
                _, data = imap.uid("FETCH", m["uid"], f"(BODY.PEEK[{number}])")
                raw = next((d[1] for d in data if isinstance(d, tuple)), b"")
                text = decode_part(raw, encoding, charset)
                if subtype == "html":
                    text = html_to_text(text)
            (out / f"{m['uid']}.txt").write_text(text[:BODY_CAP])
        (out / "headers.json").write_text(json.dumps(mails, ensure_ascii=False, indent=1))
    finally:
        imap.logout()

    print(f"dir: {out}")
    print(f"mails: {len(mails)}")
    print(f"newest: {mails[-1]['date'] if mails else 'none'}")


if __name__ == "__main__":
    main()
