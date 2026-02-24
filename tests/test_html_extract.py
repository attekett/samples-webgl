from api_audit.html_extract import extract_script
from api_audit.parse import parse_js


class TestExtractScript:
    def test_single_script(self):
        html = '<html><body><script>var x = 1;</script></body></html>'
        assert extract_script(html) == 'var x = 1;'

    def test_multiple_scripts_concatenated(self):
        html = '<script>var a = 1;</script><script>var b = 2;</script>'
        result = extract_script(html)
        assert 'var a = 1;' in result
        assert 'var b = 2;' in result

    def test_empty_script(self):
        html = '<script></script>'
        assert extract_script(html) == ''

    def test_malformed_html(self):
        html = '<script>var x = 1;<div>'
        result = extract_script(html)
        assert 'var x = 1;' in result

    def test_no_script(self):
        html = '<html><body><p>Hello</p></body></html>'
        assert extract_script(html) == ''


class TestParseJs:
    def test_returns_root_node(self):
        root = parse_js('var x = 1;')
        assert root is not None
        assert root.type == 'program'

    def test_empty_string(self):
        root = parse_js('')
        assert root is not None
        assert root.type == 'program'

    def test_gl_call_is_parseable(self):
        root = parse_js('gl.drawArrays(gl.TRIANGLES, 0, 3);')
        assert root.child_count > 0
