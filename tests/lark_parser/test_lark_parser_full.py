from lark_parser import parse_message_dsl

def test_full_example():
    text = '''
    /// This message is sent from the tool to Unreal Engine to issue a command.
    message ToolToUnrealCmd {
        /// The type of command to execute.
        command: enum { Ping, Position }
        /// The verb describing the action to perform.
        verb: string
        /// The actor on which to perform the action.
        actor: string
    }

    /// This message is sent from Unreal Engine to the tool as a reply to a command.
    message UnrealToToolCmdReply {
        /// The status of the command execution.
        status: enum { OK, FAIL }
    }

    /// This message is sent from Unreal Engine to the tool as a reply to a command
    /// that updates a position.
    message UnrealToToolCmdUpdateReply : UnrealToToolCmdReply {
        /// The position in 3D space.
        position: float { x, y, z }
    }
    '''
    tree = parse_message_dsl(text)
    # Check that the parse tree contains expected nodes
    assert 'ToolToUnrealCmd' in tree.pretty(), tree.pretty()
    assert 'UnrealToToolCmdReply' in tree.pretty(), tree.pretty()
    assert 'UnrealToToolCmdUpdateReply' in tree.pretty(), tree.pretty()
    assert 'enum_type' in tree.pretty(), tree.pretty()
    assert 'compound_type' in tree.pretty(), tree.pretty()

if __name__ == "__main__":
    test_full_example()
    print("Test passed.")
