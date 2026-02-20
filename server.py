#!/usr/bin/env python3
"""
Canvas LMS MCP Server
Provides Model Context Protocol tools for interacting with Canvas LMS.

Handles different course structures (modules, wiki/home page, files, assignments)
and provides access to grades, calendar, announcements, discussions, and submissions.
"""

import os
import sys
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from dotenv import load_dotenv
from canvas_api import CanvasAPI, CanvasAPIError

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Canvas-LMS-MCP")

# Initialize Canvas API client
try:
    canvas = CanvasAPI(
        base_url=os.getenv("CANVAS_BASE_URL", ""),
        token=os.getenv("CANVAS_TOKEN", "")
    )
except ValueError as e:
    print(f"Configuration Error: {e}", file=sys.stderr)
    print("Please ensure CANVAS_BASE_URL and CANVAS_TOKEN are set in your .env file", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Core Course Tools (original 5, maintained for backward compatibility)
# =============================================================================

@mcp.tool()
def list_courses() -> list[dict[str, Any]]:
    """
    Get all active courses for the authenticated user.

    Returns each course with: id, name, course_code, enrollment_term,
    total_students, workflow_state, and default_view.

    The default_view field reveals how the teacher has structured the course:
    - "modules"     → use get_course_modules to browse weekly content
    - "wiki"        → use get_course_home_page to see main content
    - "syllabus"    → use get_course_syllabus and get_assignments
    - "assignments" → use get_assignments

    Use this first to discover course IDs needed by all other tools.
    """
    try:
        return canvas.get_courses()
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_course_details(
    course_id: int = Field(description="The Canvas course ID")
) -> dict[str, Any]:
    """
    Get detailed information about a specific course.

    Returns: name, code, term, dates, teachers, total_students, syllabus,
    default_view, enabled_tabs, and a navigation_hint that tells you which
    tool to use next to find content in this course.

    The navigation_hint is key — it tells Claude exactly which tool to call
    based on how the teacher structured the course.

    Use when: User asks for course overview, teacher info, or you need to
    determine how to navigate a course before calling content tools.
    """
    try:
        return canvas.get_course(course_id)
    except CanvasAPIError as e:
        return {"error": str(e)}


@mcp.tool()
def get_assignments(
    course_id: int = Field(description="The Canvas course ID")
) -> list[dict[str, Any]]:
    """
    Get all assignments for a specific course.

    Returns each assignment with: id, name, description, due_at,
    points_possible, submission_types, and html_url.

    Use when: User asks about assignments, homework, labs, or project deadlines
    for a specific course.

    To check submission status or grades on a specific assignment,
    use get_assignment_submission(course_id, assignment_id) afterwards.
    """
    try:
        return canvas.get_assignments(course_id)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_upcoming_deadlines() -> list[dict[str, Any]]:
    """
    Get all upcoming assignment deadlines across ALL active courses, sorted by due date.

    Returns a consolidated list of future assignments with course context,
    due date, points, and link. Sorted earliest-first.

    Use when: User asks "what's due soon?", "what do I need to work on?",
    "show me all my upcoming assignments", or wants a priority overview.

    This scans all active courses automatically — no need to specify a course.
    """
    try:
        return canvas.get_upcoming_assignments()
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_course_files(
    course_id: int = Field(description="The Canvas course ID")
) -> dict[str, Any]:
    """
    List files available in a course.

    Returns a dict with 'files' (list) and 'count'. If the Files tab is
    disabled or empty, returns a message and suggestions for alternative
    tools (modules, home page, pages) since many teachers don't use the
    Files tab directly.

    Use when: User asks for course materials, lecture slides, PDFs, or
    downloadable resources. If this returns empty, follow the suggestions
    to try get_course_modules or get_course_home_page instead.
    """
    try:
        return canvas.get_course_files(course_id)
    except CanvasAPIError as e:
        return {"error": str(e), "files": [], "count": 0}


# =============================================================================
# Phase 1: Content Structure Tools
# =============================================================================

@mcp.tool()
def get_course_modules(
    course_id: int = Field(description="The Canvas course ID")
) -> dict[str, Any]:
    """
    Get the module/week structure of a course with all embedded content items.

    Returns a dict with 'modules' (list) where each module contains its items.
    Module items have types: File, Page, Assignment, ExternalUrl, SubHeader,
    Discussion, or Quiz — with titles and URLs for each.

    If this returns empty, the course uses a different structure — follow
    the 'suggestions' field to try get_course_home_page or get_course_pages.

    Use when:
    - User asks "what's in week 3?", "show me the course structure"
    - Course default_view is "modules"
    - You need to understand how content is organized
    - get_course_files returned empty

    Example queries: "Show week 3 content", "What files are in module 2?",
    "List all course topics"
    """
    try:
        return canvas.get_course_modules(course_id)
    except CanvasAPIError as e:
        return {"error": str(e), "modules": [], "count": 0}


@mcp.tool()
def get_course_pages(
    course_id: int = Field(description="The Canvas course ID")
) -> list[dict[str, Any]]:
    """
    List all wiki pages in a course, sorted by most recently updated.

    Returns page titles, URLs, and timestamps. Does NOT return page body content
    (to keep responses compact). Use the html_url to visit a page directly.

    Pages often contain: weekly readings, instructions, resource lists,
    supplementary material, or the entire course content for wiki-style courses.

    Use when:
    - Course default_view is "wiki" (but you want to see ALL pages, not just home)
    - User asks about readings, weekly content pages, or resource pages
    - get_course_modules returned empty
    - You need to understand what pages exist before fetching one

    Example queries: "List all pages in this course", "What reading pages exist?",
    "Show me the pages in Applied ML"
    """
    try:
        return canvas.get_course_pages(course_id)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_course_home_page(
    course_id: int = Field(description="The Canvas course ID")
) -> dict[str, Any]:
    """
    Get the main home/landing page content for a course.

    Returns the full HTML body of the front page. Many teachers put ALL course
    information here: weekly schedule, links to materials, course overview,
    important dates, and embedded content. This is critical for courses with
    default_view = "wiki".

    The body field contains rich HTML that may include tables, links to files,
    external resources, and course structure.

    Use when:
    - Course default_view is "wiki"
    - User asks about course overview, main page, or "what does the course page say?"
    - get_course_modules returned empty
    - You want to understand the course at a glance

    Example queries: "What's on the Applied ML home page?",
    "Show me the course overview", "What does the teacher say about the course?"
    """
    try:
        return canvas.get_course_home_page(course_id)
    except CanvasAPIError as e:
        return {"error": str(e)}


@mcp.tool()
def get_course_syllabus(
    course_id: int = Field(description="The Canvas course ID")
) -> dict[str, Any]:
    """
    Get the syllabus content for a course.

    Returns the syllabus HTML body along with course name and whether it's public.
    The syllabus typically contains: grading policy, learning objectives,
    required materials, attendance policy, weekly schedule, and assessment breakdown.

    If no syllabus is set, returns a message with suggestions.

    Use when:
    - User asks about grading, course requirements, or policies
    - User asks "what are the learning objectives?"
    - User asks "how are grades calculated?"
    - Course default_view is "syllabus"

    Example queries: "What's the grading policy?", "What are the course requirements?",
    "Is there a syllabus?", "How is the final grade calculated?"
    """
    try:
        return canvas.get_course_syllabus(course_id)
    except CanvasAPIError as e:
        return {"error": str(e)}


# =============================================================================
# Phase 2: Grades
# =============================================================================

@mcp.tool()
def get_course_grades(
    course_id: int = Field(description="The Canvas course ID")
) -> dict[str, Any]:
    """
    Get your current grades and score in a specific course.

    Returns: current_score (numeric %), current_grade (letter), final_score,
    final_grade, and unposted scores if available.

    Note: Some courses hide grades or don't use Canvas gradebook — in that case
    this will return an error message explaining why.

    Use when: User asks "How am I doing in [course]?", "What's my grade in X?",
    "Am I passing Y?", "What score do I have?"

    To see grades in all courses at once, use get_all_grades() instead.
    """
    try:
        return canvas.get_course_grades(course_id)
    except CanvasAPIError as e:
        return {"error": str(e)}


@mcp.tool()
def get_all_grades() -> list[dict[str, Any]]:
    """
    Get your current grades across ALL active courses at once.

    Returns a list where each entry has: course_id, course_name, course_code,
    current_score, current_grade, final_score, final_grade.

    Courses with hidden grades are silently skipped (not counted as errors).

    Use when: User asks "Show me all my grades", "How am I doing overall?",
    "What are my scores across all courses?", "Give me a grade overview"

    Example queries: "What are my grades?", "Show me my academic performance",
    "Am I doing well in my courses?"
    """
    try:
        return canvas.get_all_grades()
    except CanvasAPIError as e:
        return [{"error": str(e)}]


# =============================================================================
# Phase 2: Calendar
# =============================================================================

@mcp.tool()
def get_calendar_events(
    course_id: int = Field(description="The Canvas course ID"),
    start_date: Optional[str] = Field(
        default=None,
        description="Start date in YYYY-MM-DD format (defaults to today)"
    ),
    end_date: Optional[str] = Field(
        default=None,
        description="End date in YYYY-MM-DD format (defaults to 30 days from today)"
    ),
) -> list[dict[str, Any]]:
    """
    Get calendar events for a specific course (lectures, office hours, meetings).

    Returns events with: title, start_at, end_at, location_name, description, url.
    Defaults to the next 30 days if no date range is given.

    Note: This returns CALENDAR EVENTS (scheduled meetings, lectures), not assignment
    deadlines. For deadlines, use get_assignments or get_upcoming_deadlines.

    Use when: User asks "When is the next lecture for X?", "What events are
    scheduled in this course?", "Is there office hours this week?"

    Example queries: "When are the lectures for DAT450?",
    "What's on the calendar for Applied ML this week?"
    """
    try:
        return canvas.get_calendar_events(course_id, start_date, end_date)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_all_calendar_events(
    days_ahead: int = Field(
        default=7,
        description="Number of days ahead to fetch events (default: 7)"
    ),
) -> list[dict[str, Any]]:
    """
    Get ALL calendar events across ALL active courses for the next N days.

    Returns events sorted by start time, each with course_name for context.
    Defaults to the next 7 days.

    Use when: User asks "What do I have today?", "What's my schedule this week?",
    "What's coming up?", "What events do I have tomorrow?"

    Adjust days_ahead for longer horizons:
    - days_ahead=1  → just today
    - days_ahead=7  → this week (default)
    - days_ahead=30 → this month

    Example queries: "What's on my calendar today?", "Show me this week's schedule",
    "Do I have any events tomorrow?"
    """
    try:
        return canvas.get_all_calendar_events(days_ahead)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


# =============================================================================
# Phase 2: Announcements
# =============================================================================

@mcp.tool()
def get_announcements(
    course_id: Optional[int] = Field(
        default=None,
        description="Canvas course ID (omit to get announcements from all courses)"
    ),
    days_back: int = Field(
        default=14,
        description="How many days back to search for announcements (default: 14)"
    ),
) -> list[dict[str, Any]]:
    """
    Get recent announcements from a specific course or all active courses.

    Returns announcements with: title, message (HTML), posted_at, author,
    course info, and read status. Sorted newest-first.

    Leave course_id empty to get announcements from ALL courses at once.
    Increase days_back to search further back (e.g. 30 for a month).

    Use when: User asks "Any new announcements?", "What did the teacher post?",
    "Are there any updates in my courses?", "Did the professor say anything recently?"

    Example queries: "Any announcements this week?",
    "What did the NLP teacher post?", "Show me recent course updates"
    """
    try:
        return canvas.get_announcements(course_id, days_back)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


# =============================================================================
# Phase 2: Submissions
# =============================================================================

@mcp.tool()
def get_assignment_submission(
    course_id: int = Field(description="The Canvas course ID"),
    assignment_id: int = Field(description="The Canvas assignment ID"),
) -> dict[str, Any]:
    """
    Check your submission status, grade, and feedback for a specific assignment.

    Returns: whether submitted, submitted_at timestamp, workflow_state
    (unsubmitted/submitted/graded/pending_review), score, grade, whether it's
    late or missing, and any teacher feedback comments.

    Use get_assignments(course_id) first to find the assignment_id if you don't have it.

    Use when: User asks "Did I submit assignment X?", "What grade did I get on Y?",
    "Any feedback on my homework?", "Is my lab report submitted?",
    "Did the teacher grade my work?"

    Example queries: "Did I turn in the latest assignment?",
    "What feedback did I get on lab 2?", "Am I missing any submissions?"
    """
    try:
        return canvas.get_assignment_submission(course_id, assignment_id)
    except CanvasAPIError as e:
        return {"error": str(e)}


# =============================================================================
# Phase 3: Discussions
# =============================================================================

@mcp.tool()
def get_course_discussions(
    course_id: int = Field(description="The Canvas course ID")
) -> list[dict[str, Any]]:
    """
    Get discussion forum topics for a course, sorted by recent activity.

    Returns each topic with: title, opening message (HTML), posted_at,
    last_reply_at, reply_count, unread_count, and subscribed status.

    To read actual posts in a topic, use get_discussion_entries(course_id, topic_id).

    Use when: User asks "What's being discussed in X?", "Are there any forum posts?",
    "What discussion topics exist?", "What are students talking about?"

    Example queries: "What's being discussed in the NLP forum?",
    "Are there any unread discussions?", "List discussion topics in DAT315"
    """
    try:
        return canvas.get_course_discussions(course_id)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_discussion_entries(
    course_id: int = Field(description="The Canvas course ID"),
    topic_id: int = Field(description="The discussion topic ID (from get_course_discussions)"),
    limit: int = Field(
        default=20,
        description="Maximum number of posts to return (default: 20, max: 50)"
    ),
) -> list[dict[str, Any]]:
    """
    Read posts and replies from a specific discussion topic.

    Returns each post with: user_name, message (HTML), timestamps, rating_count,
    replies_count, and a preview of recent replies.

    Get topic_id from get_course_discussions(course_id) first.
    Limit defaults to 20 to keep responses manageable.

    Use when: User asks "What did people say about X?", "Read the discussion on Y",
    "What are the responses in topic Z?", "Summarize the forum discussion"

    Example queries: "What did students post about the midterm?",
    "Read the week 3 discussion", "What are people saying in topic 12345?"
    """
    try:
        return canvas.get_discussion_entries(course_id, topic_id, limit)
    except CanvasAPIError as e:
        return [{"error": str(e)}]


if __name__ == "__main__":
    mcp.run(transport="stdio")
