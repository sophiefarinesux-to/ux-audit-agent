"""
UX Audit Agent
--------------
Give it a website. It decides which pages to read, reviews them against
Nielsen's 10 usability heuristics, and writes a Markdown report.

Run:  python agent.py https://example.com
"""

import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

import anthropic

MODEL = "claude-sonnet-5-5"
MAX_PAGES = 4  # keeps the audit quick and cheap

# ---------------------------------------------------------------------------
# 1. The agent's "personality" and job description
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are a senior UX designer doing a quick heuristic audit.

Process:
1. Fetch the home page the user gives you.
2. Pick up to {MAX_PAGES - 1} more pages that matter most for the main user
   journey (e.g. pricing, sign up, product, contact). Fetch them.
3. Evaluate what you saw against Nielsen's 10 usability heuristics.
4. Call save_report once with the final report.

Report format (Markdown):
- # UX Audit: <site name>
- ## Summary (3 sentences max)
- ## Top 5 issues — for each: heuristic, page, what's wrong, why it matters,
  a concrete fix, and severity (High / Medium / Low)
- ## What works well (3 bullets)
- ## Quick wins (3 bullets)

You only see page text and links, not visuals. Say so where it limits you,
and never invent things you could not see."""

# ---------------------------------------------------------------------------
# 2. The tools the agent is allowed to use
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "fetch_page",
        "description": "Fetch a web page. Returns its title, headings, "
                       "buttons, form fields, visible text and links.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "save_report",
        "description": "Save the final audit report as Markdown. Call once, at the end.",
        "input_schema": {
            "type": "object",
            "properties": {"markdown": {"type": "string"}},
            "required": ["markdown"],
        },
    },
]


class PageReader(HTMLParser):
    """Pulls out the parts of a page a UX reviewer cares about."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.title, self.headings, self.buttons = "", [], []
        self.fields, self.links, self.text = [], [], []
        self._tag, self._skip = None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._tag = tag
        if tag in ("script", "style", "svg", "noscript"):
            self._skip += 1
        elif tag == "a" and a.get("href"):
            self.links.append(urljoin(self.base_url, a["href"]))
        elif tag in ("input", "select", "textarea"):
            label = a.get("aria-label") or a.get("placeholder") or a.get("name") or "?"
            self.fields.append(f"{a.get('type', tag)}: {label}")
        elif tag == "img" and not a.get("alt"):
            self.text.append("[image with no alt text]")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        data = data.strip()
        if not data or self._skip:
            return
        if self._tag == "title":
            self.title = data
        elif self._tag in ("h1", "h2", "h3"):
            self.headings.append(f"{self._tag}: {data}")
        elif self._tag == "button":
            self.buttons.append(data)
        self.text.append(data)


def fetch_page(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ux-audit-agent"})
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    except Exception as e:
        return f"Could not fetch {url}: {e}"

    p = PageReader(url)
    p.feed(html)
    links = list(dict.fromkeys(p.links))[:60]  # unique, capped
    return (
        f"URL: {url}\nTITLE: {p.title}\n\n"
        f"HEADINGS:\n" + "\n".join(p.headings[:40]) + "\n\n"
        f"BUTTONS: {', '.join(p.buttons[:30])}\n"
        f"FORM FIELDS: {', '.join(p.fields[:30])}\n\n"
        f"TEXT:\n{' '.join(p.text)[:6000]}\n\n"
        f"LINKS:\n" + "\n".join(links)
    )


def save_report(markdown):
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(markdown)
    return "Saved to report.md"


# ---------------------------------------------------------------------------
# 3. The agent loop: think -> use a tool -> look at the result -> repeat
# ---------------------------------------------------------------------------
def run(site_url):
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from your environment
    messages = [{"role": "user", "content": f"Audit this site: {site_url}"}]
    pages_fetched = 0

    for _ in range(12):  # safety limit on steps
        response = client.messages.create(
            model=MODEL, max_tokens=4000, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break  # the agent is done

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "fetch_page":
                if pages_fetched >= MAX_PAGES:
                    output = "Page limit reached. Write the report now."
                else:
                    pages_fetched += 1
                    print(f"  Reading {block.input['url']}")
                    output = fetch_page(block.input["url"])
            elif block.name == "save_report":
                output = save_report(block.input["markdown"])
                print("  Report written to report.md")
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python agent.py https://example.com")
        sys.exit(1)
    print(f"Auditing {sys.argv[1]} ...")
    run(sys.argv[1])
