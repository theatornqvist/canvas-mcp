#!/usr/bin/env python3
"""
Canvas LMS MCP Server
Provides Model Context Protocol tools for interacting with Canvas LMS API.
"""

import os
import sys
from typing import Any
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


@mcp.tool()
def list_courses() -> list[dict[str, Any]]:
    """
    Get all active courses for the authenticated user.

    Returns a list of active courses with basic information including:
    - Course ID
    - Course name
    - Course code
    - Enrollment term
    - Total students
    - Workflow state

    This is useful for discovering which courses you're enrolled in and getting
    their IDs for use with other tools.
    """
    try:
        courses = canvas.get_courses()
        return courses
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_course_details(
    course_id: int = Field(description="The Canvas course ID to retrieve details for")
) -> dict[str, Any]:
    """
    Get detailed information about a specific course.

    Retrieves comprehensive information about a course including:
    - Basic info (name, code, term)
    - Syllabus content
    - Start and end dates
    - Teachers
    - Total students
    - Workflow state

    Args:
        course_id: The unique identifier for the Canvas course

    Returns detailed course information that can help understand course structure,
    requirements, and key information from the syllabus.
    """
    try:
        course = canvas.get_course(course_id)
        return course
    except CanvasAPIError as e:
        return {"error": str(e)}


@mcp.tool()
def get_assignments(
    course_id: int = Field(description="The Canvas course ID to retrieve assignments from")
) -> list[dict[str, Any]]:
    """
    Get all assignments for a specific course.

    Retrieves the complete list of assignments for a course including:
    - Assignment ID and name
    - Description
    - Due date
    - Points possible
    - Submission types
    - Submission status
    - Assignment URL

    Args:
        course_id: The unique identifier for the Canvas course

    This is useful for understanding what assignments are available in a course,
    their requirements, and deadlines.
    """
    try:
        assignments = canvas.get_assignments(course_id)
        return assignments
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_upcoming_deadlines() -> list[dict[str, Any]]:
    """
    Get all upcoming assignment deadlines across all active courses.

    Retrieves a consolidated list of all future assignment deadlines from all
    your active courses, sorted by due date (earliest first).

    Each entry includes:
    - Course information (ID, name, code)
    - Assignment information (ID, name, URL)
    - Due date
    - Points possible

    This is particularly useful for:
    - Getting an overview of upcoming work
    - Planning your schedule
    - Identifying imminent deadlines
    - Prioritizing assignments across multiple courses

    Note: Only includes assignments with due dates in the future.
    """
    try:
        upcoming = canvas.get_upcoming_assignments()
        return upcoming
    except CanvasAPIError as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_course_files(
    course_id: int = Field(description="The Canvas course ID to list files from")
) -> list[dict[str, Any]]:
    """
    List all files available in a specific course.

    Retrieves information about all files uploaded to a course including:
    - File ID
    - Display name and filename
    - File URL for downloading
    - File size
    - Content type (MIME type)
    - Creation and update timestamps
    - Folder ID

    Args:
        course_id: The unique identifier for the Canvas course

    This is useful for:
    - Finding course materials and resources
    - Accessing lecture slides, readings, or other documents
    - Getting download URLs for specific files
    - Understanding the file organization in a course

    Note: Returns up to 100 files per request. For courses with more files,
    pagination would be needed (not currently implemented).
    """
    try:
        files = canvas.get_course_files(course_id)
        return files
    except CanvasAPIError as e:
        return [{"error": str(e)}]


if __name__ == "__main__":
    # Run the MCP server using stdio transport
    # This allows communication via standard input/output
    mcp.run(transport="stdio")
