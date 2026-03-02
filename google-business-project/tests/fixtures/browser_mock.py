#!/usr/bin/env python3
"""
Browser mock fixtures for testing.
"""

from unittest.mock import Mock, MagicMock


def create_mock_browser(url="https://accounts.google.com", title="Google Accounts"):
    """
    Create a mock browser with configurable state.

    Args:
        url: Current page URL
        title: Page title

    Returns:
        Mock browser object
    """
    browser = Mock()
    page = Mock()

    page.url = url
    page.title.return_value = title
    page.locator.return_value.all.return_value = []
    page.locator.return_value.count.return_value = 0
    page.locator.return_value.inner_text.return_value = ""

    browser.page = page
    browser.start = Mock()
    browser.close = Mock()

    return browser


def create_mock_google_login_page():
    """Create mock Google login page state."""
    page = Mock()
    page.url = "https://accounts.google.com/signin"
    page.title.return_value = "Sign in - Google Accounts"

    # Mock email input
    email_input = Mock()
    email_input.get_attribute.return_value = "email"
    email_input.is_disabled.return_value = False
    email_input.input_value.return_value = ""

    # Mock password input
    password_input = Mock()
    password_input.get_attribute.return_value = "password"
    password_input.is_disabled.return_value = False

    # Mock continue button
    continue_button = Mock()
    continue_button.inner_text.return_value = "Weiter"

    # Configure locator
    def mock_locator(selector):
        mock_result = Mock()
        if "input" in selector:
            mock_result.all.return_value = [email_input]
            mock_result.count.return_value = 1
        elif "button" in selector:
            mock_result.all.return_value = [continue_button]
        else:
            mock_result.all.return_value = []
            mock_result.count.return_value = 0
        return mock_result

    page.locator = mock_locator
    page.inner_text = Mock(return_value="Email Password Weiter")

    return page


def create_mock_google_business_page():
    """Create mock Google Business page state."""
    page = Mock()
    page.url = "https://business.google.com/create"
    page.title.return_value = "Create your Business Profile - Google Business Profile"

    # Mock business name input
    name_input = Mock()
    name_input.get_attribute.return_value = "text"
    name_input.is_disabled.return_value = False
    name_input.input_value.return_value = ""

    # Mock category input
    category_input = Mock()
    category_input.get_attribute.return_value = "text"

    # Mock continue button
    continue_button = Mock()
    continue_button.inner_text.return_value = "Weiter"

    def mock_locator(selector):
        mock_result = Mock()
        if "input" in selector:
            mock_result.all.return_value = [name_input, category_input]
        elif "button" in selector:
            mock_result.all.return_value = [continue_button]
        else:
            mock_result.all.return_value = []
        return mock_result

    page.locator = mock_locator
    page.inner_text = Mock(return_value="Business Name Category Weiter")

    return page


def create_mock_dashboard_page():
    """Create mock dashboard page state (task complete)."""
    page = Mock()
    page.url = "https://business.google.com/dashboard"
    page.title.return_value = "Business Profile - Dashboard"

    def mock_locator(selector):
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_result.count.return_value = 0
        return mock_result

    page.locator = mock_locator
    page.inner_text = Mock(return_value="Your locations Dashboard")

    return page