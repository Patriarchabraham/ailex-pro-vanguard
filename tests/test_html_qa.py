"""Tests for html_qa.py — consolidated in test_content_guard.py"""
# HTML QA tests are in test_content_guard.py (TestHTMLQA class)
# This file is kept for backwards compatibility and module discovery
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_content_guard import TestHTMLQA
import unittest
if __name__ == "__main__":
    unittest.main(verbosity=2)
