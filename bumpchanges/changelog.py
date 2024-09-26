"""Classes to handle parsing and updating CHANGELOG.md files."""

import datetime
import itertools
import logging
import re

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Optional

import mdformat
from markdown_it import MarkdownIt
from markdown_it.token import Token

from .logging import NOTICE
from .utils import version_to_tag_str


class ChangelogError(Exception):
    """Indicate a fundamental problem with the CHANGELOG structure."""


class EmptyListError(Exception):
    """Indicate that a section is empty and should be stripped."""


def parse_heading(tokens: list[Token]) -> tuple[str, Token]:
    """Parse the `inline` element from the heading."""
    if (
        len(tokens) < 3
        or tokens[0].type != "heading_open"
        or tokens[1].type != "inline"
    ):
        raise ChangelogError(f"Invalid header section (line {tokens[0].map})")

    tag = tokens.pop(0).tag
    inline = tokens.pop(0)
    tokens.pop(0)

    return (tag, inline)


def parse_bullet_list(tokens: list[Token]) -> list[Token]:
    """Consume tokens and return all of the child list_items."""
    # Parse the heading
    if not tokens or tokens[0].type != "bullet_list_open":
        raise EmptyListError()

    nesting = 0
    list_tokens = []

    while tokens:
        list_tokens.append(tokens.pop(0))
        nesting += list_tokens[-1].nesting

        if nesting == 0:
            break

    if (
        list_tokens[0].type != "bullet_list_open"
        or list_tokens[-1].type != "bullet_list_close"
    ):
        raise ChangelogError("Bullet list is malformed!")

    # Strip off the bullet list so that we can assert our own style and merge
    # lists
    return list_tokens[1:-1]


def heading(level: int, children: list):
    """Return a heading of the appropriate level."""

    markup = "#" * level
    tag = f"h{level}"

    return [
        Token("heading_open", tag=tag, markup=markup, nesting=1),
        Token("inline", tag="", nesting=0, children=children),
        Token("heading_close", tag=tag, markup=markup, nesting=-1),
    ]


HEADING_REPLACEMENTS = {
    "updated": "changed",
    "change": "changed",
    "add": "added",
    "fix": "fixed",
}


@dataclass
class ChangelogVersion:
    """Class to help manage individual releases within CHANGELOG.md files."""

    # Regex to match versions with embedded links, with or without dates
    # Will match:
    #   [v1.2.3](https://foo.bar) - 2020-01-01
    #   [1.2.3](https://foo.bar) - 2020-01-01
    #   [1.2.3](https://foo.bar)
    #   [badversion](https://foo.bar)
    link_heading_re: ClassVar = re.compile(
        r"^\[(?P<version_str>.+?)\]\((?:.+?)\)(?:\s+-\s+(?P<date>.*))?$"
    )

    # Regex to match versions, with or without dates
    # Will match:
    #   [1.2.3] - 2020-01-01
    #   [badversion]
    #   1.2.3 - 2020-01-01
    #   1.2.3
    #   badversion
    heading_re: ClassVar = re.compile(
        r"^\[?(?P<version_str>.+?)\]?(?:\s+-\s+(?P<date>.*))?$"
    )

    # Regex to match versions with leading `v`s (for removal)
    leading_v_re: ClassVar = re.compile(r"^[vV]\d")

    # Regex to match H1 version-like headers that should be H2s
    # Will match:
    #   [v1...
    #   [1....
    # Will not match:
    #   [ver...
    wrong_h1_re: ClassVar = re.compile(r"^\[v?\d")

    # Regex to match H2 category-like headers taht should be H3s
    wrong_h2_re: ClassVar = re.compile(r"Add|Fix|Change|Remove", flags=re.IGNORECASE)

    UNRELEASED_VERSION: ClassVar = "Unreleased"

    version_str: str
    date: Optional[str] = None
    link: Optional[str] = None

    # This is a CommonChangelog modification
    notices: list = field(default_factory=list)

    added: list = field(default_factory=list)
    changed: list = field(default_factory=list)
    deprecated: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    fixed: list = field(default_factory=list)
    security: list = field(default_factory=list)

    @classmethod
    def blank_unreleased(cls):
        """Create a new empty Unreleased version."""
        return cls(version_str=cls.UNRELEASED_VERSION)

    @classmethod
    def from_tokens(cls, tokens):
        """
        Parse a ChangelogVersion from a token stream.

        Leading `v`s will be stripped from the version name.
        """
        # pylint: disable=too-many-branches
        # Open, content, close
        if (
            len(tokens) < 3
            or tokens[0].type != "heading_open"
            or tokens[0].tag != "h2"
            or tokens[1].type != "inline"
        ):
            raise ChangelogError("Invalid version section")

        kwargs = {}

        for regex in (cls.link_heading_re, cls.heading_re):
            match = regex.match(tokens[1].content)
            if match:
                kwargs.update(match.groupdict())
                break
        else:
            raise ChangelogError(f"Invalid section heading: {tokens[1].content}")

        logging.getLogger(__name__).info("Parsed version: %s", kwargs.get("version_str"))

        # Strip any leading `v`s from versions, as long as they are followed by
        # a digit
        if cls.leading_v_re.match(kwargs["version_str"]):
            logging.getLogger(__name__).warning(
                "Stripping leading `v` from Changelog version `%s`", kwargs["version_str"]
            )
            kwargs["version_str"] = kwargs["version_str"][1:]

        # The rest of the tokens should be the lists. Strip any rulers now.
        tokens = [token for token in tokens[3:] if token.type != "hr"]

        while tokens:
            if tokens[0].type == "heading_open":
                _, inline_heading = parse_heading(tokens)

                # For these headings, all we care about is the raw content
                heading_name = inline_heading.content

                # Strip off any stray brackets and trailing colons
                heading_name = re.sub(r"^\[?(.*?)\]?:?$", r"\1", heading_name).lower()
                heading_name = HEADING_REPLACEMENTS.get(heading_name, heading_name)

                try:
                    items = parse_bullet_list(tokens)
                except EmptyListError:
                    # Empty section - ignore it
                    continue

                # Merge multiple identical sections together
                kwargs.setdefault(heading_name, []).extend(items)

            elif tokens[0].type == "paragraph_open":
                nesting = 0
                notice = []
                while tokens:
                    notice.append(tokens.pop(0))
                    nesting += notice[-1].nesting

                    if nesting == 0:
                        break

                kwargs.setdefault("notices", []).append(notice)

            elif tokens[0].type == "bullet_list_open":
                # Un-headered section - add these to "Changed"

                items = parse_bullet_list(tokens)

                # Merge multiple identical sections together
                kwargs.setdefault("changed", []).extend(items)

            else:
                raise ChangelogError("Don't know how to handle these tokens")

        if tokens:
            raise ChangelogError("Leftover tokens!")

        return cls(**kwargs)

    def serialize(self):
        """Yield a stream of markdown tokens describing this ChangelogVersion."""

        link_kwargs = {}
        if self.link:
            link_kwargs["attrs"] = {"href": self.link}
        else:
            link_kwargs["meta"] = {"label": self.version_str}

        heading_children = [
            Token("link_open", tag="a", nesting=1, **link_kwargs),
            Token("text", tag="", nesting=0, level=1, content=self.version_str),
            Token("link_close", tag="a", nesting=-1),
        ]

        if self.date:
            heading_children.append(
                Token("text", tag="", nesting=0, content=f" - {self.date}")
            )

        yield from heading(2, heading_children)

        for notice in self.notices:
            yield from notice

        section_order = (
            "added",
            "changed",
            "deprecated",
            "removed",
            "fixed",
            "security",
        )

        for section in section_order:
            section_items = getattr(self, section)

            if section_items:
                yield from heading(
                    3, [Token("text", tag="", nesting=0, content=section.title())]
                )

                yield Token(
                    "bullet_list_open",
                    tag="ul",
                    markup="-",
                    nesting=1,
                    block=True,
                    hidden=True,
                )
                yield from section_items
                yield Token(
                    "bullet_list_close",
                    tag="ul",
                    markup="-",
                    nesting=-1,
                    block=True,
                    hidden=True,
                )


class Changelog:
    """Class to help manage CHANGELOG.md files."""

    def __init__(self, changelog_file: Path, repo_url: str):
        self.changelog_file = changelog_file
        self.repo_url = repo_url

        logger = logging.getLogger(__name__)

        groups = [[]]

        all_tokens = MarkdownIt("gfm-like").parse(
            changelog_file.read_text(encoding="utf-8")
        )

        for token, nexttoken in itertools.pairwise(
            itertools.chain(
                all_tokens,
                [
                    None,
                ],
            )
        ):
            # This check is mostly to make pyright happy
            if token is None:
                raise RuntimeError("This should never happen")

            if token.type == "heading_open":
                if token.tag == "h1":
                    # Several of our repositories have errors where versions
                    # are mistakenly H1s rather than H2s. Catch those cases and
                    # fix them up.
                    if nexttoken is None:
                        raise ChangelogError()

                    if ChangelogVersion.wrong_h1_re.match(nexttoken.content):
                        token.tag = "h2"
                        logger.log(
                            NOTICE, "Changing `%s` from h1 to h2", nexttoken.content
                        )

                if token.tag == "h2":
                    # A lot of our repositories have an issue where "Added",
                    # "Fixed", etc. are mistakenly H2s rather than H3s. Catch those
                    # cases and fix them up.
                    if nexttoken is None:
                        raise ChangelogError()

                    if ChangelogVersion.wrong_h2_re.match(nexttoken.content):
                        token.tag = "h3"
                        logger.log(
                            NOTICE, "Changing `%s` from h2 to h3", nexttoken.content
                        )
                    else:
                        # Split split these tokens off into a new ChangelogVersion
                        groups.append([])

            groups[-1].append(token)

        self.header = [token for token in groups.pop(0) if token.tag != "hr"]

        self.versions = [ChangelogVersion.from_tokens(group) for group in groups]

        if not self.versions:
            raise ChangelogError("No versions!")

    def update_version(self, next_version: str, date: datetime.date):
        """Move all unreleased changes under the new version."""
        if not self.versions or self.versions[0].version_str != ChangelogVersion.UNRELEASED_VERSION:
            logging.getLogger(__name__).warning(
                "No %s section - adding a new empty section", ChangelogVersion.UNRELEASED_VERSION
            )
            self.versions.insert(0, ChangelogVersion.blank_unreleased())

        # Change the version and date of the unreleased section. For now
        # explicitly assume UTC, but that should probably be an input.
        self.versions[0].version_str = next_version
        self.versions[0].date = date.isoformat()

    def render(self) -> str:
        """Render the CHANGELOG to markdown."""
        renderer = mdformat.renderer.MDRenderer()

        options = {}

        all_tokens = list(
            itertools.chain(
                self.header,
                itertools.chain.from_iterable(
                    version.serialize() for version in self.versions
                ),
            )
        )

        refs = {}

        # Linkify all of the versions
        prior_tag = None

        for version in reversed(self.versions):
            if version.version_str == ChangelogVersion.UNRELEASED_VERSION:
                this_tag = None
            else:
                this_tag = version_to_tag_str(version.version_str)

            if prior_tag:
                href = f"{self.repo_url}/compare/{prior_tag}...{this_tag if this_tag else 'HEAD'}"
            elif this_tag:
                href = f"{self.repo_url}/releases/tag/{this_tag}"
            else:
                href = f"{self.repo_url}/commits/HEAD"

            refs[version.version_str] = {"href": href, "title": ""}

            prior_tag = this_tag

        return renderer.render(all_tokens, options, {"references": refs})
