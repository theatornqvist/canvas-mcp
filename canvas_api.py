"""
Canvas LMS API Wrapper
Handles all interactions with the Canvas API with proper authentication and error handling.
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors"""
    pass


class CanvasAPI:
    """Wrapper for Canvas LMS API interactions"""

    def __init__(self, base_url: str, token: str):
        """
        Initialize Canvas API client.

        Args:
            base_url: Canvas API base URL (e.g., https://canvas.chalmers.se/api/v1)
            token: Canvas access token for authentication
        """
        if not base_url:
            raise ValueError("CANVAS_BASE_URL environment variable is required")
        if not token:
            raise ValueError("CANVAS_TOKEN environment variable is required")

        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Make an authenticated request to the Canvas API.

        Args:
            endpoint: API endpoint (e.g., '/courses')
            params: Optional query parameters

        Returns:
            JSON response from the API

        Raises:
            CanvasAPIError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )

            # Handle different HTTP status codes
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise CanvasAPIError("Authentication failed. Please check your CANVAS_TOKEN.")
            elif response.status_code == 403:
                raise CanvasAPIError("Access forbidden. You may not have permission to access this resource.")
            elif response.status_code == 404:
                raise CanvasAPIError("Resource not found. Please check the course ID or endpoint.")
            elif response.status_code == 429:
                raise CanvasAPIError("Rate limit exceeded. Please wait a moment and try again.")
            else:
                raise CanvasAPIError(f"API request failed with status {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            raise CanvasAPIError("Request timed out. Please check your network connection.")
        except requests.exceptions.ConnectionError:
            raise CanvasAPIError("Connection error. Please check your network connection.")
        except requests.exceptions.RequestException as e:
            raise CanvasAPIError(f"Request failed: {str(e)}")

    def get_courses(self) -> List[Dict[str, Any]]:
        """
        Get all active courses for the authenticated user.

        Returns:
            List of course objects with id, name, course_code, etc.
        """
        params = {
            'enrollment_state': 'active',
            'include[]': ['term', 'total_students', 'teachers']
        }
        courses = self._make_request('/courses', params)

        # Filter and format the response
        formatted_courses = []
        for course in courses:
            formatted_courses.append({
                'id': course.get('id'),
                'name': course.get('name'),
                'course_code': course.get('course_code'),
                'enrollment_term': course.get('enrollment_term', {}).get('name'),
                'total_students': course.get('total_students'),
                'workflow_state': course.get('workflow_state')
            })

        return formatted_courses

    def get_course(self, course_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            Course object with full details
        """
        params = {
            'include[]': ['syllabus_body', 'term', 'teachers', 'total_students', 'course_image']
        }
        course = self._make_request(f'/courses/{course_id}', params)

        return {
            'id': course.get('id'),
            'name': course.get('name'),
            'course_code': course.get('course_code'),
            'enrollment_term': course.get('enrollment_term', {}).get('name'),
            'start_at': course.get('start_at'),
            'end_at': course.get('end_at'),
            'total_students': course.get('total_students'),
            'workflow_state': course.get('workflow_state'),
            'public_syllabus': course.get('public_syllabus'),
            'syllabus_body': course.get('syllabus_body'),
            'teachers': [{'id': t.get('id'), 'name': t.get('display_name')}
                        for t in course.get('teachers', [])]
        }

    def get_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Get all assignments for a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of assignment objects
        """
        assignments = self._make_request(f'/courses/{course_id}/assignments')

        formatted_assignments = []
        for assignment in assignments:
            formatted_assignments.append({
                'id': assignment.get('id'),
                'name': assignment.get('name'),
                'description': assignment.get('description'),
                'due_at': assignment.get('due_at'),
                'points_possible': assignment.get('points_possible'),
                'submission_types': assignment.get('submission_types'),
                'has_submitted_submissions': assignment.get('has_submitted_submissions'),
                'workflow_state': assignment.get('workflow_state'),
                'html_url': assignment.get('html_url')
            })

        return formatted_assignments

    def get_upcoming_assignments(self) -> List[Dict[str, Any]]:
        """
        Get all upcoming assignment deadlines across all active courses.

        Returns:
            List of upcoming assignments sorted by due date, with course context
        """
        # Get all active courses
        courses = self.get_courses()

        # Collect all assignments from all courses
        all_assignments = []
        current_time = datetime.utcnow()

        for course in courses:
            try:
                assignments = self.get_assignments(course['id'])

                for assignment in assignments:
                    # Only include assignments with future due dates
                    due_at = assignment.get('due_at')
                    if due_at:
                        try:
                            due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                            if due_date > current_time:
                                all_assignments.append({
                                    'course_id': course['id'],
                                    'course_name': course['name'],
                                    'course_code': course['course_code'],
                                    'assignment_id': assignment['id'],
                                    'assignment_name': assignment['name'],
                                    'due_at': due_at,
                                    'points_possible': assignment['points_possible'],
                                    'html_url': assignment['html_url']
                                })
                        except (ValueError, AttributeError):
                            # Skip assignments with invalid date formats
                            continue
            except CanvasAPIError:
                # Skip courses that fail (e.g., no access to assignments)
                continue

        # Sort by due date (earliest first)
        all_assignments.sort(key=lambda x: x['due_at'])

        return all_assignments

    def get_course_files(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Get all files available in a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of file objects
        """
        params = {
            'per_page': 100  # Get up to 100 files per request
        }
        files = self._make_request(f'/courses/{course_id}/files', params)

        formatted_files = []
        for file in files:
            formatted_files.append({
                'id': file.get('id'),
                'display_name': file.get('display_name'),
                'filename': file.get('filename'),
                'url': file.get('url'),
                'size': file.get('size'),
                'content_type': file.get('content-type'),
                'created_at': file.get('created_at'),
                'updated_at': file.get('updated_at'),
                'folder_id': file.get('folder_id')
            })

        return formatted_files
