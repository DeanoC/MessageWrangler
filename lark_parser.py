from lark import Lark, Transformer, v_args


# Extended grammar for full message format
grammar = r"""
    start: (comment | import_stmt | item)+
    import_stmt: "import" STRING ("as" NAME)?

    item: comment
        | namespace
        | message
        | enum_def
        | options_def
        | compound_def

    enum_def: DOC_COMMENT* enum_kind NAME inheritance? "{" enum_value_or_comment_list "}"
    inheritance: ":" qualified_name_with_dot
    enum_value_or_comment_list: enum_value_or_comment_seq?
    enum_value_or_comment_seq: enum_value_or_comment_item (enum_value_or_comment_sep enum_value_or_comment_item)* enum_value_or_comment_sep?
    enum_value_or_comment_item: enum_value | comment
    enum_value_or_comment_sep: (COMMA | comment)*
    ENUM_KIND: "enum" | "open_enum"
    enum_kind: ENUM_KIND
    options_def: DOC_COMMENT* "options" NAME "{" option_value_or_comment_list "}"
    option_value_or_comment_list: option_value_or_comment_seq?
    option_value_or_comment_seq: option_value_or_comment_item (option_value_or_comment_sep option_value_or_comment_item)* option_value_or_comment_sep?
    option_value_or_comment_item: option_value | comment
    option_value_or_comment_sep: (COMMA | comment)*
    option_value_or_comment: comment | option_value
    compound_def: DOC_COMMENT* basic_type NAME "{" NAME ("," NAME)* "}"

    comment: DOC_COMMENT | LOCAL_COMMENT | C_COMMENT
    C_COMMENT: /\/\*[\s\S]*\*\//
    DOC_COMMENT: /\s*\/{3}[^\n]*/
    LOCAL_COMMENT: /\s*\/\/[^\n]*/

    namespace: "namespace" NAME "{" item* "}"
message: comment* "message" NAME inheritance? "{" message_body* "}"
    message_body: comment | field
    qualified_name: NAME ("::" NAME)*
    qualified_name_with_dot: NAME ("::" NAME)* ("." NAME)?

field: comment* field_modifier* NAME ":" type_def field_default? ";"?
    field_modifier: NAME
    type_def: enum_type
        | options_type
        | compound_type
        | array_type
        | map_type
        | ref_type
        | basic_type

    array_type: (enum_type | options_type | compound_type | ref_type | basic_type) "[" "]"
    map_type: "Map" "<" map_key_type "," map_value_type ">"
    map_key_type: basic_type | ref_type | NAME
    map_value_type: type_def

enum_type: enum_kind ("{" enum_value_or_comment_list "}" | qualified_name_with_dot)
    enum_value: DOC_COMMENT* NAME ("=" NUMBER)? ";"?

    options_type: "options" "{" option_value_or_comment_list "}"
    option_value: DOC_COMMENT* NAME ("=" NUMBER)?

    // Allow compound_type with zero or more components, and any base type (NAME or BASIC_TYPE), and allow comments between components
    compound_type: (basic_type | NAME) "{" compound_component_seq? "}"
    // Allow comments anywhere between components and commas
    compound_component_seq: compound_component_item (compound_component_sep compound_component_item)*
    compound_component_item: NAME
    compound_component_sep: (COMMA | comment)*

    ref_type: qualified_name_with_dot
    enum_extension: ("{" enum_value_or_comment_list "}") | ("enum" "{" enum_value_or_comment_list "}")

field_default: "=" default_expr
# Accept anything after '=' up to ';' or end of line
default_expr: /[^;\n]+/

    COMMA: ","
    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
    BASIC_TYPE: "string" | "int" | "float" | "bool" | "byte"
    basic_type: BASIC_TYPE
    NUMBER: /-?[0-9]+/
    STRING: /"(\\.|[^"\\])*"/
    %import common.WS
    %ignore WS
"""

parser = Lark(
    grammar,
    start='start',
    propagate_positions=True
)


# Transformer to attach line numbers to field nodes
from lark import Transformer
class AttachFieldLineNumbers(Transformer):
    def field(self, items):
        # Find the first NAME token (field name)
        for item in items:
            if hasattr(item, 'type') and item.type == 'NAME':
                line = getattr(item, 'line', None)
                break
        else:
            line = None
        node = self.__default__('field', items, None)
        if line is not None:
            node.line = line
        return node

def parse_message_dsl(text):
    tree = parser.parse(text)
    # Attach line numbers to field nodes
    tree = AttachFieldLineNumbers().transform(tree)
    return tree
