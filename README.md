# dev-workflow

One build workflow for AI coding agents, written for Claude Code and assembled from other people's skills plus one of mine. Matt Pocock's skills decide what happens next. My `changeable-software` skill decides what good looks like at each step. A workflow file ties them together and adds parallel ticket waves, so independent tickets build at the same time. I built it with an AI pair, which seemed only fair for a workflow about building with one.

The full walkthrough is in [docs/workflow-guide.md](docs/workflow-guide.md). This page covers what's in the box, who made it, and how to install it.

## What's in the repo

| Path | What it is |
| --- | --- |
| `workflow/dev-workflow.md` | The workflow itself. Claude Code loads it into every session through an `@` import in `~/.claude/CLAUDE.md`. |
| `skills/changeable-software/` | The standards layer: design laws, testing standard, review checklist, review mode. Original to this repo. |
| `cloud/dev-workflow/SKILL.md` | The same workflow wrapped as a skill, for Claude Code on the web, where `~/.claude/CLAUDE.md` isn't loaded. |
| `install.sh` | Installs everything below at user level, so every project gets it. |
| `docs/workflow-guide.md` | The long-form explanation. |

## Credits

Nothing from the projects below is copied into this repo. The installer fetches each one from its own source, so the authors' current versions and licences apply.

| Project | Author | Licence | What it supplies |
| --- | --- | --- | --- |
| [mattpocock/skills](https://github.com/mattpocock/skills) | [Matt Pocock](https://www.aihero.dev) | MIT | The whole sequence: `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`, `/triage`, `/wayfinder`, `/domain-modeling`, `/codebase-design` and the rest. Built against v1.2.3. |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | [Addy Osmani](https://github.com/addyosmani), with Federico Bartoli and Joan León | MIT | Six skills for after the commit: `shipping-and-launch`, `observability-and-instrumentation`, `security-and-hardening`, `deprecation-and-migration`, `ci-cd-and-automation`, `performance-optimization`. |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | Vercel | see repo | The `npx skills` installer that `install.sh` uses. |

`changeable-software` has no upstream repo. I wrote it here, as a distillation of these sources, which are credited inside the skill too:

- John Ousterhout, *A Philosophy of Software Design*: structure, complexity, deep modules.
- Andrew Hunt and David Thomas, *The Pragmatic Programmer*: pragmatic practice, root causes, broken windows.
- Matt Pocock: software design for AI-assisted development.
- Sandeep Swadia: systems thinking and decision-making in complex systems.
- Dave Snowden: the Cynefin framework, used to pick a method by the kind of problem.

## Install

You need [Claude Code](https://docs.claude.com/en/docs/claude-code/overview), git and Node.js.

```bash
git clone https://github.com/weezyf1995-boop/dev-workflow.git
cd dev-workflow
bash install.sh
```

Then, once in every repo you build in, open Claude Code and run `/setup-matt-pocock-skills`. It records your issue tracker and label names, which `/to-tickets` and `/triage` need.

Check it worked by running `/memory` in a session: `dev-workflow.md` should be in the list.

**Don't also install the Pocock or Addy Osmani plugins.** The installer copies skills in by name. Adding either plugin on top gives you every skill twice, and Addy's full plugin brings back nineteen skills that compete with the Pocock flow.

**Claude Code on the web.** Cloud sessions don't read your local `~/.claude`. Add `skills/changeable-software` and `cloud/dev-workflow` to your account as skills, and install the Pocock and Addy Osmani skills there the same way.

## Other AI coding agents

The skills travel; the glue is written for Claude Code. Pocock's and Osmani's skills are plain Markdown that Codex, Cursor and other agents can use (`npx skills add` installs them for any supported agent through `-a <agent>`), and changeable-software is the same. The workflow file leans on Claude Code features: the `@` import in `CLAUDE.md`, subagents in git worktrees for parallel tickets, `/memory`, and the Opus and Sonnet model rule. On another agent, load `workflow/dev-workflow.md` the way that agent loads instructions (`AGENTS.md`, for example) and expect to adapt those parts. `install.sh` targets Claude Code only.

## Updating

Re-run `bash install.sh`. It pulls the latest third-party skills and moves any old copy of this repo's files to `~/.claude/skills-backup/` before replacing it.

## Licence

The files in this repo are MIT licensed: see [LICENSE](LICENSE). The skills the installer fetches carry their own licences in their own repos.
