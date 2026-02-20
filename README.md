# Canvas LMS MCP Server

A Model Context Protocol (MCP) server that integrates Canvas LMS with Claude, enabling
natural-language access to your Chalmers Canvas courses — including modules, pages,
grades, calendar events, announcements, discussions, and assignment submissions.

## Features

13 tools covering the full range of Canvas student needs:

**Course Structure** (handles all teacher styles)
| Tool | Description |
|------|-------------|
| `list_courses` | Get all active courses + their structure type |
| `get_course_details` | Detailed info + navigation hint for this course |
| `get_course_modules` | Week-by-week module structure with embedded items |
| `get_course_pages` | List all wiki pages (readings, instructions, etc.) |
| `get_course_home_page` | Main landing page content (critical for wiki-view courses) |
| `get_course_files` | Downloadable files, with smart fallback suggestions |
| `get_course_syllabus` | Grading policy, requirements, course objectives |

**Student Features**
| Tool | Description |
|------|-------------|
| `get_assignments` | All assignments for a course |
| `get_upcoming_deadlines` | All future deadlines across all courses |
| `get_course_grades` | Your grade/score in a specific course |
| `get_all_grades` | Grade overview across all courses |
| `get_assignment_submission` | Submission status + teacher feedback |
| `get_announcements` | Recent announcements (one course or all) |
| `get_calendar_events` | Lectures and events for a course |
| `get_all_calendar_events` | Full schedule across all courses |

**Discussions**
| Tool | Description |
|------|-------------|
| `get_course_discussions` | Forum topics with reply/unread counts |
| `get_discussion_entries` | Read actual posts and replies |

---

## Canvas Course Structure — How It Works

Teachers structure Canvas courses differently. The `default_view` field (visible
in `list_courses` and `get_course_details`) tells you which tools to use:

| `default_view` | What it means | Best tool to start with |
|---------------|---------------|------------------------|
| `modules` | Week-by-week structure | `get_course_modules` |
| `wiki` | Home page is the content hub | `get_course_home_page` |
| `syllabus` | Syllabus-focused | `get_course_syllabus` |
| `assignments` | Assignment-centric | `get_assignments` |

`get_course_details` always returns a `navigation_hint` that tells Claude exactly
which tool to call next for that course.

---

## Prerequisites

- Python 3.10 or higher
- A Chalmers Canvas account at [canvas.chalmers.se](https://canvas.chalmers.se)
- Claude Desktop (for integration)

---

## Getting Your Canvas Access Token

1. Go to [canvas.chalmers.se](https://canvas.chalmers.se) and log in
2. Click **Account** (left sidebar) → **Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Set **Purpose**: "Claude MCP Integration"
6. Optionally set an expiry date for security
7. Click **Generate Token**
8. **Copy the token immediately** — it's only shown once

---

## Installation

```bash
# 1. Navigate to the project directory
cd /Users/theatornqvist/canvas-mcp

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set CANVAS_TOKEN=your_actual_token_here
```

---

## Testing the Server

```bash
# Quick startup check (Ctrl+C to stop)
python server.py

# No output = working correctly. Errors appear on stderr.
```

---

## Claude Desktop Integration

Edit your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "canvas-lms": {
      "command": "/Users/theatornqvist/canvas-mcp/.venv/bin/python",
      "args": ["/Users/theatornqvist/canvas-mcp/server.py"],
      "env": {
        "CANVAS_TOKEN": "your_canvas_token_here",
        "CANVAS_BASE_URL": "https://canvas.chalmers.se/api/v1"
      }
    }
  }
}
```

Restart Claude Desktop completely after saving.

---

## Usage Examples

### Navigating Different Course Structures

```
"What courses am I enrolled in?"
→ list_courses — see default_view for each course

"Tell me about my NLP course"
→ get_course_details — returns navigation_hint: "use get_course_modules"

"Show week 3 content from the NLP course"
→ get_course_modules — shows weekly structure with all embedded items

"What's on the Applied ML home page?"
→ get_course_home_page — critical for wiki-view courses

"List all pages in my Machine Learning course"
→ get_course_pages — shows all wiki pages

"What files are available in DAT450?"
→ get_course_files — with smart suggestions if empty
```

### Grades & Performance

```
"How am I doing in all my courses?"
→ get_all_grades

"What's my grade in the NLP course?"
→ get_course_grades(course_id)

"Did I submit the last homework?"
→ get_assignment_submission(course_id, assignment_id)

"What feedback did I get on lab 2?"
→ get_assignment_submission — includes teacher comments
```

### Deadlines & Calendar

```
"What's due this week?"
→ get_upcoming_deadlines

"What do I have today?"
→ get_all_calendar_events(days_ahead=1)

"What's my schedule this week?"
→ get_all_calendar_events(days_ahead=7)

"When is the next lecture for DAT315?"
→ get_calendar_events(course_id)
```

### Announcements

```
"Any new announcements?"
→ get_announcements (all courses, last 14 days)

"Did the NLP teacher post anything?"
→ get_announcements(course_id=NLP_COURSE_ID)

"Show me announcements from the last month"
→ get_announcements(days_back=30)
```

### Discussions

```
"What's being discussed in the forum?"
→ get_course_discussions(course_id)

"Read the week 3 discussion"
→ get_discussion_entries(course_id, topic_id)

"Summarize what people are saying about the midterm"
→ get_discussion_entries(course_id, topic_id)
```

---

## Common Patterns

### Pattern 1: Unknown Course Structure

```
You: "Show me the content for my Applied ML course"

Claude:
1. list_courses → finds Applied ML, default_view = "wiki"
2. get_course_home_page → gets the rich home page content
   OR if empty: get_course_pages → lists all wiki pages
```

### Pattern 2: Finding Specific Materials

```
You: "Find the lecture slides for week 3 in NLP"

Claude:
1. list_courses → finds NLP course ID
2. get_course_modules → finds "Week 3" module
3. Looks for File/Page items in that module
```

### Pattern 3: Checking Grades + Feedback

```
You: "How did I do on the last assignment in DAT450?"

Claude:
1. get_assignments(course_id) → finds the latest assignment + its ID
2. get_assignment_submission(course_id, assignment_id) → grade + comments
```

### Pattern 4: Daily Planning

```
You: "What do I have going on today and this week?"

Claude:
1. get_all_calendar_events(days_ahead=7) → schedule
2. get_upcoming_deadlines → nearest assignment deadlines
3. get_announcements → any recent teacher posts
```

---

## Tool Reference

### list_courses
```json
[{
  "id": 12345,
  "name": "Natural Language Processing",
  "course_code": "DAT450",
  "enrollment_term": "HT 2024",
  "default_view": "modules",
  "total_students": 85
}]
```

### get_course_modules
```json
{
  "modules": [{
    "id": 111,
    "name": "Week 3: Sequence Models",
    "position": 3,
    "items_count": 5,
    "items": [
      {"type": "File", "title": "Lecture 3 Slides", "html_url": "..."},
      {"type": "Assignment", "title": "Lab 1", "html_url": "..."},
      {"type": "ExternalUrl", "title": "Paper reading", "external_url": "..."}
    ]
  }],
  "count": 8
}
```

### get_all_grades
```json
[{
  "course_id": 12345,
  "course_name": "Natural Language Processing",
  "course_code": "DAT450",
  "current_score": 87.5,
  "current_grade": "B+",
  "final_score": 85.0,
  "final_grade": "B"
}]
```

### get_assignment_submission
```json
{
  "assignment_name": "Lab 2: Sequence Labelling",
  "submitted": true,
  "submitted_at": "2024-10-15T22:30:00Z",
  "workflow_state": "graded",
  "score": 95.0,
  "grade": "A",
  "late": false,
  "submission_comments": [
    {"comment": "Great work on the CRF section!", "author_name": "Dr. Smith"}
  ]
}
```

### get_all_calendar_events
```json
[{
  "title": "Lecture 5: Transformers",
  "course_name": "Natural Language Processing",
  "start_at": "2024-10-17T10:00:00Z",
  "end_at": "2024-10-17T12:00:00Z",
  "location_name": "Room HC4"
}]
```

---

## Project Structure

```
canvas-mcp/
├── server.py        # MCP server with all 13 tool definitions
├── canvas_api.py    # Canvas API wrapper (all HTTP calls + error handling)
├── requirements.txt # Dependencies
├── .env.example     # Environment variable template
├── .env             # Your actual token (NOT in git)
├── .gitignore       # Protects .env and caches
└── README.md        # This file
```

---

## Error Handling

All tools handle errors gracefully and return descriptive messages:

| HTTP Code | Meaning | Response |
|-----------|---------|----------|
| 401 | Bad token | "Authentication failed. Check CANVAS_TOKEN." |
| 403 | Tab disabled | "Files tab is disabled. Try get_course_modules." |
| 404 | No such resource | "No home page set. Try get_course_modules." |
| 429 | Rate limited | "Rate limit exceeded. Wait a moment." |
| Empty | No data | "No modules found. Try get_course_home_page." |

Empty results always include a `suggestions` field with alternative tools to try.

---

## Security

- Token lives in `.env` (local only, excluded from git)
- Token also in Claude Desktop config (local only, not sent anywhere)
- No logging of tokens anywhere in the codebase
- Canvas rate limit: ~3000 requests/hour — normal usage is well under this

---

## Troubleshooting

**Server doesn't start**
```bash
# Verify dependencies are installed
.venv/bin/pip list | grep mcp

# Check .env exists and has your token
cat .env
```

**"Authentication failed"** — Check that your CANVAS_TOKEN is correct and hasn't expired.
Generate a new one from Canvas Settings if needed.

**Claude Desktop doesn't show Canvas tools** — Verify the absolute Python path in the config
matches `.venv/bin/python` and restart Claude Desktop completely.

**All courses return empty modules** — Use `list_courses` first to check `default_view`
for each course, then call the appropriate tool for that view type.

---

## Future Enhancements

- Submit assignments
- Post discussion replies
- Download file content
- Pagination for large courses (>100 files/modules)
- Caching layer for repeated queries
- Notifications / push-style announcements
