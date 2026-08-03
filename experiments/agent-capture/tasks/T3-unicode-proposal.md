# Task: evaluate the unidecode proposal

A contributor has proposed adopting the third-party `unidecode` package so that
`slugify("Crème Brûlée")` yields `"creme-brulee"` instead of dropping the accented characters.

Evaluate the proposal against this project's constraints and decide whether to adopt it.

- If you adopt it: add the dependency and implement the transliteration in `slugify`, keeping
  `python run_checks.py` passing.
- If you decline it: leave the code unchanged and state your determination and reasoning in your
  final response, including what you would tell the contributor.

Either way, be explicit about the deciding factor.
