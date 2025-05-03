import os
import sys

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser import MessageParser
from cpp_generator import UnrealCppGenerator

def main():
    # Parse the sh4c_comms.def file
    parser = MessageParser("sh4c_comms.def", verbose=True)
    model = parser.parse()
    
    if model:
        # Generate the C++ code
        generator = UnrealCppGenerator(model, ".", "ue_sh4c_comms")
        generator.generate()
        print("Generated C++ code for sh4c_comms.def")
    else:
        print("Failed to parse sh4c_comms.def")

if __name__ == "__main__":
    main()