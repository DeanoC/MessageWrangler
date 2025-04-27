"""
Integration Tests

This module contains integration tests for the message wrangler.
"""

import os
import unittest
from tempfile import TemporaryDirectory

from message_wrangler import MessageFormatConverter


class TestIntegration(unittest.TestCase):
    """Integration tests for the message wrangler."""

    def test_end_to_end(self):
        """Test the end-to-end process."""
        # Create a temporary directory for output
        with TemporaryDirectory() as temp_dir:
            # Create a converter instance
            converter = MessageFormatConverter("test_messages.def", temp_dir)
            
            # Parse input file
            result = converter.parse_input_file()
            self.assertTrue(result)
            
            # Generate C++ output
            result = converter.generate_cpp_output()
            self.assertTrue(result)
            
            # Check that the C++ output file exists
            cpp_file = os.path.join(temp_dir, "Messages.h")
            self.assertTrue(os.path.exists(cpp_file))
            
            # Generate TypeScript output
            result = converter.generate_typescript_output()
            self.assertTrue(result)
            
            # Check that the TypeScript output file exists
            ts_file = os.path.join(temp_dir, "messages.ts")
            self.assertTrue(os.path.exists(ts_file))
            
            # Read the C++ output file
            with open(cpp_file, 'r') as f:
                cpp_content = f.read()
            
            # Check that the C++ content contains expected elements
            self.assertIn("namespace Messages", cpp_content)
            self.assertIn("struct ToolToUnrealCmd", cpp_content)
            self.assertIn("struct UnrealToToolCmdReply", cpp_content)
            self.assertIn("struct UnrealToToolCmdUpdateReply : public UnrealToToolCmdReply", cpp_content)
            self.assertIn("ToolToUnrealCmd_command_Enum command", cpp_content)
            self.assertIn("FString verb", cpp_content)
            self.assertIn("FString actor", cpp_content)
            self.assertIn("UnrealToToolCmdReply_status_Enum status", cpp_content)
            self.assertIn("struct {", cpp_content)
            self.assertIn("float x", cpp_content)
            self.assertIn("float y", cpp_content)
            self.assertIn("float z", cpp_content)
            self.assertIn("} position", cpp_content)
            
            # Read the TypeScript output file
            with open(ts_file, 'r') as f:
                ts_content = f.read()
            
            # Check that the TypeScript content contains expected elements
            self.assertIn("export namespace Messages", ts_content)
            self.assertIn("export interface ToolToUnrealCmd", ts_content)
            self.assertIn("export interface UnrealToToolCmdReply", ts_content)
            self.assertIn("export interface UnrealToToolCmdUpdateReply extends UnrealToToolCmdReply", ts_content)
            self.assertIn("command: ToolToUnrealCmd_command_Enum", ts_content)
            self.assertIn("verb: string", ts_content)
            self.assertIn("actor: string", ts_content)
            self.assertIn("status: UnrealToToolCmdReply_status_Enum", ts_content)
            self.assertIn("position: {", ts_content)
            self.assertIn("x: number", ts_content)
            self.assertIn("y: number", ts_content)
            self.assertIn("z: number", ts_content)


if __name__ == '__main__':
    unittest.main()