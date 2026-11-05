# UX Audit Agent

An AI agent that does a quick usability review of any website.

Give it a URL. It reads the home page, **decides on its own** which other pages matter most for the main user journey (pricing, sign up, contact…), reads those, and writes a heuristic audit based on [Nielsen's 10 usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/). The audit ranks issues by severity and suggests concrete fixes.

Built by a product designer to explore how AI agents can support everyday UX work.

## Example

```
$ python agent.py https://example.com
Auditing https://example.com ...
  Reading https://example.com
  Reading https://example.com/pricing
  Reading https://example.com/signup
  Report written to report.md
Done.
```

The report lands in `report.md`: a summary, the top 5 issues (heuristic, page, why it matters, fix, severity), what works well, and quick wins.

## How it works

An agent is an AI model running in a loop with tools it can choose to use:

```
Goal: "Audit this site"
   ↓
Claude thinks → picks a tool → sees the result → thinks again → …
   ↓
Done: calls save_report
```

This agent has two tools:

| Tool | What it does |
|---|---|
| `fetch_page` | Reads a page: title, headings, buttons, form fields, text, links, images missing alt text |
| `save_report` | Writes the final audit to `report.md` |

The design decisions live in plain English in `SYSTEM_PROMPT` inside [`agent.py`](agent.py): the audit process, the report format, and a page limit so it stays fast and cheap.

## Run it yourself

1. Install [Python 3.10+](https://www.python.org/downloads/).
2. Get an API key at [console.anthropic.com](https://console.anthropic.com).
3. In a terminal, in this folder:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"     # Windows: set ANTHROPIC_API_KEY=your-key-here
python agent.py https://your-site.com
```

One audit costs a few cents.

## Limitations

- It reads page **text and structure**, not visuals, so it can't judge layout, colour contrast or spacing.
- Sites that build their content with JavaScript may look nearly empty to it.
- It's a first pass to speed up a review, not a replacement for testing with real users.

## Ideas for next versions

- Add screenshots so it can review visual design
- Check colour contrast for accessibility (WCAG)
- Compare two competitor sites side by side

## License

MIT
