"""Tests for the bumpchanges module."""

import pytest

from bumpchanges.updatefiles import update_file


# A list of tuples. The first element represents the existing version string in
# a file, and the second represents the expected text once the version has been
# updated to `2.3.4`.
version_strings = [
    (
        # Python-style, double-quoted
        '''__version__ = "1.1.0"''',
        '''__version__ = "2.3.4"''',
    ),
    (
        # Python-style, single quotes
        """__version__ = '1.1.0'""",
        """__version__ = '2.3.4'""",
    ),
    (
        # Python-style, no quotes
        """__version__ = 1.1.0""",
        """__version__ = 2.3.4""",
    ),
    (
        # Python-style with typing
        """__version__: str = '1.1.0'""",
        """__version__: str = '2.3.4'""",
    ),
    (
        # Python-style with typing, double-quotes
        '''__version__:str= "1.1.0"''',
        '''__version__:str= "2.3.4"''',
    ),
    (
        # Plain string version
        '''version = "1.1.0"''',
        '''version = "2.3.4"''',
    ),
    (
        # Version key double quoted
        '''"version" = "1.1.0"''',
        '''"version" = "2.3.4"''',
    ),
    (
        # Version key single quoted
        """'version' = '1.1.0'""",
        """'version' = '2.3.4'""",
    ),
    (
        # Trailing comma
        """version = "1.1.0",""",
        """version = "2.3.4",""",
    ),
    (
        # Extra spaces
        """   version   =    "1.1.0"    """,
        """   version   =    "2.3.4"    """,
    ),
    (
        # No spaces
        '''version="1.1.0"''',
        '''version="2.3.4"''',
    ),
    (
        # Capitalization
        """Version=1.2.3""",
        """Version=2.3.4""",
    ),
    (
        # Comments
        """VERSION=foo  # comments""",
        """VERSION=2.3.4  # comments""",
    ),
    (
        # Colon separator
        """version: 1.2.3""",
        """version: 2.3.4""",
    ),
    (
        # Space separator
        """version 90304""",
        """version 2.3.4""",
    ),
    (
        # Leading prefix
        """PluginVersion: 0.6.0""",
        """PluginVersion: 2.3.4""",
    ),
    (
        # Leading prefix and dash
        """Plugin-Version: 0.6.0""",
        """Plugin-Version: 2.3.4""",
    ),
    (
        # Almost but-not-quite Manifest-Version
        """anifest-Version: 0.6.0""",
        """anifest-Version: 2.3.4""",
    ),
]


# A list of version-like strings that will _not_ be matched.
unmatched_strings = [
    # Java JAR manifest version
    "Manifest-Version: 1.0",
    "manifest-version: 1.0",
]


@pytest.mark.parametrize("original,expected", version_strings)
def test_version_updates(tmp_path, original, expected):
    """Confirm that the file contents are updated correctly."""
    version = "2.3.4"

    # Test the text alone (no trailing newline
    version_file = tmp_path / "version.txt"
    version_file.write_text(original, encoding="utf-8")
    update_file(version, version_file)
    assert version_file.read_text(encoding="utf-8") == expected

@pytest.mark.parametrize("unmatched_line", unmatched_strings)
def test_negative_matches(tmp_path, unmatched_line):
    """Confirm that the invalid version paths are _not_ matched."""
    version = "2.3.4"

    # Test the text alone (no trailing newline
    version_file = tmp_path / "version.txt"
    version_file.write_text(unmatched_line, encoding="utf-8")

    with pytest.raises(ValueError):
        update_file(version, version_file)
