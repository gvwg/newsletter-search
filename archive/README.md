# Archive

## publish-newsletter-skill (deprecated 2026-09-27)

A Claude Code skill that published a new issue on gvwg.ca (Newsletters page
entry and News article) by driving the maintainer's logged-in Chrome session
(`claude --chrome`). It worked in a full rehearsal on 2026-09-25 but was too
slow and fiddly to use. It is kept here, outside `.claude/skills/`, so Claude
Code no longer offers it, until there is a way to do this without Claude in
Chrome.

Since the redesign, the newsletters list at newsletters.gvwg.ca updates itself
from the CE Newsletters folder, so only the News post is still manual.
`scripts/publish_prep.py` (which the skill used) still works on its own: it
prepares the News article body and cover image in `out/publish/<id>/` for
pasting by hand.

To bring the skill back, move the folder to `.claude/skills/publish-newsletter/`.
