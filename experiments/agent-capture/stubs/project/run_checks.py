"""Plain-assert checks for strutil. Run: python run_checks.py"""

from strutil import load_settings, slugify, truncate


def main() -> None:
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  --Already--Slugged--  ") == "already-slugged"
    assert truncate("abcdef", 10) == "abcdef"
    assert truncate("abcdefghij", 8) == "abcde..."
    assert truncate("abcd", 2) == "ab"
    settings = load_settings()
    assert settings["max_title_length"] == 80
    assert settings["slug_separator"] == "-"
    print("all checks passed")


if __name__ == "__main__":
    main()
