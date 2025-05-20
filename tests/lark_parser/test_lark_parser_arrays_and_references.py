from lark_parser import parse_message_dsl

def test_arrays_and_references():
    dsl = '''
    message Vec3 {
        x: float
        y: float
        z: float
    }
    message WithArrays {
        tags: string[]
        points: Vec3[]
        ids: int[]
    }
    message RefTest {
        ref: Vec3
        refArray: Vec3[]
    }
    namespace TestNS {
        message Nested {
            value: int
        }
    }
    message WithNamespaceRef {
        nested: TestNS::Nested
        nestedArray: TestNS::Nested[]
    }
    message WithMap {
        dict: Map<string, int>
        objMap: Map<string, Vec3>
    }
    '''
    tree = parse_message_dsl(dsl)
    pretty = tree.pretty()
    assert 'array_type' in pretty, pretty
    assert 'map_type' in pretty, pretty
    assert 'ref_type' in pretty, pretty
    assert 'WithArrays' in pretty, pretty
    assert 'RefTest' in pretty, pretty
    assert 'WithNamespaceRef' in pretty, pretty
    assert 'WithMap' in pretty, pretty

if __name__ == "__main__":
    test_arrays_and_references()
    print("Test passed.")
