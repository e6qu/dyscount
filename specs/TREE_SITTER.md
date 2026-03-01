# Tree-sitter Grammar for DynamoDB Expressions

## Table of Contents

1. [Overview](#overview)
2. [Grammar Structure](#grammar-structure)
3. [Grammar Rules](#grammar-rules)
4. [UpdateExpression Specifics](#updateexpression-specifics)
5. [ProjectionExpression Specifics](#projectionexpression-specifics)
6. [KeyConditionExpression Specifics](#keyconditionexpression-specifics)
7. [Operator Precedence](#operator-precedence)
8. [Tree-sitter Bindings](#tree-sitter-bindings)
9. [Example Parse Trees](#example-parse-trees)
10. [Implementation Approach](#implementation-approach)

---

## Overview

### What is Tree-sitter?

Tree-sitter is a parser generator tool and incremental parsing library that:
- **General**: Capable of parsing any programming language
- **Fast**: Efficient enough to parse on every keystroke in a text editor
- **Robust**: Provides useful results even in the presence of syntax errors
- **Dependency-free**: Written in pure C11 for easy embedding in any application

### Why Tree-sitter is Suitable for Dyscount

| Feature | Benefit for DynamoDB Expressions |
|---------|----------------------------------|
| **Incremental Parsing** | Efficiently re-parse expressions as users type |
| **Error Recovery** | Provide meaningful results even with incomplete expressions |
| **Multiple Language Bindings** | Native support for Python, Go, Rust, and Zig via C interop |
| **Unified Grammar** | Single grammar.js file can handle all expression types |
| **GLR Algorithm** | Handles operator precedence and associativity correctly |
| **WASM Support** | Can run in browsers for client-side validation |

---

## Grammar Structure

### Grammar Name

```javascript
name: 'dynamodb_expression'
```

### Entry Points

The unified grammar supports multiple entry points for different expression types:

| Entry Point | Expression Type | Purpose |
|-------------|-----------------|---------|
| `key_condition` | KeyConditionExpression | Query partition/sort key conditions |
| `filter` | FilterExpression | Filter query/scan results |
| `projection` | ProjectionExpression | Select attributes to return |
| `condition` | ConditionExpression | Conditional write operations |
| `update` | UpdateExpression | Modify item attributes |

### Grammar Configuration

```javascript
module.exports = grammar({
  name: 'dynamodb_expression',
  
  // Whitespace handling
  extras: $ => [/[\s\t\r\n]+/],
  
  // Case-insensitive keywords
  word: $ => $.identifier,
  
  // Entry points for different expression types
  rules: {
    // Primary entry points
    key_condition: $ => $._key_condition_expression,
    filter: $ => $._condition_expression,
    projection: $ => $._projection_expression,
    condition: $ => $._condition_expression,
    update: $ => $._update_expression,
    
    // ... additional rules
  }
});
```

---

## Grammar Rules

### Literals

#### Strings

```javascript
string_literal: $ => choice(
  // Single-quoted strings
  seq("'", repeat(choice(/[^'\\]/, /\\./)), "'"),
  // Double-quoted strings  
  seq('"', repeat(choice(/[^"\\]/, /\\./)), '"')
),
```

#### Numbers

```javascript
number_literal: $ => {
  const digits = /[0-9]+/;
  const sign = /[+-]?/;
  const exponent = /[eE][+-]?[0-9]+/;
  
  return token(seq(
    sign,
    choice(
      seq(digits, optional('.'), optional(digits), optional(exponent)),
      seq('.', digits, optional(exponent))
    )
  ));
}
```

#### Binary (Base64)

```javascript
binary_literal: $ => token(seq(
  'B',
  /[A-Za-z0-9+/=]+/
)),
```

#### Booleans

```javascript
boolean_literal: $ => choice(
  alias(/[Tt][Rr][Uu][Ee]/, 'true'),
  alias(/[Ff][Aa][Ll][Ss][Ee]/, 'false')
),
```

#### Null

```javascript
null_literal: $ => /[Nn][Uu][Ll][Ll]/,
```

### Identifiers and Placeholders

#### Attribute Names

```javascript
// #placeholder for attribute name substitution
attribute_placeholder: $ => seq(
  '#',
  /[a-zA-Z_][a-zA-Z0-9_]*/
),

// Regular identifier
identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,

// Attribute name (identifier or placeholder)
attribute_name: $ => choice(
  $.identifier,
  $.attribute_placeholder
),
```

#### Value Placeholders

```javascript
// :placeholder for value substitution
value_placeholder: $ => seq(
  ':',
  /[a-zA-Z_][a-zA-Z0-9_]*/
),

// Value reference
value: $ => choice(
  $.value_placeholder,
  $.literal
),
```

### Comparison Operators

```javascript
comparison_operator: $ => choice(
  '=',           // Equal
  '<>',          // Not equal
  '<',           // Less than
  '<=',          // Less than or equal
  '>',           // Greater than
  '>='           // Greater than or equal
),
```

### Logical Operators

```javascript
_logical_operator: $ => choice(
  $.and_operator,
  $.or_operator
),

and_operator: $ => /[Aa][Nn][Dd]/,
or_operator: $ => /[Oo][Rr]/,
not_operator: $ => /[Nn][Oo][Tt]/,
```

### Functions

```javascript
function_call: $ => choice(
  $.attribute_exists,
  $.attribute_not_exists,
  $.attribute_type,
  $.begins_with,
  $.contains,
  $.size
),

attribute_exists: $ => seq(
  field('function', /[Aa][Tt][Tt][Rr][Ii][Bb][Uu][Tt][Ee]_[Ee][Xx][Ii][Ss][Tt][Ss]/),
  '(',
  field('path', $.path),
  ')'
),

attribute_not_exists: $ => seq(
  field('function', /[Aa][Tt][Tt][Rr][Ii][Bb][Uu][Tt][Ee]_[Nn][Oo][Tt]_[Ee][Xx][Ii][Ss][Tt][Ss]/),
  '(',
  field('path', $.path),
  ')'
),

attribute_type: $ => seq(
  field('function', /[Aa][Tt][Tt][Rr][Ii][Bb][Uu][Tt][Ee]_[Tt][Yy][Pp][Ee]/),
  '(',
  field('path', $.path),
  ',',
  field('type', $.value),
  ')'
),

begins_with: $ => seq(
  field('function', /[Bb][Ee][Gg][Ii][Nn][Ss]_[Ww][Ii][Tt][Hh]/),
  '(',
  field('path', $.path),
  ',',
  field('substring', $.value),
  ')'
),

contains: $ => seq(
  field('function', /[Cc][Oo][Nn][Tt][Aa][Ii][Nn][Ss]/),
  '(',
  field('path', $.path),
  ',',
  field('operand', $.value),
  ')'
),

size: $ => seq(
  field('function', /[Ss][Ii][Zz][Ee]/),
  '(',
  field('path', $.path),
  ')'
),
```

### Math Operators (UpdateExpression)

```javascript
math_operator: $ => choice('+', '-'),

math_expression: $ => prec.left(2, seq(
  field('left', $.operand),
  field('operator', $.math_operator),
  field('right', $.operand)
)),
```

### Path Expressions

```javascript
// Document path for accessing nested attributes
path: $ => seq(
  $.attribute_name,
  repeat($.path_element)
),

path_element: $ => choice(
  $.nested_attribute,
  $.list_index
),

// Dot notation for map attributes
nested_attribute: $ => seq(
  '.',
  choice(
    $.identifier,
    $.attribute_placeholder
  )
),

// Bracket notation for list indices
list_index: $ => seq(
  '[',
  field('index', $.number_literal),
  ']'
),
```

### List/Map Literals

```javascript
literal: $ => choice(
  $.string_literal,
  $.number_literal,
  $.binary_literal,
  $.boolean_literal,
  $.null_literal,
  $.list_literal,
  $.map_literal
),

list_literal: $ => seq(
  '[',
  optional($.list_elements),
  ']'
),

list_elements: $ => seq(
  $.value,
  repeat(seq(',', $.value))
),

map_literal: $ => seq(
  '{',
  optional($.map_elements),
  '}'
),

map_elements: $ => seq(
  $.map_element,
  repeat(seq(',', $.map_element))
),

map_element: $ => seq(
  field('key', choice($.string_literal, $.identifier)),
  ':',
  field('value', $.value)
),
```

### Condition Expression

```javascript
_condition_expression: $ => prec.left($._condition_or),

_condition_or: $ => prec.left(1, seq(
  $._condition_and,
  repeat(seq($.or_operator, $._condition_and))
)),

_condition_and: $ => prec.left(2, seq(
  $._condition_not,
  repeat(seq($.and_operator, $._condition_not))
)),

_condition_not: $ => choice(
  prec.right(3, seq($.not_operator, $._condition_not)),
  $._condition_primary
),

_condition_primary: $ => choice(
  $.condition_comparison,
  $.condition_between,
  $.condition_in,
  $.function_call,
  seq('(', $._condition_expression, ')')
),

condition_comparison: $ => seq(
  field('left', $.operand),
  field('operator', $.comparison_operator),
  field('right', $.operand)
),

condition_between: $ => seq(
  field('operand', $.operand),
  /[Bb][Ee][Tt][Ww][Ee][Ee][Nn]/,
  field('lower', $.operand),
  /[Aa][Nn][Dd]/,
  field('upper', $.operand)
),

condition_in: $ => seq(
  field('operand', $.operand),
  /[Ii][Nn]/,
  '(',
  $.operand_list,
  ')'
),

operand: $ => choice(
  $.path,
  $.value,
  $.function_call,
  $.math_expression
),

operand_list: $ => seq(
  $.operand,
  repeat(seq(',', $.operand))
),
```

---

## UpdateExpression Specifics

### Update Expression Structure

```javascript
_update_expression: $ => seq(
  optional($.set_clause),
  optional($.remove_clause),
  optional($.add_clause),
  optional($.delete_clause)
),
```

### SET Actions

```javascript
set_clause: $ => seq(
  /[Ss][Ee][Tt]/,
  $.set_action,
  repeat(seq(',', $.set_action))
),

set_action: $ => seq(
  field('path', $.path),
  '=',
  field('value', $.set_value)
),

set_value: $ => choice(
  $.operand,
  $.math_expression,
  $.if_not_exists,
  $.list_append
),

if_not_exists: $ => seq(
  /[Ii][Ff]_[Nn][Oo][Tt]_[Ee][Xx][Ii][Ss][Tt][Ss]/,
  '(',
  field('path', $.path),
  ',',
  field('value', $.set_value),
  ')'
),

list_append: $ => seq(
  /[Ll][Ii][Ss][Tt]_[Aa][Pp][Pp][Ee][Nn][Dd]/,
  '(',
  field('list1', $.operand),
  ',',
  field('list2', $.operand),
  ')'
),
```

### REMOVE Actions

```javascript
remove_clause: $ => seq(
  /[Rr][Ee][Mm][Oo][Vv][Ee]/,
  $.remove_action,
  repeat(seq(',', $.remove_action))
),

remove_action: $ => field('path', $.path),
```

### ADD Actions

```javascript
add_clause: $ => seq(
  /[Aa][Dd][Dd]/,
  $.add_action,
  repeat(seq(',', $.add_action))
),

add_action: $ => seq(
  field('path', $.path),
  field('value', $.operand)
),
```

### DELETE Actions

```javascript
delete_clause: $ => seq(
  /[Dd][Ee][Ll][Ee][Tt][Ee]/,
  $.delete_action,
  repeat(seq(',', $.delete_action))
),

delete_action: $ => seq(
  field('path', $.path),
  field('subset', $.operand)
),
```

---

## ProjectionExpression Specifics

```javascript
_projection_expression: $ => seq(
  $.projection_path,
  repeat(seq(',', $.projection_path))
),

projection_path: $ => $.path,
```

**Characteristics:**
- Comma-separated list of document paths
- Each path specifies an attribute to retrieve
- Nested paths supported: `User.Address.City`
- Array indices supported: `Tags[0]`

---

## KeyConditionExpression Specifics

```javascript
_key_condition_expression: $ => seq(
  $.partition_key_condition,
  optional(seq(
    /[Aa][Nn][Dd]/,
    $.sort_key_condition
  ))
),

partition_key_condition: $ => seq(
  field('key', $.attribute_name),
  '=',
  field('value', $.value_placeholder)
),

sort_key_condition: $ => choice(
  $.sort_key_comparison,
  $.sort_key_between,
  $.sort_key_begins_with
),

sort_key_comparison: $ => seq(
  field('key', $.attribute_name),
  field('operator', $.comparison_operator),
  field('value', $.value_placeholder)
),

sort_key_between: $ => seq(
  field('key', $.attribute_name),
  /[Bb][Ee][Tt][Ww][Ee][Ee][Nn]/,
  field('lower', $.value_placeholder),
  /[Aa][Nn][Dd]/,
  field('upper', $.value_placeholder)
),

sort_key_begins_with: $ => seq(
  /[Bb][Ee][Gg][Ii][Nn][Ss]_[Ww][Ii][Tt][Hh]/,
  '(',
  field('key', $.attribute_name),
  ',',
  field('prefix', $.value_placeholder),
  ')'
),
```

**Constraints:**
- Must include partition key equality condition
- Optional sort key condition
- Sort key supports: `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, `begins_with`
- Logical operators NOT allowed (unlike FilterExpression)

---

## Operator Precedence

### DynamoDB Precedence Rules (from highest to lowest)

| Precedence | Operator/Construct | Description |
|------------|-------------------|-------------|
| 1 | `=`, `<>`, `<`, `<=`, `>`, `>=` | Comparison operators |
| 2 | `IN` | Membership test |
| 3 | `BETWEEN` | Range test |
| 4 | `attribute_exists`, `attribute_not_exists`, `begins_with`, `contains` | Functions |
| 5 | Parentheses `()` | Grouping |
| 6 | `NOT` | Logical negation |
| 7 | `AND` | Logical conjunction |
| 8 | `OR` | Logical disjunction |

**Evaluation:** Left to right within same precedence level

### Grammar Implementation

```javascript
rules: {
  // Level 8: OR (lowest)
  _condition_or: $ => prec.left(1, seq(
    $._condition_and,
    repeat(seq($.or_operator, $._condition_and))
  )),
  
  // Level 7: AND
  _condition_and: $ => prec.left(2, seq(
    $._condition_not,
    repeat(seq($.and_operator, $._condition_not))
  )),
  
  // Level 6: NOT
  _condition_not: $ => choice(
    prec.right(3, seq($.not_operator, $._condition_not)),
    $._condition_comparison
  ),
  
  // Level 5: Parentheses (handled in primary)
  // Level 4: Functions (handled as primary expressions)
  // Level 1-3: Comparisons (highest among condition operators)
  _condition_comparison: $ => prec.left(4, choice(
    $.condition_comparison,
    $.condition_between,
    $.condition_in,
    $.function_call,
    seq('(', $._condition_expression, ')')
  )),
  
  // Math expressions in SET
  math_expression: $ => prec.left(2, seq(
    $.operand,
    choice('+', '-'),
    $.operand
  )),
}
```

### Associativity

| Operator | Associativity | Example |
|----------|--------------|---------|
| `AND` | Left | `a AND b AND c` → `(a AND b) AND c` |
| `OR` | Left | `a OR b OR c` → `(a OR b) OR c` |
| `NOT` | Right | `NOT NOT a` → `NOT (NOT a)` |
| `+`, `-` | Left | `a + b + c` → `(a + b) + c` |

---

## Tree-sitter Bindings

### Python

**Package:** `tree-sitter` (PyPI)

```python
from tree_sitter import Language, Parser

# Build the language library
Language.build_library(
    'build/dynamodb.so',
    ['path/to/tree-sitter-dynamodb']
)

# Load the language
DYNAMODB_LANGUAGE = Language('build/dynamodb.so', 'dynamodb_expression')

# Create parser
parser = Parser()
parser.set_language(DYNAMODB_LANGUAGE)

# Parse expression
tree = parser.parse(b"Price > :min AND Status = :status")
root = tree.root_node

# Walk the tree
def walk(node, depth=0):
    print("  " * depth + f"{node.type}: {node.text.decode()}")
    for child in node.children:
        walk(child, depth + 1)

walk(root)
```

### Go

**Package:** `github.com/smacker/go-tree-sitter`

```go
package main

import (
    "context"
    "fmt"
    sitter "github.com/smacker/go-tree-sitter"
    "github.com/smacker/go-tree-sitter/dynamodb"
)

func main() {
    parser := sitter.NewParser()
    parser.SetLanguage(dynamodb.GetLanguage())
    
    source := []byte("Price > :min AND Status = :status")
    tree := parser.Parse(source)
    root := tree.RootNode()
    
    // Walk the tree
    var walk func(node *sitter.Node, depth int)
    walk = func(node *sitter.Node, depth int) {
        indent := ""
        for i := 0; i < depth; i++ {
            indent += "  "
        }
        fmt.Printf("%s%s: %s\n", indent, node.Type(), node.Content(source))
        for i := 0; i < int(node.ChildCount()); i++ {
            walk(node.Child(i), depth+1)
        }
    }
    
    walk(root, 0)
}
```

### Rust

**Package:** `tree-sitter` crate

```rust
use tree_sitter::{Parser, Language};

extern "C" {
    fn tree_sitter_dynamodb() -> Language;
}

fn main() {
    let mut parser = Parser::new();
    let language = unsafe { tree_sitter_dynamodb() };
    parser.set_language(language).expect("Error loading grammar");
    
    let source = "Price > :min AND Status = :status";
    let tree = parser.parse(source, None).expect("Error parsing");
    let root = tree.root_node();
    
    fn print_tree(node: tree_sitter::Node, source: &str, depth: usize) {
        let indent = "  ".repeat(depth);
        println!("{}{}: {}", 
            indent, 
            node.kind(), 
            &source[node.byte_range()]
        );
        for i in 0..node.child_count() {
            print_tree(node.child(i).unwrap(), source, depth + 1);
        }
    }
    
    print_tree(root, source, 0);
}
```

Cargo.toml:
```toml
[dependencies]
tree-sitter = "0.20"
```

### Zig

**Approach:** C interop with compiled parser library

```zig
const std = @import("std");
const c = @cImport({
    @cInclude("tree_sitter/api.h");
    @cInclude("tree_sitter_dynamodb.h");
});

pub fn main() !void {
    const parser = c.ts_parser_new();
    defer c.ts_parser_delete(parser);
    
    const language = c.tree_sitter_dynamodb();
    _ = c.ts_parser_set_language(parser, language);
    
    const source = "Price > :min AND Status = :status";
    const tree = c.ts_parser_parse_string(
        parser, 
        null, 
        source.ptr, 
        @intCast(u32, source.len)
    );
    defer c.ts_tree_delete(tree);
    
    const root = c.ts_tree_root_node(tree);
    
    // Walk tree using C API
    printNode(root, source, 0);
}

fn printNode(node: c.TSNode, source: []const u8, depth: usize) void {
    const indent = "  " ** depth;
    const type_str = c.ts_node_type(node);
    const start = c.ts_node_start_byte(node);
    const end = c.ts_node_end_byte(node);
    
    std.debug.print("{s}{s}: {s}\n", .{
        indent, 
        type_str, 
        source[start..end]
    });
    
    const child_count = c.ts_node_child_count(node);
    var i: u32 = 0;
    while (i < child_count) : (i += 1) {
        printNode(c.ts_node_child(node, i), source, depth + 1);
    }
}
```

---

## Example Parse Trees

### Example 1: Simple Condition Expression

**Input:** `Price > :min AND Status = :status`

**Parse Tree:**
```
(condition_expression [0, 0] - [0, 38])
  (_condition_or [0, 0] - [0, 38])
    (_condition_and [0, 0] - [0, 38])
      (_condition_and [0, 0] - [0, 13])
        (_condition_not [0, 0] - [0, 13])
          (_condition_comparison [0, 0] - [0, 13])
            left: (path [0, 0] - [0, 5])
              (attribute_name [0, 0] - [0, 5])
                (identifier [0, 0] - [0, 5])
            operator: (comparison_operator [0, 6] - [0, 7])
            right: (value [0, 8] - [0, 13])
              (value_placeholder [0, 8] - [0, 13])
      (and_operator [0, 14] - [0, 17])
      (_condition_not [0, 18] - [0, 38])
        (_condition_comparison [0, 18] - [0, 38])
          left: (path [0, 18] - [0, 24])
            (attribute_name [0, 18] - [0, 24])
              (identifier [0, 18] - [0, 24])
          operator: (comparison_operator [0, 25] - [0, 26])
          right: (value [0, 27] - [0, 38])
            (value_placeholder [0, 27] - [0, 38])
```

### Example 2: KeyConditionExpression

**Input:** `ForumName = :name AND begins_with(Subject, :prefix)`

**Parse Tree:**
```
(key_condition_expression [0, 0] - [0, 55])
  (partition_key_condition [0, 0] - [0, 18])
    key: (attribute_name [0, 0] - [0, 9])
      (identifier [0, 0] - [0, 9])
    value: (value_placeholder [0, 12] - [0, 18])
  (sort_key_condition [0, 23] - [0, 55])
    (sort_key_begins_with [0, 23] - [0, 55])
      function: (begins_with [0, 23] - [0, 34])
      key: (attribute_name [0, 35] - [0, 42])
        (identifier [0, 35] - [0, 42])
      prefix: (value_placeholder [0, 44] - [0, 54])
```

### Example 3: UpdateExpression

**Input:** `SET Price = Price - :discount, #status = :newStatus REMOVE OldField`

**Parse Tree:**
```
(update_expression [0, 0] - [0, 69])
  (set_clause [0, 0] - [0, 54])
    (set_action [0, 4] - [0, 29])
      path: (path [0, 4] - [0, 9])
        (attribute_name [0, 4] - [0, 9])
          (identifier [0, 4] - [0, 9])
      value: (math_expression [0, 12] - [0, 29])
        left: (operand [0, 12] - [0, 17])
          (path [0, 12] - [0, 17])
            (attribute_name [0, 12] - [0, 17])
              (identifier [0, 12] - [0, 17])
        operator: (math_operator [0, 18] - [0, 19])
        right: (operand [0, 20] - [0, 29])
          (value_placeholder [0, 20] - [0, 29])
    (set_action [0, 31] - [0, 54])
      path: (path [0, 31] - [0, 38])
        (attribute_name [0, 31] - [0, 38])
          (attribute_placeholder [0, 31] - [0, 38])
      value: (value_placeholder [0, 41] - [0, 54])
  (remove_clause [0, 55] - [0, 69])
    (remove_action [0, 62] - [0, 69])
      path: (path [0, 62] - [0, 69])
        (attribute_name [0, 62] - [0, 69])
          (identifier [0, 62] - [0, 69])
```

### Example 4: ProjectionExpression

**Input:** `UserId, Address.City, Tags[0]`

**Parse Tree:**
```
(projection_expression [0, 0] - [0, 30])
  (projection_path [0, 0] - [0, 6])
    (path [0, 0] - [0, 6])
      (attribute_name [0, 0] - [0, 6])
        (identifier [0, 0] - [0, 6])
  (projection_path [0, 8] - [0, 20])
    (path [0, 8] - [0, 20])
      (attribute_name [0, 8] - [0, 15])
        (identifier [0, 8] - [0, 15])
      (nested_attribute [0, 15] - [0, 20])
        (identifier [0, 16] - [0, 20])
  (projection_path [0, 22] - [0, 30])
    (path [0, 22] - [0, 30])
      (attribute_name [0, 22] - [0, 26])
        (identifier [0, 22] - [0, 26])
      (list_index [0, 26] - [0, 30])
        index: (number_literal [0, 27] - [0, 28])
```

### Example 5: Complex Filter with Functions

**Input:** `attribute_exists(Reviews) AND size(Comments) > :min AND contains(Tags, :tag)`

**Parse Tree:**
```
(filter_expression [0, 0] - [0, 79])
  (_condition_or [0, 0] - [0, 79])
    (_condition_and [0, 0] - [0, 79])
      (_condition_and [0, 0] - [0, 47])
        (_condition_not [0, 0] - [0, 25])
          (function_call [0, 0] - [0, 25])
            (attribute_exists [0, 0] - [0, 25])
              function: "attribute_exists"
              path: (path [0, 17] - [0, 24])
                (attribute_name [0, 17] - [0, 24])
                  (identifier [0, 17] - [0, 24])
        (and_operator [0, 26] - [0, 29])
        (_condition_not [0, 30] - [0, 47])
          (_condition_comparison [0, 30] - [0, 47])
            left: (function_call [0, 30] - [0, 45])
              (size [0, 30] - [0, 45])
                function: "size"
                path: (path [0, 35] - [0, 43])
                  (attribute_name [0, 35] - [0, 43])
                    (identifier [0, 35] - [0, 43])
            operator: (comparison_operator [0, 46] - [0, 47])
            right: (value_placeholder [0, 48] - [0, 53])
      (and_operator [0, 54] - [0, 57])
      (_condition_not [0, 58] - [0, 79])
        (function_call [0, 58] - [0, 79])
          (contains [0, 58] - [0, 79])
            function: "contains"
            path: (path [0, 67] - [0, 71])
              (attribute_name [0, 67] - [0, 71])
                (identifier [0, 67] - [0, 71])
            operand: (value_placeholder [0, 73] - [0, 78])
```

---

## Implementation Approach

### Project Structure

```
tree-sitter-dynamodb/
├── grammar.js              # Main grammar definition
├── package.json            # NPM manifest
├── src/
│   ├── parser.c            # Generated parser (tree-sitter generate)
│   └── tree_sitter/
│       └── parser.h        # Parser API header
├── bindings/
│   ├── node/               # Node.js bindings
│   ├── python/             # Python bindings
│   ├── rust/               # Rust bindings
│   └── go/                 # Go bindings
├── test/
│   └── corpus/
│       ├── conditions.txt  # Condition expression tests
│       ├── updates.txt     # Update expression tests
│       ├── projections.txt # Projection expression tests
│       └── keys.txt        # Key condition expression tests
└── queries/
    ├── highlights.scm      # Syntax highlighting queries
    └── injections.scm      # Language injection queries
```

### Grammar Development Workflow

1. **Initialize Project**
   ```bash
   npm install -g tree-sitter-cli
   mkdir tree-sitter-dynamodb
   cd tree-sitter-dynamodb
   tree-sitter init
   ```

2. **Edit Grammar** (`grammar.js`)
   - Define entry points
   - Implement rules incrementally
   - Use `field()` for semantic structure
   - Apply `prec()` for operator precedence

3. **Generate Parser**
   ```bash
   tree-sitter generate
   ```

4. **Write Tests** (`test/corpus/*.txt`)
   ```
   ==================
   Simple Comparison
   ==================
   Price > :min
   ---
   (condition_expression
     (_condition_comparison
       left: (path ...)
       operator: (comparison_operator)
       right: (value ...)))
   ```

5. **Run Tests**
   ```bash
   tree-sitter test
   ```

6. **Parse Example**
   ```bash
   echo "Price > :min" | tree-sitter parse
   ```

### Integration with Dyscount

The parser will be integrated into Dyscount as:

1. **Validation Layer**: Parse expressions before sending to DynamoDB
2. **Analysis Layer**: Extract attribute references and value placeholders
3. **Transformation Layer**: Modify or rewrite expressions

```python
# Example Dyscount integration
from dyscount.parser import DynamoDBParser

parser = DynamoDBParser()

# Parse and validate
result = parser.parse_condition("Price > :min AND Status = :status")
if result.errors:
    raise ValidationError(result.errors)

# Extract placeholders
placeholders = result.extract_value_placeholders()
# Returns: [":min", ":status"]

# Extract attribute names
attributes = result.extract_attribute_names()
# Returns: ["Price", "Status"]
```

### Build and Distribution

1. **Generate all bindings**
   ```bash
   tree-sitter generate --bindings
   ```

2. **Build native libraries**
   ```bash
   # Node.js
   npm build
   
   # Python
   python setup.py build
   
   # Rust
   cargo build --release
   
   # Go (requires cgo)
   go build
   ```

3. **Publish**
   - npm: `@dyscount/tree-sitter-dynamodb`
   - PyPI: `tree-sitter-dynamodb`
   - crates.io: `tree-sitter-dynamodb`
   - Go: `github.com/dyscount/tree-sitter-dynamodb`

---

## References

- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [AWS DynamoDB Expression Reference](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.html)
- [DynamoDB Condition Expression Syntax](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.OperatorsAndFunctions.html)
- [DynamoDB Update Expression Syntax](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html)
- [DynamoDB Key Condition Expression](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.KeyConditionExpressions.html)
