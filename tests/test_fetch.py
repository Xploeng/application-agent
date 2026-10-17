import unittest

from inbox.fetch import decode_part, find_text_part, html_to_text, join_fetch, parse_internaldate, parse_sexp

SINGLE_PLAIN = b'("TEXT" "PLAIN" ("CHARSET" "iso-8859-1") NIL NIL "QUOTED-PRINTABLE" 120 4 NIL NIL NIL NIL)'

ALTERNATIVE = (
    b'(("TEXT" "PLAIN" ("CHARSET" "utf-8") NIL NIL "7BIT" 50 2 NIL NIL NIL NIL)'
    b'("TEXT" "HTML" ("CHARSET" "utf-8") NIL NIL "BASE64" 400 6 NIL NIL NIL NIL)'
    b' "ALTERNATIVE" ("BOUNDARY" "b1") NIL NIL NIL)'
)

# mixed: [alternative(plain, html), pdf attachment]; params list after subtype must not count as a part
MIXED_WITH_PDF = (
    b'((("TEXT" "PLAIN" ("CHARSET" "utf-8") NIL NIL "7BIT" 50 2 NIL NIL NIL NIL)'
    b'("TEXT" "HTML" ("CHARSET" "utf-8") NIL NIL "QUOTED-PRINTABLE" 400 6 NIL NIL NIL NIL)'
    b' "ALTERNATIVE" ("BOUNDARY" "b2") NIL NIL NIL)'
    b'("APPLICATION" "PDF" ("NAME" "cv.pdf") NIL NIL "BASE64" 90000 NIL ("ATTACHMENT" ("FILENAME" "cv.pdf")) NIL NIL)'
    b' "MIXED" ("BOUNDARY" "b1") NIL NIL NIL)'
)

# text file attached as text/plain: must be skipped, html body chosen
TEXT_ATTACHMENT_ONLY = (
    b'(("TEXT" "PLAIN" ("CHARSET" "utf-8") NIL NIL "7BIT" 50 2 NIL ("ATTACHMENT" ("FILENAME" "a.txt")) NIL NIL)'
    b' "MIXED" ("BOUNDARY" "b3") NIL NIL NIL)'
)


def bs(raw: bytes):
    return parse_sexp(raw)[0]


class FindTextPartTest(unittest.TestCase):
    def test_single_part_plain(self):
        self.assertEqual(find_text_part(bs(SINGLE_PLAIN)), ("1", "plain", "quoted-printable", "iso-8859-1"))

    def test_alternative_prefers_html(self):
        self.assertEqual(find_text_part(bs(ALTERNATIVE)), ("2", "html", "base64", "utf-8"))

    def test_mixed_with_pdf_picks_nested_html(self):
        self.assertEqual(find_text_part(bs(MIXED_WITH_PDF)), ("1.2", "html", "quoted-printable", "utf-8"))

    def test_text_attachment_is_skipped(self):
        self.assertIsNone(find_text_part(bs(TEXT_ATTACHMENT_ONLY)))


class FetchResponseTest(unittest.TestCase):
    def test_literal_header_and_bracketed_key(self):
        header = b"From: Recruiting <jobs@example.com>\r\nSubject: Ihre Bewerbung\r\n\r\n"
        data = [
            (b'1 (UID 42 INTERNALDATE " 7-Oct-2026 14:05:09 +0200" BODYSTRUCTURE ' + SINGLE_PLAIN
             + b' BODY[HEADER.FIELDS (FROM SUBJECT)] {%d}' % len(header), header),
            b")",
        ]
        tokens = parse_sexp(join_fetch(data))
        self.assertEqual(tokens[0], "1")
        fields = dict(zip(tokens[1][::2], tokens[1][1::2]))
        self.assertEqual(fields["UID"], "42")
        self.assertEqual(fields["BODY[HEADER.FIELDS (FROM SUBJECT)]"], header)
        self.assertEqual(parse_internaldate(fields["INTERNALDATE"]).isoformat(), "2026-10-07T12:05:09+00:00")


class DecodeTest(unittest.TestCase):
    def test_quoted_printable_latin1(self):
        self.assertEqual(decode_part(b"Gr=FC=DFe", "quoted-printable", "iso-8859-1"), "Grüße")

    def test_unknown_charset_falls_back(self):
        self.assertEqual(decode_part(b"hi", "7bit", "x-made-up"), "hi")

    def test_html_to_text_drops_images_scripts_styles(self):
        html = (
            '<html><head><title>T</title><style>p{color:red}</style></head><body>'
            '<p>Leider m&uuml;ssen wir Ihnen absagen.</p><img src="https://track.example.com/px.gif">'
            "<script>alert(1)</script><div>Viele Gr&uuml;&szlig;e</div></body></html>"
        )
        self.assertEqual(html_to_text(html), "Leider müssen wir Ihnen absagen.\nViele Grüße")


if __name__ == "__main__":
    unittest.main()
