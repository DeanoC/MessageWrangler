# Message Format Syntax Highlighting for JetBrains IDEs

This document explains how to add syntax highlighting for `.def` message definition files in your JetBrains IDE.

## Installation

1. Close your JetBrains IDE if it's currently running.

2. Find your IDE config directory:
   - Windows: `%USERPROFILE%\.IntelliJIdea<version>\config` (or similar for other JetBrains IDEs)
   - macOS: `~/Library/Preferences/IntelliJIdea<version>` (or similar for other JetBrains IDEs)
   - Linux: `~/.IntelliJIdea<version>/config` (or similar for other JetBrains IDEs)

3. Within the config directory, navigate to or create the `filetypes` directory.

4. Copy the `MessageFormat.xml` file into this directory.

5. Start your IDE. The `.def` files should now have syntax highlighting.

## Features

This syntax highlighting configuration provides:

- Keywords highlighting for `message`, `field`, and `enum`
- Type highlighting for `string`, `float`, etc.
- Enum value highlighting
- Comment support for `//` line comments and `/* */` block comments
- Inheritance highlighting via the `:` symbol
- Proper brace, bracket, and parenthesis handling

## Customization

If you wish to modify the syntax highlighting:

1. Go to **Settings (Preferences)** → **Editor** → **File Types**
2. Find **Message Definition Format** in the list
3. Modify keywords, comments, or other settings as needed

## Note

This syntax highlighting is a basic configuration. For more advanced features like code completion or validation, a full language plugin would be needed.
