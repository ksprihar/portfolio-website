"""
Language -> color map for the little dot next to a project's language
on the project cards / detail page.

Colors follow GitHub's own Linguist palette (the same colors GitHub uses
next to "Python", "JavaScript", etc. on a repo page), so the dot will
match what visitors already associate with each language. A handful of
languages GitHub doesn't officially color (like SQL) use a commonly-used
unofficial value instead — tweak freely to taste.

Usage:
    from lang_colors import LANG_COLORS, get_lang_color

    color = get_lang_color(project["language"])
"""

LANG_COLORS = {
    "Python": "#3572A5",
    "Jupyter Notebook": "#DA5B0B",
    "SQL": "#e38cd7",
    "PLpgSQL": "#336790",
    "R": "#198CE7",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Scala": "#c22d40",
    "Perl": "#0298c3",
    "Lua": "#000080",
    "Haskell": "#5e5086",
    "Elixir": "#6e4a7e",
    "Erlang": "#B83998",
    "Clojure": "#db5855",
    "F#": "#b845fc",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "Dockerfile": "#384d54",
    "Vue": "#41b883",
    "TeX": "#3D6117",
    "MATLAB": "#e16737",
    "Julia": "#a270ba",
    "Groovy": "#e69f56",
    "Objective-C": "#438eff",
    "Assembly": "#6E4C13",
    "CoffeeScript": "#244776",
    "Vim script": "#199f4b",
    "Markdown": "#083fa1",
    "TSQL": "#E38C00",
}

# Used for any language not in the map above, so the dot never breaks —
# just renders a neutral gray instead of a language-specific color.
DEFAULT_LANG_COLOR = "#8b8b8b"


def get_lang_color(language: str) -> str:
    """Look up a language's dot color, falling back to a neutral gray."""
    return LANG_COLORS.get(language, DEFAULT_LANG_COLOR)
