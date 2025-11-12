#!/usr/bin/env python3
"""
Test suite for sendkeys.py optimizations
Tests key mapping, command generation, and other core functionality
"""

import unittest
import sys
import os

# Import the sendkeys module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sendkeys


class TestKeyMap(unittest.TestCase):
    """Test the key map generation and lookup"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Get the key map (whether it's a function or constant)
        if hasattr(sendkeys, 'KEY_MAP'):
            self.key_map = sendkeys.KEY_MAP
        elif hasattr(sendkeys, 'build_key_map'):
            self.key_map = sendkeys.build_key_map()
        else:
            self.fail("No key map found in sendkeys module")
    
    def test_lowercase_letters(self):
        """Test lowercase letters a-z"""
        for c in 'abcdefghijklmnopqrstuvwxyz':
            self.assertIn(c, self.key_map, f"Missing lowercase letter: {c}")
            self.assertIsInstance(self.key_map[c], (str, list))
    
    def test_uppercase_letters(self):
        """Test uppercase letters A-Z"""
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            self.assertIn(c, self.key_map, f"Missing uppercase letter: {c}")
            # Uppercase should use shift (0xe1)
            key_val = self.key_map[c]
            if isinstance(key_val, str):
                self.assertIn('0xe1', key_val, f"Uppercase {c} should use shift")
    
    def test_numbers(self):
        """Test numbers 0-9"""
        for n in '0123456789':
            self.assertIn(n, self.key_map, f"Missing number: {n}")
    
    def test_special_chars(self):
        """Test common special characters"""
        special = ' \n\t-=[]\\;\',./`'
        for c in special:
            self.assertIn(c, self.key_map, f"Missing special char: {repr(c)}")
    
    def test_shifted_symbols(self):
        """Test shifted symbols"""
        shifted = '!@#$%^&*()_+{}|:"<>?~'
        for c in shifted:
            self.assertIn(c, self.key_map, f"Missing shifted symbol: {c}")


class TestCommandGeneration(unittest.TestCase):
    """Test command generation for virsh send-key"""
    
    def setUp(self):
        """Set up test fixtures"""
        if hasattr(sendkeys, 'KEY_MAP'):
            self.key_map = sendkeys.KEY_MAP
        elif hasattr(sendkeys, 'build_key_map'):
            self.key_map = sendkeys.build_key_map()
    
    def test_simple_letter_command(self):
        """Test command generation for a simple letter"""
        char = 'a'
        key_seq = self.key_map.get(char)
        self.assertIsNotNone(key_seq, "Key 'a' should have a mapping")
        
        # Key sequence should be either a string or list
        if isinstance(key_seq, str):
            # Should be a hex code
            self.assertTrue(key_seq.startswith('0x'))
        elif isinstance(key_seq, list):
            # Should be a list of hex codes
            for code in key_seq:
                self.assertTrue(code.startswith('0x'))
    
    def test_uppercase_has_shift(self):
        """Test that uppercase letters include shift modifier"""
        char = 'A'
        key_seq = self.key_map.get(char)
        self.assertIsNotNone(key_seq, "Key 'A' should have a mapping")
        
        # Should contain shift modifier
        if isinstance(key_seq, str):
            self.assertIn('0xe1', key_seq)
        elif isinstance(key_seq, list):
            self.assertIn('0xe1', key_seq)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_validate_choice_valid(self):
        """Test validate_choice with valid input"""
        result = sendkeys.validate_choice('1', 5)
        self.assertEqual(result, 0)
        
        result = sendkeys.validate_choice('5', 5)
        self.assertEqual(result, 4)
    
    def test_validate_choice_invalid(self):
        """Test validate_choice with invalid input"""
        with self.assertRaises(SystemExit):
            sendkeys.validate_choice('0', 5)
        
        with self.assertRaises(SystemExit):
            sendkeys.validate_choice('6', 5)
        
        with self.assertRaises(SystemExit):
            sendkeys.validate_choice('abc', 5)


if __name__ == '__main__':
    unittest.main()
