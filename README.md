# Canvas LMS MCP Server

A Model Context Protocol (MCP) server that integrates Canvas LMS with Claude, enabling seamless access to your Chalmers Canvas courses, assignments, deadlines, and files directly through Claude conversations.

## Features

This MCP server provides five tools:

1. **list_courses** - Get all your active courses
2. **get_course_details** - View detailed information about a specific course
3. **get_assignments** - List all assignments for a course
4. **get_upcoming_deadlines** - See all upcoming deadlines across all your courses
5. **get_course_files** - Browse files available in a course

## Prerequisites

- Python 3.10 or higher
- A Chalmers Canvas account with access to canvas.chalmers.se
- Claude Desktop (for integration with Claude)

## Getting Your Canvas Access Token

Before you can use this MCP server, you need to generate a Canvas API access token:

1. Navigate to [canvas.chalmers.se](https://canvas.chalmers.se)
2. Log in with your Chalmers credentials
3. Click on **Account** (left sidebar) → **Settings**
4. Scroll down to the **Approved Integrations** section
5. Click **+ New Access Token**
6. Fill in the form:
   - **Purpose**: "Claude MCP Integration" (or any descriptive name)
   - **Expires**: (Optional) Set an expiration date for security
7. Click **Generate Token**
8. **IMPORTANT**: Copy the token immediately - it will only be shown once!

## Installation

### 1. Clone or Download This Project

```bash
cd /path/to/your/projects
# If you haven't already created the directory
git clone <your-repo> canvas-mcp
# Or just ensure you're in the canvas-mcp directory
cd canvas-mcp
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
```

### 3. Activate the Virtual Environment

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

**On Windows:**
```cmd
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or: vim .env, code .env, etc.
```

Add your Canvas token to the `.env` file:

```env
CANVAS_TOKEN=your_actual_token_here
CANVAS_BASE_URL=https://canvas.chalmers.se/api/v1
```

**Security Note**: Never commit your `.env` file to version control! It's already listed in `.gitignore`.

## Testing the Server Standalone

Before integrating with Claude Desktop, test that the server works:

```bash
python server.py
```

The server should start without errors. You'll see it running in stdio mode (it won't print anything unless there's an error during startup).

Press `Ctrl+C` to stop the server.

## Claude Desktop Integration

To use this MCP server with Claude Desktop, you need to add it to your Claude Desktop configuration.

### 1. Locate Your Claude Desktop Config File

**On macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**On Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**On Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### 2. Edit the Configuration File

Open the config file in a text editor. If the file doesn't exist, create it with this content:

```json
{
  "mcpServers": {
    "canvas-lms": {
      "command": "python",
      "args": ["/absolute/path/to/canvas-mcp/server.py"],
      "env": {
        "CANVAS_TOKEN": "your_canvas_token_here",
        "CANVAS_BASE_URL": "https://canvas.chalmers.se/api/v1"
      }
    }
  }
}
```

**Important**:
- Replace `/absolute/path/to/canvas-mcp/server.py` with the actual absolute path to your server.py file
- Replace `your_canvas_token_here` with your actual Canvas token
- You can also use the virtual environment's Python: `/absolute/path/to/canvas-mcp/.venv/bin/python`

**Example (macOS):**
```json
{
  "mcpServers": {
    "canvas-lms": {
      "command": "/Users/theatornqvist/canvas-mcp/.venv/bin/python",
      "args": ["/Users/theatornqvist/canvas-mcp/server.py"],
      "env": {
        "CANVAS_TOKEN": "1234~abcdefghijklmnopqrstuvwxyz",
        "CANVAS_BASE_URL": "https://canvas.chalmers.se/api/v1"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Completely quit and restart Claude Desktop for the changes to take effect.

### 4. Verify the Integration

Open Claude Desktop and check:
- Look for the MCP server indicator (usually a small icon or indicator showing connected servers)
- The "canvas-lms" server should be listed as connected

## Usage Examples

Once integrated with Claude Desktop, you can ask Claude questions like:

### View Your Courses
```
"Show me all my active courses"
"What courses am I enrolled in?"
```

### Check Assignments
```
"What assignments do I have in course 12345?"
"Show me the assignments for my Machine Learning course"
```

### See Upcoming Deadlines
```
"What assignments are due soon?"
"Show me all my upcoming deadlines"
"What do I need to work on this week?"
```

### Get Course Details
```
"Tell me more about course 67890"
"What's the syllabus for my Algorithms course?"
```

### Browse Course Files
```
"What files are available in course 12345?"
"Show me the lecture slides for my Data Structures course"
```

## Project Structure

```
canvas-mcp/
├── server.py          # Main MCP server with tool definitions
├── canvas_api.py      # Canvas API wrapper with error handling
├── requirements.txt   # Python dependencies
├── .env.example      # Environment variable template
├── .env              # Your actual environment variables (not in git)
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## Tools Reference

### list_courses()
Returns all active courses you're enrolled in.

**Returns:**
```json
[
  {
    "id": 12345,
    "name": "Introduction to Machine Learning",
    "course_code": "TDA231",
    "enrollment_term": "HT 2024",
    "total_students": 150,
    "workflow_state": "available"
  }
]
```

### get_course_details(course_id)
Get detailed information about a specific course.

**Parameters:**
- `course_id` (int): The Canvas course ID

**Returns:** Full course object with syllabus, teachers, dates, etc.

### get_assignments(course_id)
List all assignments for a course.

**Parameters:**
- `course_id` (int): The Canvas course ID

**Returns:**
```json
[
  {
    "id": 67890,
    "name": "Assignment 1: Linear Regression",
    "due_at": "2024-09-15T23:59:00Z",
    "points_possible": 100,
    "submission_types": ["online_upload"],
    "html_url": "https://canvas.chalmers.se/courses/12345/assignments/67890"
  }
]
```

### get_upcoming_deadlines()
Get all upcoming assignment deadlines across all your courses, sorted by due date.

**Returns:**
```json
[
  {
    "course_id": 12345,
    "course_name": "Introduction to Machine Learning",
    "course_code": "TDA231",
    "assignment_id": 67890,
    "assignment_name": "Assignment 1: Linear Regression",
    "due_at": "2024-09-15T23:59:00Z",
    "points_possible": 100,
    "html_url": "https://canvas.chalmers.se/courses/12345/assignments/67890"
  }
]
```

### get_course_files(course_id)
List all files in a course.

**Parameters:**
- `course_id` (int): The Canvas course ID

**Returns:**
```json
[
  {
    "id": 111222,
    "display_name": "Lecture 1 - Introduction.pdf",
    "filename": "lecture1_intro.pdf",
    "url": "https://canvas.chalmers.se/files/111222/download",
    "size": 1048576,
    "content_type": "application/pdf",
    "created_at": "2024-08-20T10:00:00Z"
  }
]
```

## Error Handling

The server handles common errors gracefully:

- **401 Unauthorized**: Invalid or expired Canvas token
- **403 Forbidden**: No permission to access the resource
- **404 Not Found**: Invalid course ID or endpoint
- **429 Rate Limit**: Too many requests (Canvas limits apply)
- **Network Errors**: Connection timeouts or failures

Errors are returned in the response with descriptive messages.

## Security Considerations

- **Never commit your `.env` file** - it contains your sensitive Canvas token
- **Token permissions** - Your token has the same permissions as your Canvas account
- **Rate limits** - Canvas API typically allows ~3000 requests per hour
- **Token expiration** - Set expiration dates on tokens for better security
- **Local only** - This MCP server runs locally on your machine and doesn't send data elsewhere

## Troubleshooting

### Server doesn't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file exists and contains valid values
- Ensure your virtual environment is activated

### "Authentication failed" error
- Verify your Canvas token is correct in the `.env` file (or Claude Desktop config)
- Check if the token has expired (generate a new one if needed)
- Ensure there are no extra spaces or quotes around the token

### Claude Desktop doesn't show the server
- Verify the absolute path in `claude_desktop_config.json` is correct
- Check that the Python path is valid (use full path to `.venv/bin/python`)
- Restart Claude Desktop completely (quit and reopen)
- Check Claude Desktop logs for error messages

### "Resource not found" errors
- Verify the course ID is correct (use `list_courses` to get valid IDs)
- Ensure you have access to the course in Canvas
- Check that the course is in "active" state

## Canvas API Documentation

For more information about Canvas API endpoints:
- [Canvas API Documentation](https://canvas.instructure.com/doc/api/)
- [Canvas REST API Reference](https://canvas.instructure.com/doc/api/all_resources.html)

## Future Enhancements

Possible features for future versions:
- Submit assignments
- Post to discussion boards
- Download course files
- Get announcement notifications
- Calendar integration
- Caching for better performance
- Support for pagination (>100 files per course)

## Contributing

This is a personal project for Chalmers Canvas integration. Feel free to fork and adapt for your own institution's Canvas instance!

## License

MIT License - feel free to use and modify as needed.

## Support

For Canvas-related issues, contact Chalmers IT support.
For MCP server issues, check the implementation or create an issue in the repository.
