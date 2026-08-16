"""tests/fuzz_data.py -- shared parametrize data. Centralized so
test_authentication.py's lighter email-format pass and
test_input_validation.py's deeper boundary pass don't drift out of sync
with each other over time.
"""

MALFORMED_EMAILS = [
    ("plainaddress", "plainaddress"),
    ("no_at_symbol", "userexample.com"),
    ("no_tld", "user@example"),
    ("double_at", "user@@example.com"),
    ("leading_dot", ".user@example.com"),
    ("trailing_dot", "user.@example.com"),
    ("spaces_in_local", "us er@example.com"),
    ("comma_in_local", "user,name@example.com"),
    ("semicolon_in_local", "user;name@example.com"),
    ("unicode_domain", "user@exämple.com"),
    ("very_long_local", ("a" * 250) + "@example.com"),
    ("empty_string", ""),
]

VALID_LOOKING_EMAILS = [
    ("simple", "user@example.com"),
    ("plus_tag", "user+tag@example.com"),
    ("subdomain", "user@mail.example.com"),
    ("short", "u@e.io"),
]

BOUNDARY_TEXT_INPUTS = [
    ("empty", ""),
    ("whitespace_only", "   "),
    ("single_char", "a"),
    ("very_long", "A" * 5000),
    ("sql_injection", "'; DROP TABLE scans; --"),
    ("script_tag_xss", "<script>alert(1)</script>"),
    ("html_entities", "&lt;b&gt;bold&lt;/b&gt;"),
    ("emoji", "\U0001F600\U0001F4A5\U0001F510"),
    ("null_byte_like", "value\x00tail"),
    ("newlines", "line one\nline two\nline three"),
    ("unicode_rtl", "\u202Ereversed\u202C"),
    ("leading_trailing_spaces", "   padded value   "),
    ("valid_ip", "192.168.1.55"),
    ("valid_cidr", "10.0.0.0/24"),
    ("valid_hostname", "testphp.vulnweb.com"),
    ("path_traversal", "../../etc/passwd"),
]

BOUNDARY_PASSWORD_INPUTS = [
    ("empty", ""),
    ("whitespace_only", "        "),
    ("single_char", "a"),
    ("very_long", "P@ssw0rd" * 40),
    ("sql_injection", "' OR '1'='1"),
    ("unicode", "pässwörd123!"),
    ("only_digits", "12345678"),
    ("only_symbols", "!@#$%^&*()"),
    ("leading_trailing_spaces", "  Client1QA123!  "),
    ("wrong_case", "client1qa123!"),
    ("truncated_valid", "Client1QA12"),
    ("valid_plus_extra_char", "Client1QA123!X"),
]
