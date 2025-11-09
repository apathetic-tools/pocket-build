r"""Tests for pocket_build.utils._compile_glob_recursive() regex generator.

_compile_glob_recursive() compiles a glob pattern to a regex pattern,
backporting recursive '**' support to Python < 3.11.

This function is always case-sensitive and uses gitignore-style pattern matching.

Test Coverage:
- pattern_types_single_star — * matches any characters except /
- pattern_types_double_star — ** matches recursively including /
- pattern_types_question_mark — ? matches exactly one character except /
- pattern_types_character_class — [] matches character classes
- pattern_types_literals — literal characters are escaped properly
- edge_cases_unmatched_brackets — unmatched [ treated as literal
- edge_cases_escaped_chars — regex metacharacters are escaped
- edge_cases_empty_pattern — empty pattern behavior
- edge_cases_run_of_stars — *** or more collapse to **
- caching_behavior — @lru_cache(maxsize=512) caches patterns
- regex_anchoring — pattern is anchored with \Z
"""

# We import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from functools import _lru_cache_wrapper

import pocket_build.utils as mod_utils


# Cache configuration constants
_COMPILE_GLOB_RECURSIVE_CACHE_MAXSIZE = 512


class TestCompileGlobRecursivePatternTypes:
    """Test handling of glob pattern types: *, **, ?, [], literals."""

    def test_single_star_matches_any_except_slash(self) -> None:
        """* should match any characters except /.

        Example:
          pattern: "*.py"
          matches: "main.py", "test.py"
          no match: "src/main.py", "a/b/c.py"

        """
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("*.py")

        # --- verify matches ---
        assert pattern.match("main.py")
        assert pattern.match("test.py")
        assert pattern.match("a.py")
        assert pattern.match(".py")  # zero-length prefix

        # --- verify non-matches ---
        assert not pattern.match("src/main.py")
        assert not pattern.match("a/b/c.py")
        assert not pattern.match("main.txt")

    def test_single_star_in_middle(self) -> None:
        """* in the middle of a pattern."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/*.py")

        # --- verify ---
        assert pattern.match("src/main.py")
        assert pattern.match("src/test.py")
        # Single * does NOT cross /, unlike some shells
        # (in regex generator context, * is [^/]*)
        assert not pattern.match("src/sub/main.py")

    def test_double_star_matches_recursively(self) -> None:
        """** should match any characters including /.

        Example:
          pattern: "src/**/main.py"
          matches: "src/a/b/c/main.py"
          no match: "src/main.py" (** requires at least one segment)

        """
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/**/main.py")

        # --- verify matches ---
        assert pattern.match("src/a/main.py")
        assert pattern.match("src/a/b/main.py")
        assert pattern.match("src/a/b/c/main.py")

        # --- verify non-matches ---
        # ** requires at least one segment (matches /.+/)
        assert not pattern.match("src/main.py")
        assert not pattern.match("other/a/main.py")

    def test_double_star_at_start(self) -> None:
        """** at the start of pattern."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("**/main.py")

        # --- verify matches ---
        assert pattern.match("a/main.py")
        assert pattern.match("a/b/c/main.py")

        # --- verify non-matches ---
        # ** requires at least one path component
        assert not pattern.match("main.py")

    def test_double_star_at_end(self) -> None:
        """** at the end of pattern."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/**")

        # --- verify matches ---
        assert pattern.match("src/main.py")
        assert pattern.match("src/a/b/c/main.py")

        # --- verify non-matches ---
        assert not pattern.match("other/main.py")

    def test_double_star_alone(self) -> None:
        """** as the entire pattern."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("**")

        # --- verify matches everything ---
        assert pattern.match("a")
        assert pattern.match("a/b")
        assert pattern.match("a/b/c")

    def test_multiple_double_stars(self) -> None:
        """Multiple ** in one pattern."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/**/test/**/main.py")

        # --- verify matches ---
        assert pattern.match("src/a/test/b/main.py")
        assert pattern.match("src/a/b/test/c/d/main.py")

        # --- verify non-matches ---
        # Each ** requires at least one segment
        assert not pattern.match("src/test/main.py")
        assert not pattern.match("src/a/b/main.py")

    def test_question_mark_matches_single_char(self) -> None:
        """? should match exactly one character except /.

        Example:
          pattern: "file?.py"
          matches: "file1.py", "fileA.py"
          no match: "file12.py", "file.py"

        """
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file?.py")

        # --- verify matches ---
        assert pattern.match("file1.py")
        assert pattern.match("fileA.py")
        assert pattern.match("file_.py")

        # --- verify non-matches ---
        assert not pattern.match("file.py")  # no char
        assert not pattern.match("file12.py")  # two chars
        assert not pattern.match("file/.py")  # ? doesn't match /

    def test_multiple_question_marks(self) -> None:
        """Multiple ? in one pattern."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file??.py")

        # --- verify matches ---
        assert pattern.match("file12.py")
        assert pattern.match("fileAB.py")

        # --- verify non-matches ---
        assert not pattern.match("file1.py")  # one char
        assert not pattern.match("file123.py")  # three chars

    def test_character_class_basic(self) -> None:
        """[] should match character classes.

        Example:
          pattern: "file[0-9].py"
          matches: "file1.py", "file5.py"
          no match: "fileA.py"

        """
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[0-9].py")

        # --- verify matches ---
        assert pattern.match("file0.py")
        assert pattern.match("file5.py")
        assert pattern.match("file9.py")

        # --- verify non-matches ---
        assert not pattern.match("fileA.py")
        assert not pattern.match("file_.py")

    def test_character_class_range(self) -> None:
        """Character class with ranges."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[a-z].py")

        # --- verify matches ---
        assert pattern.match("filea.py")
        assert pattern.match("filem.py")
        assert pattern.match("filez.py")

        # --- verify non-matches ---
        assert not pattern.match("fileA.py")  # uppercase
        assert not pattern.match("file1.py")  # digit

    def test_character_class_multiple_ranges(self) -> None:
        """Character class with multiple ranges."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[0-9a-z].py")

        # --- verify matches ---
        assert pattern.match("file1.py")
        assert pattern.match("filea.py")

        # --- verify non-matches ---
        assert not pattern.match("fileA.py")
        assert not pattern.match("file_.py")

    def test_character_class_negation_with_caret_in_class(self) -> None:
        """[^...] negates a character class (Python regex syntax)."""
        # Note: _compile_glob_recursive passes [!...] through as-is,
        # but Python regex interprets [!...] as literal [!] and the chars.
        # Use [^...] for negation which works in Python regex.
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[^0-9].py")

        # --- verify matches ---
        assert pattern.match("fileA.py")
        assert pattern.match("file_.py")

        # --- verify non-matches ---
        assert not pattern.match("file1.py")
        assert not pattern.match("file5.py")

    def test_character_class_negation_with_caret(self) -> None:
        """[^...] also negates (alternative syntax)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[^0-9].py")

        # --- verify matches ---
        assert pattern.match("fileA.py")
        assert pattern.match("file_.py")

        # --- verify non-matches ---
        assert not pattern.match("file1.py")

    def test_character_class_with_leading_bracket(self) -> None:
        """[] can contain a literal ] at the start."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[]a].py")

        # --- verify matches ] and a ---
        assert pattern.match("file].py")
        assert pattern.match("filea.py")

        # --- verify non-matches ---
        assert not pattern.match("fileb.py")

    def test_literals_alphanumeric(self) -> None:
        """Alphanumeric characters are preserved literally."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/main.py")

        # --- verify matches ---
        assert pattern.match("src/main.py")

        # --- verify non-matches ---
        assert not pattern.match("src/main.txt")
        assert not pattern.match("src/other.py")

    def test_literals_with_slashes(self) -> None:
        """Forward slashes are literal path separators."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/test/main.py")

        # --- verify matches ---
        assert pattern.match("src/test/main.py")

        # --- verify non-matches ---
        assert not pattern.match("src/main.py")
        assert not pattern.match("src/test/sub/main.py")

    def test_literals_with_dashes_and_underscores(self) -> None:
        """Dashes and underscores are literal."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file-name_test.py")

        # --- verify matches ---
        assert pattern.match("file-name_test.py")

        # --- verify non-matches ---
        assert not pattern.match("file_name_test.py")
        assert not pattern.match("file-nametest.py")


class TestCompileGlobRecursiveEdgeCases:
    """Test edge cases: unmatched brackets, escaped characters, empty patterns."""

    def test_unmatched_opening_bracket_treated_as_literal(self) -> None:
        """Unmatched [ is treated as a literal [ (escaped)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[.py")

        # --- verify matches ---
        assert pattern.match("file[.py")

        # --- verify non-matches ---
        assert not pattern.match("file0.py")  # [0] would be a class

    def test_unmatched_bracket_with_closing_bracket_later(self) -> None:
        """[ without matching ] is treated as literal."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file[abc")

        # --- verify matches literal [ ---
        assert pattern.match("file[abc")

        # --- verify non-matches ---
        assert not pattern.match("fileabc")

    def test_escaped_regex_metacharacters(self) -> None:
        """Regex metacharacters like . + ^ $ etc. are escaped."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file.test.py")

        # --- verify matches ---
        assert pattern.match("file.test.py")

        # --- verify non-matches (. should not match any char in regex) ---
        assert not pattern.match("fileXtestXpy")

    def test_escaped_plus_sign(self) -> None:
        """+ is escaped (not a regex quantifier)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file+test.py")

        # --- verify matches ---
        assert pattern.match("file+test.py")

        # --- verify non-matches ---
        assert not pattern.match("filetest.py")  # + doesn't mean one-or-more

    def test_escaped_caret(self) -> None:
        """^ is escaped (not a regex anchor)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file^test.py")

        # --- verify matches ---
        assert pattern.match("file^test.py")

        # --- verify non-matches ---
        assert not pattern.match("filetesttest.py")

    def test_escaped_dollar_sign(self) -> None:
        """$ is escaped (not a regex anchor)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file$test.py")

        # --- verify matches ---
        assert pattern.match("file$test.py")

        # --- verify non-matches ---
        assert not pattern.match("file test.py")

    def test_escaped_backslash(self) -> None:
        """Backslash is escaped."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file\\test.py")

        # --- verify matches ---
        assert pattern.match("file\\test.py")

        # --- verify non-matches ---
        assert not pattern.match("file/test.py")

    def test_escaped_pipe_char(self) -> None:
        """| is escaped (not a regex alternation operator)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("file|test.py")

        # --- verify matches ---
        assert pattern.match("file|test.py")

        # --- verify non-matches ---
        assert not pattern.match("filetest.py")

    def test_empty_pattern(self) -> None:
        """Empty pattern should match only empty string."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("")

        # --- verify matches ---
        assert pattern.match("")

        # --- verify non-matches ---
        assert not pattern.match("a")
        assert not pattern.match("file.py")

    def test_run_of_three_stars_collapses_to_double_star(self) -> None:
        """*** collapses to ** (treated as recursive)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src***/main.py")

        # --- verify matches (*** treated as **) ---
        assert pattern.match("src/a/main.py")
        assert pattern.match("src/a/b/c/main.py")

    def test_run_of_four_stars_collapses_to_double_star(self) -> None:
        """**** collapses to ** (treated as recursive)."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src****/main.py")

        # --- verify matches (any run >= 2 is **) ---
        assert pattern.match("src/a/main.py")
        assert pattern.match("src/a/b/c/main.py")

    def test_mixed_stars_and_other_chars(self) -> None:
        """Complex pattern with * and ** mixed."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/**/test_*.py")

        # --- verify matches ---
        assert pattern.match("src/a/test_main.py")
        assert pattern.match("src/a/b/test_foo.py")

        # --- verify non-matches ---
        assert not pattern.match("src/a/main.py")  # missing test_
        assert not pattern.match("src/test/main.py")  # ** requires segment


class TestCompileGlobRecursiveCaching:
    """Test @lru_cache behavior with maxsize=512."""

    def test_lru_cache_is_enabled(self) -> None:
        """Function should have @lru_cache decorator."""
        # --- verify ---
        assert isinstance(mod_utils._compile_glob_recursive, _lru_cache_wrapper)

    def test_lru_cache_has_correct_maxsize(self) -> None:
        """lru_cache should have correct maxsize."""
        # --- verify ---
        assert (
            mod_utils._compile_glob_recursive.cache_info().maxsize
            == _COMPILE_GLOB_RECURSIVE_CACHE_MAXSIZE
        )

    def test_cache_returns_same_compiled_pattern(self) -> None:
        """Same pattern string should return same compiled regex object."""
        # --- setup ---
        pattern_str = "src/**/main.py"

        # --- execute ---
        pattern1 = mod_utils._compile_glob_recursive(pattern_str)
        pattern2 = mod_utils._compile_glob_recursive(pattern_str)

        # --- verify (same object in cache) ---
        assert pattern1 is pattern2

    def test_cache_stores_different_patterns(self) -> None:
        """Different patterns should produce different compiled regexes."""
        # --- execute ---
        pattern1 = mod_utils._compile_glob_recursive("src/*.py")
        pattern2 = mod_utils._compile_glob_recursive("test/*.py")

        # --- verify ---
        assert pattern1 is not pattern2

    def test_cache_info_tracks_hits_and_misses(self) -> None:
        """Cache info should track hits and misses."""
        # --- setup ---
        mod_utils._compile_glob_recursive.cache_clear()

        # --- execute: first call is a miss ---
        mod_utils._compile_glob_recursive("pattern1")
        info1 = mod_utils._compile_glob_recursive.cache_info()
        assert info1.hits == 0
        assert info1.misses == 1

        # --- execute: second call is a hit ---
        mod_utils._compile_glob_recursive("pattern1")
        info2 = mod_utils._compile_glob_recursive.cache_info()
        assert info2.hits == 1
        assert info2.misses == 1

        # --- cleanup ---
        mod_utils._compile_glob_recursive.cache_clear()

    def test_cache_clear_works(self) -> None:
        """cache_clear() should reset cache."""
        # --- setup ---
        mod_utils._compile_glob_recursive.cache_clear()

        # --- execute ---
        mod_utils._compile_glob_recursive("pattern")
        info_before = mod_utils._compile_glob_recursive.cache_info()
        mod_utils._compile_glob_recursive.cache_clear()
        info_after = mod_utils._compile_glob_recursive.cache_info()

        # --- verify ---
        assert info_before.currsize > 0
        assert info_after.currsize == 0

        # --- cleanup ---
        mod_utils._compile_glob_recursive.cache_clear()


class TestCompileGlobRecursiveRegexAnchorAndMode:
    """Test regex anchoring and dotall mode."""

    def test_pattern_is_anchored_at_end_with_z(self) -> None:
        r"""Pattern should be anchored with \Z to end of string."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/main.py")

        # --- verify matches ---
        assert pattern.match("src/main.py")

        # --- verify does not match partial ---
        assert not pattern.match("src/main.pyx")  # extra char
        assert not pattern.match("src/main.py extra")

    def test_pattern_start_is_anchored_implicitly(self) -> None:
        """match() implicitly anchors at start."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("main.py")

        # --- verify matches at start ---
        assert pattern.match("main.py")

        # --- verify does not match at end only ---
        # match() anchors to start, so this shouldn't match
        assert not pattern.match("src/main.py")

    def test_dotall_mode_allows_dot_to_match_newlines(self) -> None:
        """Dotall mode ((?s:...)) allows . to match newlines."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/**")

        # --- verify matches across newlines ---
        # ** becomes .* which can match newlines in dotall mode
        assert pattern.match("src/a\nb")

    def test_case_sensitive_matching(self) -> None:
        """Patterns are case-sensitive."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("Main.py")

        # --- verify case matters ---
        assert pattern.match("Main.py")
        assert not pattern.match("main.py")
        assert not pattern.match("MAIN.py")


class TestCompileGlobRecursiveComplexPatterns:
    """Test real-world complex patterns."""

    def test_python_gitignore_pattern(self) -> None:
        """Pattern for Python build artifacts: __pycache__/**."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("__pycache__/**")

        # --- verify matches ---
        assert pattern.match("__pycache__/module.pyc")
        assert pattern.match("__pycache__/sub/module.pyc")

        # --- verify non-matches ---
        assert not pattern.match("module/pycache__/file.pyc")

    def test_node_modules_pattern(self) -> None:
        """Pattern for node_modules: **/node_modules/**."""
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("**/node_modules/**")

        # --- verify matches ---
        assert pattern.match("app/node_modules/package/index.js")
        assert pattern.match("src/lib/node_modules/pkg/file.js")

    def test_build_output_pattern(self) -> None:
        """Pattern for build outputs: dist/**/*.js."""
        # Note: ** requires at least one path segment, so dist/**/*.js
        # won't match dist/main.js. It requires dist/<something>/something.js
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("dist/**/*.js")

        # --- verify matches (** requires at least one segment) ---
        assert pattern.match("dist/lib/util.js")
        assert pattern.match("dist/lib/sub/deep.js")

        # --- verify non-matches ---
        assert not pattern.match("dist/main.js")  # ** requires segment
        assert not pattern.match("dist/main.css")

    def test_test_file_pattern(self) -> None:
        """Pattern for test files: **/test_*.py."""
        # Note: ** requires at least one path segment, so **/test_*.py
        # won't match test_main.py directly. It needs at least one directory.
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("**/test_*.py")

        # --- verify matches (** requires at least one segment) ---
        assert pattern.match("tests/test_main.py")
        assert pattern.match("src/tests/unit/test_foo.py")

        # --- verify non-matches ---
        assert not pattern.match("test_main.py")  # ** requires at least one segment
        assert not pattern.match("main.py")
        assert not pattern.match("testing.py")

    def test_nested_source_pattern(self) -> None:
        """Pattern matching nested sources: src/**/*.py."""
        # Note: ** requires at least one path segment, so src/**/*.py
        # won't match src/main.py directly. It requires src/<dir>/something.py
        # --- execute ---
        pattern = mod_utils._compile_glob_recursive("src/**/*.py")

        # --- verify matches (** requires at least one segment) ---
        assert pattern.match("src/lib/util.py")
        assert pattern.match("src/lib/sub/deep.py")

        # --- verify non-matches ---
        assert not pattern.match("src/main.py")  # ** requires at least one segment
        assert not pattern.match("src/lib/util.ts")
        assert not pattern.match("test/main.py")
