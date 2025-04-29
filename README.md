# MessageWrangler
# MessageWrangler

MessageWrangler is a utility that processes message definitions from a source file and generates C++, TypeScript, and Python compatible message formats. This tool is designed to facilitate communication between an Electron app and Unreal Engine over WebSocket.

## Installation

1. Ensure you have Python 3.x installed
2. Set up a virtual environment (recommended):
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install requirements:
   ```
   pip install -r requirements.txt
   ```

## Usage

The script can be run in several ways:

### Direct execution
MessageWrangler is a utility for converting message definitions from a single source format into C++, TypeScript, and Python implementations. This enables seamless communication between an Electron application (TypeScript), Unreal Engine (C++), and Python applications over WebSocket connections.

## Features

- Parse message definitions from a single source file
- Generate C++ header files with proper UE4/UE5 types
- Generate TypeScript interface definitions
- Generate Python dataclasses with type annotations
- Support for inheritance between message types
- Support for enums and compound types
- Automatic type conversion between languages

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/MessageWrangler.git
   cd MessageWrangler
   ```

2. Set up a virtual environment (recommended):
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with the required input and output parameters:
