"""Tests for motion_system.py — consolidated in test_content_guard.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_content_guard import TestMotionSystem
import unittest
if __name__ == "__main__":
    unittest.main(verbosity=2)
