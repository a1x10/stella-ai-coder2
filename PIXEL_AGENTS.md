# Stella AI Agent 3.8 Enterprise Autopilot and Pixel Agents

**Stella AI Agent 3.8 Enterprise Autopilot Edition** integrates with Pixel Agents through a local transcript bridge, an Autopilot operator log, and a generated HTML live-viewer. The public Pixel Agents README describes the primary user path as a VS Code extension and documents source installation with `git clone`, `npm install`, `cd webview-ui && npm install`, and `npm run build`.[1] Stella therefore does not depend on private internals; it writes compatible observational files and offers a safe helper for opening VS Code or preparing Pixel Agents source locally.

## How the bridge works

When Stella starts, it creates a Pixel-compatible transcript under `~/.claude/projects`. The exact path is visible with the `/pixel` command. Stella also keeps its own native `.stella/sessions` history and Autopilot writes `.stella/operator_actions.jsonl`, so the Pixel bridge is additive and does not replace internal session logging.

| Stella event | JSONL record written for Pixel Agents |
|---|---|
| User sends a prompt | `type: user` with text content. |
| Assistant replies with text | `type: assistant` with a text block. |
| Assistant calls a tool | `type: assistant` with a `tool_use` block. |
| Tool returns a result | `type: user` with a `tool_result` block. |
| Turn ends | `type: system`, `subtype: turn_duration`. |
| Autopilot/Desktop Operator action | `.stella/operator_actions.jsonl` event mirrored into the live-viewer. |

The bridge is intentionally observational. It does not modify Pixel Agents source code, does not require private Claude Code internals, and does not send project data anywhere by itself.

## Usage

Run Stella in a project and type:

```text
/pixel
```

Stella will print the current JSONL path and the Autopilot live-viewer path, usually similar to this:

```text
~/.claude/projects/stella-my-project-7a1c0e2d98e4f6b1/stella-20260524-120000-a1b2c3d4.jsonl
./.stella/live_actions.html
```

Then use one of the workflows below.

| Workflow | When to use it | Stella behavior |
|---|---|---|
| VS Code extension | You want the normal Pixel Agents user experience. | If the `code` command exists and you approve, Stella opens the current project in VS Code. |
| Source build | You want to inspect, develop, or try standalone/source behavior. | If `git` and `npm` exist and you approve, Stella clones or updates `https://github.com/pixel-agents-hq/pixel-agents.git` under `~/.stella-ai-coder/pixel-agents`, runs `npm install`, installs `webview-ui`, and runs `npm run build`. |
| Manual JSONL | You only need the transcript path. | Stella prints the JSONL file path and leaves the rest to the user. |
| Autopilot live-viewer | You want to watch what Stella did in the current project. | `live_actions_viewer` creates `.stella/live_actions.html` with recent Pixel and operator events. |

## First-run helper

On first launch Stella shows a small informational panel explaining that Pixel Agents can be prepared through VS Code or source setup. This is only a prompt; Stella does not install or clone anything without explicit approval.

The one-time marker is:

```text
~/.stella-ai-coder/.pixel_first_run_checked
```

To suppress the prompt in automated environments, set:

```bash
export STELLA_SKIP_PIXEL_PROMPT=1
```

## What `/pixel` can do

The `/pixel` command reports the active transcript, operator log and live-viewer. The helper can open VS Code, clone/update the Pixel Agents repository, and run the documented build steps. Build logs are captured and returned in the Stella tool result so failures are visible to the user. For Autopilot and Desktop Operator tasks, `live_actions_viewer` can be called at any time to regenerate the HTML viewer from current logs, including screen/app-control events recorded by Stella.

> Stella does not pretend that a command exists unless it is available in the local environment. The helper checks for `code`, `git`, and `npm` and degrades gracefully when they are missing.

## Safety

The Pixel bridge writes local JSONL files only. The optional source setup downloads code from GitHub and runs `npm install`/`npm run build`; Stella treats that path as a risky action and asks for confirmation. The Autopilot viewer is local HTML generated from local logs. Any further sharing or telemetry depends on the user’s VS Code installation, extensions, npm packages, and local environment.

## References

[1]: https://github.com/pixel-agents-hq/pixel-agents "GitHub — pixel-agents-hq/pixel-agents"
