import io
import json

import pytest

from nix_auto_follow.cli import (
    LockFile,
    Node,
    check_lock_file,
    start,
    update_flake_lock,
)


@pytest.mark.parametrize(
    "node, expected_url",
    [
        (
            Node.from_dict(
                {
                    "original": {
                        "owner": "nixos",
                        "ref": "nixos-24.05",
                        "repo": "nixpkgs",
                        "type": "github",
                    }
                }
            ),
            "github:nixos/nixpkgs/nixos-24.05",
        ),
        (
            Node.from_dict(
                {"original": {"owner": "nixos", "repo": "nixpkgs", "type": "github"}}
            ),
            "github:nixos/nixpkgs",
        ),
        (
            Node.from_dict({"original": {"id": "nixpkgs", "type": "indirect"}}),
            "nixpkgs",
        ),
        (
            Node.from_dict({"original": {"id": "nixpkgs", "type": "indirect"}}),
            "nixpkgs",
        ),
        (
            Node.from_dict(
                {
                    "original": {
                        "id": "nixpkgs",
                        "ref": "nixos-unstable",
                        "type": "indirect",
                    }
                }
            ),
            "nixpkgs/nixos-unstable",
        ),
        (
            Node.from_dict(
                {
                    "original": {
                        "id": "nixpkgs",
                        "ref": "nixos-unstable",
                        "rev": "23.11",
                        "type": "indirect",
                    }
                }
            ),
            "nixpkgs/nixos-unstable/23.11",
        ),
    ],
)
def test_get_url_for_node(node: Node, expected_url: str) -> None:
    assert node.get_url() == expected_url


def test_simple_follow_flake() -> None:
    with open("tests/fixtures/has_follow.json") as f:
        flake_lock = LockFile.from_dict(json.load(f))
        # precondition:
        assert flake_lock.nodes["nixpkgs"] != flake_lock.nodes["nixpkgs_2"]
        modified_lock = update_flake_lock(flake_lock)
        # postcondition:
        assert modified_lock.nodes["nixpkgs"] == modified_lock.nodes["nixpkgs_2"]


def test_simple_root_has_follow_flake() -> None:
    with open("tests/fixtures/root_has_follow.json") as f:
        flake_lock = LockFile.from_dict(json.load(f))
        # precondition:
        assert flake_lock.nodes["nixpkgs"] != flake_lock.nodes["nixpkgs_2"]
        modified_lock = update_flake_lock(flake_lock)
        # postcondition:
        assert modified_lock.nodes["nixpkgs"] == modified_lock.nodes["nixpkgs_2"]


def test_full_start() -> None:
    with open("tests/fixtures/root_has_follow.json") as f:
        stdout = io.StringIO()
        start(stdin=f, stdout=stdout)
        flake_lock = LockFile.from_dict(json.loads(stdout.getvalue()))
        assert flake_lock.root == "root"


@pytest.mark.parametrize(
    "filename",
    [
        "tests/fixtures/has_follow.json",
        "tests/fixtures/root_has_follow.json",
    ],
)
def test_check_lock_file_success(filename: str) -> None:
    with open(filename) as f:
        flake_lock = LockFile.from_dict(json.load(f))
        assert not check_lock_file(flake_lock)
        # fix it
        modified_lock = update_flake_lock(flake_lock)
        assert check_lock_file(modified_lock)


def test_check_lock_file_fail() -> None:
    """
    This lockfile fails because there are follows beyond the root.
    We cann't figure out which follow to use so the user needs to elevate
    one to the root.
    """
    with open("tests/fixtures/non_root_follow.json") as f:
        flake_lock = LockFile.from_dict(json.load(f))
        assert not check_lock_file(flake_lock)
        # try to fix it
        modified_lock = update_flake_lock(flake_lock)
        # still fails
        assert not check_lock_file(modified_lock)
