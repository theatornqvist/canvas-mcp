"""
Canvas LMS API Wrapper
Handles all interactions with the Canvas API with proper authentication and error handling.
Supports a wide range of Canvas features including modules, pages, grades, calendar,
announcements, discussions, and submissions.
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors"""
    pass


class CanvasAPI:
    """Wrapper for Canvas LMS API interactions"""

    def __init__(self, base_url: str, token: str):
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
        Make an authenticated GET request to the Canvas API.
        Raises CanvasAPIError on HTTP errors or network issues.
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )

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
                raise CanvasAPIError(f"API request failed with status {response.status_code}: {response.text[:200]}")

        except requests.exceptions.Timeout:
            raise CanvasAPIError("Request timed out. Please check your network connection.")
        except requests.exceptions.ConnectionError:
            raise CanvasAPIError("Connection error. Please check your network connection.")
        except requests.exceptions.RequestException as e:
            raise CanvasAPIError(f"Request failed: {str(e)}")

    # -------------------------------------------------------------------------
    # Core Course Methods
    # -------------------------------------------------------------------------

    def get_courses(self) -> List[Dict[str, Any]]:
        """Get all active courses, including default_view for navigation hints."""
        params = {
            'enrollment_state': 'active',
            'include[]': ['term', 'total_students', 'teachers']
        }
        courses = self._make_request('/courses', params)

        formatted = []
        for course in courses:
            formatted.append({
                'id': course.get('id'),
                'name': course.get('name'),
                'course_code': course.get('course_code'),
                'enrollment_term': course.get('enrollment_term', {}).get('name'),
                'total_students': course.get('total_students'),
                'workflow_state': course.get('workflow_state'),
                'default_view': course.get('default_view'),  # modules|wiki|syllabus|assignments|feed
            })

        return formatted

    def get_course(self, course_id: int) -> Dict[str, Any]:
        """
        Get detailed course info including default_view, enabled tabs,
        and a navigation hint to guide tool selection.
        """
        params = {
            'include[]': ['syllabus_body', 'term', 'teachers', 'total_students']
        }
        course = self._make_request(f'/courses/{course_id}', params)

        # Fetch enabled tabs to know what content the teacher has exposed
        enabled_tabs = []
        try:
            tabs = self._make_request(f'/courses/{course_id}/tabs')
            enabled_tabs = [t.get('label') for t in tabs if not t.get('hidden', False)]
        except CanvasAPIError:
            pass

        default_view = course.get('default_view', 'unknown')

        view_hints = {
            'modules': 'This course uses Modules — use get_course_modules to browse weekly content.',
            'wiki':    'This course uses a home page — use get_course_home_page for main content.',
            'syllabus':'This course is syllabus-focused — use get_course_syllabus and get_assignments.',
            'assignments': 'This course is assignment-centric — use get_assignments.',
            'feed':    'This course uses an activity feed — check get_announcements for updates.',
        }
        navigation_hint = view_hints.get(
            default_view,
            'Try get_course_modules or get_course_home_page to find content.'
        )

        return {
            'id': course.get('id'),
            'name': course.get('name'),
            'course_code': course.get('course_code'),
            'enrollment_term': course.get('enrollment_term', {}).get('name'),
            'start_at': course.get('start_at'),
            'end_at': course.get('end_at'),
            'total_students': course.get('total_students'),
            'workflow_state': course.get('workflow_state'),
            'default_view': default_view,
            'enabled_tabs': enabled_tabs,
            'navigation_hint': navigation_hint,
            'public_syllabus': course.get('public_syllabus'),
            'syllabus_body': course.get('syllabus_body'),
            'teachers': [
                {'id': t.get('id'), 'name': t.get('display_name')}
                for t in course.get('teachers', [])
            ],
        }

    def get_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """Get all assignments for a course."""
        assignments = self._make_request(f'/courses/{course_id}/assignments')

        formatted = []
        for a in assignments:
            formatted.append({
                'id': a.get('id'),
                'name': a.get('name'),
                'description': a.get('description'),
                'due_at': a.get('due_at'),
                'points_possible': a.get('points_possible'),
                'submission_types': a.get('submission_types'),
                'has_submitted_submissions': a.get('has_submitted_submissions'),
                'workflow_state': a.get('workflow_state'),
                'html_url': a.get('html_url'),
            })

        return formatted

    def get_upcoming_assignments(self) -> List[Dict[str, Any]]:
        """Get upcoming assignments across all active courses, sorted by due date."""
        courses = self.get_courses()
        all_assignments = []
        now = datetime.now(timezone.utc)

        for course in courses:
            try:
                assignments = self.get_assignments(course['id'])
                for a in assignments:
                    due_at = a.get('due_at')
                    if due_at:
                        try:
                            due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                            if due_date > now:
                                all_assignments.append({
                                    'course_id': course['id'],
                                    'course_name': course['name'],
                                    'course_code': course['course_code'],
                                    'assignment_id': a['id'],
                                    'assignment_name': a['name'],
                                    'due_at': due_at,
                                    'points_possible': a['points_possible'],
                                    'html_url': a['html_url'],
                                })
                        except (ValueError, AttributeError):
                            continue
            except CanvasAPIError:
                continue

        all_assignments.sort(key=lambda x: x['due_at'])
        return all_assignments

    def get_course_files(self, course_id: int) -> Dict[str, Any]:
        """
        Get course files. Returns smart fallback suggestions when the Files tab
        is disabled or empty, since many teachers organise content via modules/pages.
        """
        try:
            files = self._make_request(
                f'/courses/{course_id}/files',
                params={'per_page': 100}
            )

            if not files:
                return {
                    'files': [],
                    'count': 0,
                    'message': (
                        'No files found. This course likely organises content via modules or pages. '
                        'Try get_course_modules or get_course_home_page.'
                    ),
                    'suggestions': ['get_course_modules', 'get_course_home_page', 'get_course_pages'],
                }

            formatted = []
            for f in files:
                formatted.append({
                    'id': f.get('id'),
                    'display_name': f.get('display_name'),
                    'filename': f.get('filename'),
                    'url': f.get('url'),
                    'size': f.get('size'),
                    'content_type': f.get('content-type'),
                    'created_at': f.get('created_at'),
                    'updated_at': f.get('updated_at'),
                    'folder_id': f.get('folder_id'),
                })

            return {'files': formatted, 'count': len(formatted)}

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return {
                    'files': [],
                    'count': 0,
                    'error': 'Files tab is disabled or restricted for this course.',
                    'suggestions': ['get_course_modules', 'get_course_home_page', 'get_course_pages'],
                }
            elif 'not found' in err.lower() or '404' in err:
                return {
                    'files': [],
                    'count': 0,
                    'error': 'Files section not found for this course.',
                    'suggestions': ['get_course_modules', 'get_course_home_page'],
                }
            raise

    # -------------------------------------------------------------------------
    # Phase 1: Content Structure Methods
    # -------------------------------------------------------------------------

    def get_course_modules(self, course_id: int) -> Dict[str, Any]:
        """
        Get course modules with all embedded items (files, pages, assignments,
        external URLs, discussions, quizzes, sub-headers).
        """
        try:
            modules = self._make_request(
                f'/courses/{course_id}/modules',
                params={'include[]': ['items', 'content_details'], 'per_page': 50}
            )

            if not modules:
                return {
                    'modules': [],
                    'count': 0,
                    'message': (
                        'This course has no modules. Content may be on the home page or in pages. '
                        'Try get_course_home_page or get_course_pages.'
                    ),
                    'suggestions': ['get_course_home_page', 'get_course_pages', 'get_course_files'],
                }

            formatted = []
            for module in modules:
                items = []
                for item in module.get('items', []):
                    items.append({
                        'id': item.get('id'),
                        'type': item.get('type'),  # File|Page|Assignment|ExternalUrl|SubHeader|Discussion|Quiz
                        'title': item.get('title'),
                        'content_id': item.get('content_id'),
                        'html_url': item.get('html_url'),
                        'external_url': item.get('external_url'),
                        'published': item.get('published'),
                        'position': item.get('position'),
                    })

                formatted.append({
                    'id': module.get('id'),
                    'name': module.get('name'),
                    'position': module.get('position'),
                    'unlock_at': module.get('unlock_at'),
                    'published': module.get('published'),
                    'items_count': len(items),
                    'items': items,
                })

            return {'modules': formatted, 'count': len(formatted)}

        except CanvasAPIError as e:
            err = str(e)
            if 'not found' in err.lower() or '404' in err:
                return {
                    'modules': [],
                    'count': 0,
                    'message': 'Modules not available for this course.',
                    'suggestions': ['get_course_home_page', 'get_course_pages'],
                }
            raise

    def get_course_pages(self, course_id: int) -> List[Dict[str, Any]]:
        """
        List all wiki pages in a course, sorted by most recently updated.
        Pages often contain weekly readings, instructions, and supplementary content.
        """
        try:
            pages = self._make_request(
                f'/courses/{course_id}/pages',
                params={'sort': 'updated_at', 'order': 'desc', 'per_page': 100}
            )

            if not pages:
                return [{
                    'info': 'No pages found in this course.',
                    'suggestions': ['get_course_modules', 'get_course_files'],
                }]

            formatted = []
            for page in pages:
                formatted.append({
                    'page_id': page.get('url'),   # slug used to fetch individual page
                    'title': page.get('title'),
                    'created_at': page.get('created_at'),
                    'updated_at': page.get('updated_at'),
                    'html_url': page.get('html_url'),
                    'front_page': page.get('front_page', False),
                    'published': page.get('published', True),
                })

            return formatted

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return [{'error': 'Pages tab is disabled for this course.', 'suggestions': ['get_course_modules']}]
            if 'not found' in err.lower() or '404' in err:
                return [{'info': 'Pages not available for this course.'}]
            raise

    def get_course_home_page(self, course_id: int) -> Dict[str, Any]:
        """
        Get the front/home page of a course. Many teachers put the entire course
        structure, links, and content overview here (especially wiki-view courses).
        """
        try:
            page = self._make_request(f'/courses/{course_id}/front_page')

            return {
                'title': page.get('title'),
                'body': page.get('body'),   # Rich HTML — may contain links, embeds, tables
                'url': page.get('url'),
                'created_at': page.get('created_at'),
                'updated_at': page.get('updated_at'),
                'html_url': page.get('html_url'),
                'published': page.get('published'),
            }

        except CanvasAPIError as e:
            err = str(e)
            if 'not found' in err.lower() or '404' in err:
                return {
                    'error': 'This course does not have a custom home page.',
                    'suggestions': ['get_course_modules', 'get_course_pages', 'get_course_files'],
                }
            raise

    def get_course_syllabus(self, course_id: int) -> Dict[str, Any]:
        """Get just the syllabus body for a course."""
        params = {'include[]': ['syllabus_body']}
        course = self._make_request(f'/courses/{course_id}', params)

        syllabus = course.get('syllabus_body')
        return {
            'course_id': course.get('id'),
            'course_name': course.get('name'),
            'course_code': course.get('course_code'),
            'public_syllabus': course.get('public_syllabus', False),
            'syllabus_body': syllabus,
            'has_syllabus': bool(syllabus),
            'message': None if syllabus else 'No syllabus content found. The teacher may use modules or pages instead.',
        }

    # -------------------------------------------------------------------------
    # Phase 2: Grades
    # -------------------------------------------------------------------------

    def get_course_grades(self, course_id: int) -> Dict[str, Any]:
        """Get the student's current grades/scores in a specific course."""
        try:
            enrollments = self._make_request(
                f'/courses/{course_id}/enrollments',
                params={
                    'user_id': 'self',
                    'include[]': ['current_grades', 'total_scores'],
                    'type[]': 'StudentEnrollment',
                }
            )

            if not enrollments:
                return {
                    'course_id': course_id,
                    'error': 'No student enrollment found. You may not be a student in this course.',
                }

            enrollment = enrollments[0]
            grades = enrollment.get('grades', {})

            return {
                'course_id': course_id,
                'enrollment_type': enrollment.get('type'),
                'current_score': grades.get('current_score'),
                'current_grade': grades.get('current_grade'),
                'final_score': grades.get('final_score'),
                'final_grade': grades.get('final_grade'),
                'unposted_current_score': grades.get('unposted_current_score'),
                'unposted_current_grade': grades.get('unposted_current_grade'),
            }

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return {'course_id': course_id, 'error': 'Grades are hidden or restricted for this course.'}
            if 'not found' in err.lower() or '404' in err:
                return {'course_id': course_id, 'error': f'Course {course_id} not found.'}
            raise

    def get_all_assignment_grades(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Get grades for every individual assignment in a course.
        Uses the submissions endpoint which includes score, grade, and assignment metadata.
        """
        try:
            submissions = self._make_request(
                f'/courses/{course_id}/students/submissions',
                params={
                    'student_ids[]': 'self',
                    'include[]': ['assignment', 'submission_comments'],
                    'per_page': 100,
                }
            )

            if not submissions:
                return [{'info': 'No submissions found for this course.'}]

            formatted = []
            for sub in submissions:
                assignment = sub.get('assignment') or {}
                formatted.append({
                    'assignment_id': sub.get('assignment_id'),
                    'assignment_name': assignment.get('name', f'Assignment {sub.get("assignment_id")}'),
                    'points_possible': assignment.get('points_possible'),
                    'due_at': assignment.get('due_at'),
                    'submitted': sub.get('workflow_state') != 'unsubmitted',
                    'submitted_at': sub.get('submitted_at'),
                    'workflow_state': sub.get('workflow_state'),  # unsubmitted|submitted|graded
                    'score': sub.get('score'),
                    'grade': sub.get('grade'),
                    'late': sub.get('late', False),
                    'missing': sub.get('missing', False),
                    'html_url': sub.get('preview_url'),
                })

            # Sort: graded first, then by due date
            formatted.sort(key=lambda x: (
                x.get('workflow_state') != 'graded',
                x.get('due_at') or ''
            ))

            return formatted

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return [{'error': 'Grades are hidden or restricted for this course.'}]
            if 'not found' in err.lower() or '404' in err:
                return [{'error': f'Course {course_id} not found.'}]
            raise

    def get_all_grades(self) -> List[Dict[str, Any]]:
        """Get grades for all active courses at once."""
        courses = self.get_courses()
        all_grades = []

        for course in courses:
            try:
                enrollments = self._make_request(
                    f'/courses/{course["id"]}/enrollments',
                    params={
                        'user_id': 'self',
                        'include[]': ['current_grades', 'total_scores'],
                        'type[]': 'StudentEnrollment',
                    }
                )
                if enrollments:
                    grades = enrollments[0].get('grades', {})
                    all_grades.append({
                        'course_id': course['id'],
                        'course_name': course['name'],
                        'course_code': course['course_code'],
                        'current_score': grades.get('current_score'),
                        'current_grade': grades.get('current_grade'),
                        'final_score': grades.get('final_score'),
                        'final_grade': grades.get('final_grade'),
                    })
            except CanvasAPIError:
                # Skip courses where grades aren't accessible (e.g. hidden)
                continue

        return all_grades

    # -------------------------------------------------------------------------
    # Phase 2: Calendar
    # -------------------------------------------------------------------------

    def get_calendar_events(
        self,
        course_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events for a specific course.
        Defaults to the next 30 days if no date range is given.
        """
        now = datetime.now(timezone.utc)
        start = start_date or now.strftime('%Y-%m-%d')
        end = end_date or (now + timedelta(days=30)).strftime('%Y-%m-%d')

        try:
            events = self._make_request(
                '/calendar_events',
                params={
                    'context_codes[]': [f'course_{course_id}'],
                    'start_date': start,
                    'end_date': end,
                    'per_page': 100,
                }
            )

            if not events:
                return [{'info': f'No calendar events found between {start} and {end}.'}]

            formatted = []
            for event in events:
                formatted.append({
                    'id': event.get('id'),
                    'title': event.get('title'),
                    'start_at': event.get('start_at'),
                    'end_at': event.get('end_at'),
                    'location_name': event.get('location_name'),
                    'description': event.get('description'),
                    'html_url': event.get('html_url'),
                    'type': event.get('type', 'event'),
                })

            return formatted

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return [{'error': 'Calendar access is restricted for this course.'}]
            raise

    def get_all_calendar_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get calendar events across all active courses for the next N days.
        Results are sorted by start time and include course name for context.
        """
        now = datetime.now(timezone.utc)
        start = now.strftime('%Y-%m-%d')
        end = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        courses = self.get_courses()
        if not courses:
            return [{'info': 'No active courses found.'}]

        context_codes = [f'course_{c["id"]}' for c in courses]
        course_map = {c['id']: c['name'] for c in courses}

        try:
            events = self._make_request(
                '/calendar_events',
                params={
                    'context_codes[]': context_codes,
                    'start_date': start,
                    'end_date': end,
                    'per_page': 100,
                }
            )

            if not events:
                return [{'info': f'No calendar events found in the next {days_ahead} days.'}]

            formatted = []
            for event in events:
                context = event.get('context_code', '')
                try:
                    cid = int(context.split('_')[-1])
                except (ValueError, IndexError):
                    cid = None

                formatted.append({
                    'id': event.get('id'),
                    'title': event.get('title'),
                    'course_name': course_map.get(cid, 'Unknown Course'),
                    'course_id': cid,
                    'start_at': event.get('start_at'),
                    'end_at': event.get('end_at'),
                    'location_name': event.get('location_name'),
                    'description': event.get('description'),
                    'html_url': event.get('html_url'),
                    'type': event.get('type', 'event'),
                })

            formatted.sort(key=lambda x: x.get('start_at') or '')
            return formatted

        except CanvasAPIError as e:
            return [{'error': str(e)}]

    # -------------------------------------------------------------------------
    # Phase 2: Announcements
    # -------------------------------------------------------------------------

    def get_announcements(
        self,
        course_id: Optional[int] = None,
        days_back: int = 14,
    ) -> List[Dict[str, Any]]:
        """
        Get recent announcements from one course or all active courses.
        Defaults to the last 14 days.
        """
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days_back)).strftime('%Y-%m-%d')

        if course_id:
            context_codes = [f'course_{course_id}']
            course_map: Dict[int, str] = {}
        else:
            courses = self.get_courses()
            context_codes = [f'course_{c["id"]}' for c in courses]
            course_map = {c['id']: c['name'] for c in courses}

        if not context_codes:
            return [{'info': 'No active courses found.'}]

        try:
            announcements = self._make_request(
                '/announcements',
                params={
                    'context_codes[]': context_codes,
                    'start_date': start_date,
                    'per_page': 50,
                }
            )

            if not announcements:
                scope = f'course {course_id}' if course_id else 'any active course'
                return [{'info': f'No announcements in the last {days_back} days for {scope}.'}]

            formatted = []
            for ann in announcements:
                context = ann.get('context_code', '')
                try:
                    cid = int(context.split('_')[-1])
                except (ValueError, IndexError):
                    cid = None

                formatted.append({
                    'id': ann.get('id'),
                    'title': ann.get('title'),
                    'message': ann.get('message'),
                    'posted_at': ann.get('posted_at'),
                    'author': ann.get('author', {}).get('display_name'),
                    'course_id': cid,
                    'course_name': course_map.get(cid) if cid else None,
                    'html_url': ann.get('html_url'),
                    'read_state': ann.get('read_state'),
                })

            formatted.sort(key=lambda x: x.get('posted_at') or '', reverse=True)
            return formatted

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return [{'error': 'Announcements are restricted.'}]
            raise

    # -------------------------------------------------------------------------
    # Phase 2: Submissions
    # -------------------------------------------------------------------------

    def get_assignment_submission(self, course_id: int, assignment_id: int) -> Dict[str, Any]:
        """
        Get your own submission for an assignment, including grade and any
        teacher feedback comments.
        """
        try:
            submission = self._make_request(
                f'/courses/{course_id}/assignments/{assignment_id}/submissions/self',
                params={'include[]': ['submission_comments', 'assignment']}
            )

            assignment_data = submission.get('assignment') or {}
            workflow_state = submission.get('workflow_state', 'unsubmitted')

            comments = [
                {
                    'comment': c.get('comment'),
                    'author_name': c.get('author_name'),
                    'created_at': c.get('created_at'),
                }
                for c in submission.get('submission_comments', [])
            ]

            return {
                'course_id': course_id,
                'assignment_id': assignment_id,
                'assignment_name': assignment_data.get('name', f'Assignment {assignment_id}'),
                'submitted': workflow_state != 'unsubmitted',
                'submitted_at': submission.get('submitted_at'),
                'workflow_state': workflow_state,   # unsubmitted|submitted|graded|pending_review
                'score': submission.get('score'),
                'grade': submission.get('grade'),
                'late': submission.get('late', False),
                'missing': submission.get('missing', False),
                'submission_type': submission.get('submission_type'),
                'attempt': submission.get('attempt'),
                'submission_comments': comments,
                'html_url': submission.get('preview_url'),
            }

        except CanvasAPIError as e:
            err = str(e)
            if 'not found' in err.lower() or '404' in err:
                return {'error': f'Assignment {assignment_id} not found in course {course_id}.'}
            if 'forbidden' in err.lower() or '403' in err:
                return {'error': 'You do not have permission to view this submission.'}
            raise

    # -------------------------------------------------------------------------
    # Phase 3: Discussions
    # -------------------------------------------------------------------------

    def get_course_discussions(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Get discussion forum topics for a course, sorted by recent activity.
        Includes unread counts and reply counts.
        """
        try:
            topics = self._make_request(
                f'/courses/{course_id}/discussion_topics',
                params={'order_by': 'recent_activity', 'per_page': 50}
            )

            if not topics:
                return [{'info': 'No discussion topics found in this course.'}]

            formatted = []
            for topic in topics:
                formatted.append({
                    'id': topic.get('id'),
                    'title': topic.get('title'),
                    'message': topic.get('message'),       # HTML opening post
                    'posted_at': topic.get('posted_at'),
                    'last_reply_at': topic.get('last_reply_at'),
                    'discussion_type': topic.get('discussion_type'),
                    'reply_count': topic.get('discussion_subentry_count', 0),
                    'unread_count': topic.get('unread_count', 0),
                    'subscribed': topic.get('subscribed', False),
                    'published': topic.get('published', True),
                    'html_url': topic.get('html_url'),
                })

            return formatted

        except CanvasAPIError as e:
            err = str(e)
            if 'forbidden' in err.lower() or '403' in err:
                return [{'error': 'Discussions are restricted for this course.'}]
            if 'not found' in err.lower() or '404' in err:
                return [{'info': 'Discussions not available for this course.'}]
            raise

    def get_discussion_entries(
        self,
        course_id: int,
        topic_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get posts and replies from a specific discussion topic.
        Limited to avoid overwhelming responses (default 20 entries).
        """
        try:
            entries = self._make_request(
                f'/courses/{course_id}/discussion_topics/{topic_id}/entries',
                params={'per_page': min(limit, 50)}
            )

            if not entries:
                return [{'info': 'No posts found in this discussion topic.'}]

            formatted = []
            for entry in entries[:limit]:
                replies = [
                    {
                        'id': r.get('id'),
                        'user_name': r.get('user_name'),
                        'message': r.get('message'),
                        'created_at': r.get('created_at'),
                    }
                    for r in entry.get('recent_replies', [])
                ]

                formatted.append({
                    'id': entry.get('id'),
                    'user_name': entry.get('user_name'),
                    'message': entry.get('message'),
                    'created_at': entry.get('created_at'),
                    'updated_at': entry.get('updated_at'),
                    'rating_count': entry.get('rating_count', 0),
                    'replies_count': entry.get('replies_count', 0),
                    'recent_replies': replies,
                })

            return formatted

        except CanvasAPIError as e:
            err = str(e)
            if 'not found' in err.lower() or '404' in err:
                return [{'error': f'Discussion topic {topic_id} not found in course {course_id}.'}]
            raise
