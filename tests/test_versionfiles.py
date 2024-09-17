"""Tests for the bumpchanges module."""

from bumpchanges.updatefiles import update_file

import pytest


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
