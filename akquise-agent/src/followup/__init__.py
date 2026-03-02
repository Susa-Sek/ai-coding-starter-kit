"""
Follow-up module for tracking contact states and generating reminders.
"""

from .tracker import FollowUpTracker, FollowUpState
from .generator import FollowUpGenerator

__all__ = ['FollowUpTracker', 'FollowUpState', 'FollowUpGenerator']