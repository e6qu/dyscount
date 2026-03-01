# DynamoDB Expression LSP Specification

**Version**: 0.1.0  
**LSP Version**: 3.17+  
**Status**: Draft

---

## Table of Contents

1. [Overview](#1-overview)
2. [Server Capabilities](#2-server-capabilities)
3. [Expression Types](#3-expression-types)
4. [Completion Features](#4-completion-features)
5. [Hover Documentation](#5-hover-documentation)
6. [Diagnostic Validation](#6-diagnostic-validation)
7. [Schema Awareness](#7-schema-awareness)
8. [Configuration](#8-configuration)
9. [Communication Protocol](#9-communication-protocol)
10. [Editor Integration](#10-editor-integration)
11. [Implementation Architecture](#11-implementation-architecture)
12. [Appendix: Function Reference](#appendix-function-reference)

---

## 1. Overview

### 1.1 What is LSP?

The [Language Server Protocol (LSP)](https://microsoft.github.io/language-server-protocol/) is an open protocol for providing language features (autocompletion, go-to-definition, diagnostics, etc.) in editors and IDEs. It decouples language tooling from editor implementations.

### 1.2 Why LSP for DynamoDB Expressions?

DynamoDB expressions have complex syntax with:
- Case-sensitive function names (`attribute_exists` vs `ATTRIBUTE_EXISTS`)
- Expression-specific valid functions/operators
- Reserved words requiring aliasing
- Nested attribute paths
- Type-specific constraints

An LSP server provides:
- **Real-time validation** - Catch syntax errors before runtime
- **Intelligent autocomplete** - Functions, operators, attribute names
- **Inline documentation** - Function signatures and examples
- **Schema-aware suggestions** - Contextual attribute completions

### 1.3 LSP Version

This specification targets **LSP 3.17+** to utilize:
- `Diagnostic.relatedInformation`
- `CompletionItem.labelDetails`
- `InlayHint` support (future)

---

## 2. Server Capabilities

The server MUST advertise the following capabilities during initialization:

```json
{
  "capabilities": {
    "textDocumentSync": {
      "openClose": true,
      "change": 2,
      "willSave": false,
      "willSaveWaitUntil": false,
      "save": true
    },
    "completionProvider": {
      "resolveProvider": true,
      "triggerCharacters": ["(", ",", ".", "#", ":", " ", "("]
    },
    "hoverProvider": true,
    "diagnosticProvider": {
      "identifier": "dyscount",
      "interFileDependencies": false,
      "workspaceDiagnostics": false
    },
    "documentSymbolProvider": true,
    "workspace": {
      "workspaceFolders": {
        "supported": true,
        "changeNotifications": true
      },
      "configuration": true
    }
  }
}
```

### 2.1 Capability Details

| Capability | Method | Description |
|------------|--------|-------------|
| `textDocument/completion` | Autocomplete | Function names, operators, keywords, attributes |
| `textDocument/hover` | Documentation | Function signatures, parameter docs, examples |
| `textDocument/diagnostic` | Validation | Syntax errors, type mismatches, invalid functions |
| `textDocument/documentSymbol` | Outline | Expression structure (functions, conditions, paths) |
| `workspace/didChangeConfiguration` | Settings | Schema path, validation toggle, expression type |
| `textDocument/formatting` *(optional)* | Format | Consistent spacing, indentation |

---

## 3. Expression Types

The server supports five DynamoDB expression types, each with distinct syntax:

### 3.1 KeyConditionExpression

Used in `Query` operations. Restricted to key attributes only.

**Allowed:**
- Partition key: `=` only
- Sort key: `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, `begins_with()`
- `AND` (required between partition and sort key conditions)

**Not Allowed:**
- `OR`, `NOT`, `IN`
- Functions other than `begins_with`
- Non-key attributes

```
# Valid
ForumName = :name
ForumName = :name AND Subject = :sub
ForumName = :name AND begins_with(Subject, :prefix)
ForumName = :name AND ReplyDateTime BETWEEN :start AND :end

# Invalid
ForumName = :name OR ForumName = :other
attribute_exists(NonKeyAttr)
Title = :title
```

### 3.2 FilterExpression

Used to filter `Query`/`Scan` results. Can reference any attribute.

**Allowed:**
- All comparison operators: `=`, `<>`, `<`, `<=`, `>`, `>=`
- `BETWEEN`, `IN`
- All functions: `attribute_exists`, `begins_with`, `contains`, `size`, etc.
- Logical operators: `AND`, `OR`, `NOT`
- Parentheses for precedence

### 3.3 ProjectionExpression

Specifies attributes to retrieve. Simple comma-separated list.

**Allowed:**
- Attribute names (top-level or nested)
- List indexing: `RelatedItems[0]`
- Map paths: `ProductReviews.FiveStar`
- Expression attribute names: `#a`

**Not Allowed:**
- Functions
- Operators
- Expression attribute values

```
Title, Price, Color
Description, RelatedItems[0], ProductReviews.FiveStar
#a, #b[0], #c.#d
```

### 3.4 ConditionExpression

Used in `PutItem`, `UpdateItem`, `DeleteItem` for conditional writes.

**Allowed:**
- Same as FilterExpression
- Plus conditional write patterns

### 3.5 UpdateExpression

Modifies item attributes. Uses clause-based syntax.

**Clauses:**
- `SET` - Add/modify attributes
- `REMOVE` - Delete attributes
- `ADD` - Increment numbers, add to sets
- `DELETE` - Remove from sets

**SET Functions:**
- `if_not_exists(path, value)` - Only valid in SET

```
SET Price = :p, Status = :s
REMOVE OldAttribute, Outdated[0]
ADD ViewCount :inc
DELETE Tags :tagToRemove

# Multiple clauses (order doesn't matter)
SET Price = :p REMOVE OldAttribute ADD ViewCount :inc
```

---

## 4. Completion Features

### 4.1 Completion Contexts

The server provides completions based on cursor position:

| Context | Completions |
|---------|-------------|
| Top-level | Expression keywords, attribute names |
| After function name | Opening parenthesis |
| Inside function | Parameter hints |
| After operand | Comparison operators |
| After condition | Logical operators |
| After `#` | Expression attribute name placeholders |
| After `:` | Expression attribute value placeholders |

### 4.2 Function Completions

```json
{
  "label": "attribute_exists",
  "kind": 3,
  "detail": "function(path): boolean",
  "documentation": {
    "kind": "markdown",
    "value": "Returns true if the item contains the attribute at the specified path.\n\n**Example:** `attribute_exists(ProductReviews.FiveStar)`"
  },
  "insertText": "attribute_exists($1)",
  "insertTextFormat": 2,
  "sortText": "01_attribute_exists"
}
```

### 4.3 Operator Completions

Context-aware operator suggestions:

| Expression Type | Operators Shown |
|-----------------|-----------------|
| KeyConditionExpression (partition) | `=` |
| KeyConditionExpression (sort) | `=`, `<`, `<=`, `>`, `>=`, `BETWEEN` |
| Filter/Condition | All comparison operators, `BETWEEN`, `IN` |
| UpdateExpression (SET) | `=`, `+`, `-` |

### 4.4 Keyword Completions

**UpdateExpression keywords:**
- `SET`, `REMOVE`, `ADD`, `DELETE`

**Logical operators:**
- `AND`, `OR`, `NOT`

### 4.5 Attribute Name Completions

When schema is available:

```json
{
  "label": "ProductName",
  "kind": 6,
  "detail": "String (S)",
  "documentation": "Partition key",
  "sortText": "00_ProductName"
}
```

**Reserved word handling:**
If an attribute name is a reserved word (e.g., `Date`, `Data`), suggest with `#` prefix:

```json
{
  "label": "#Date",
  "detail": "Reserved word - use expression attribute name",
  "insertText": "#Date"
}
```

### 4.6 Nested Path Completions

After typing `.`, suggest nested attributes:

```
ProductReviews.  →  FiveStar, FourStar, ThreeStar, ...
```

---

## 5. Hover Documentation

### 5.1 Function Hover

```markdown
### `attribute_exists(path)` → `boolean`

Returns true if the item contains the attribute specified by path.

**Parameters:**
- `path` - Document path to the attribute (e.g., `Pictures.SideView`)

**Example:**
```
attribute_exists(#Pictures.#SideView)
```

**Valid in:** FilterExpression, ConditionExpression

---

**Note:** Function names are case-sensitive.
```

### 5.2 Operator Hover

```markdown
### `BETWEEN ... AND`

Range comparison operator. True if value is within inclusive range.

**Syntax:** `operand BETWEEN lower AND upper`

**Example:**
```
ReplyDateTime BETWEEN :start AND :end
Price BETWEEN :min AND :max
```

**Valid in:**
- ✅ FilterExpression
- ✅ ConditionExpression  
- ✅ KeyConditionExpression (sort key only)
- ❌ ProjectionExpression
- ❌ UpdateExpression
```

### 5.3 Attribute Hover (with schema)

```markdown
### `ProductReviews`

**Type:** Map (M)

**Path:** Top-level attribute

**Nested attributes:**
- `FiveStar` (List)
- `FourStar` (List)
- `ThreeStar` (List)
- `TwoStar` (List)
- `OneStar` (List)
```

---

## 6. Diagnostic Validation

### 6.1 Diagnostic Severity Levels

| Severity | Use Case |
|----------|----------|
| Error | Syntax errors, invalid operators, unknown functions |
| Warning | Reserved words without aliasing, potential type issues |
| Information | Best practice suggestions |
| Hint | Deprecated patterns |

### 6.2 Validation Categories

#### 6.2.1 Syntax Errors

```
# Error: Missing closing parenthesis
attribute_exists(Brand
                  ^~~~
                  Expected ')'

# Error: Invalid operator
ForumName <> :name
           ^~
           '<>' not allowed for partition key in KeyConditionExpression
```

#### 6.2.2 Unknown Functions

```
# Error: Unknown function
is_empty(Brand)
^^^^^^^^
Unknown function 'is_empty'. Did you mean 'attribute_not_exists'?

# Error: Case sensitivity
ATTRIBUTE_EXISTS(Brand)
^^^^^^^^^^^^^^^^
Function names are case-sensitive. Use 'attribute_exists'.
```

#### 6.2.3 Type Mismatches

```
# Warning: Type mismatch (with schema)
Price = :price
       ^~~~~~
       Attribute 'Price' is Number, comparing with String value
```

#### 6.2.4 Invalid Operators for Expression Type

```
# Error: Invalid operator in KeyConditionExpression
ForumName = :name OR Subject = :sub
                   ^~
                   'OR' not allowed in KeyConditionExpression

# Error: Function not allowed
ForumName = :name AND contains(Subject, :sub)
                      ^~~~~~~~
                      'contains' not allowed in KeyConditionExpression
```

#### 6.2.5 Reserved Words

```
# Warning: Reserved word
Date = :date
^^^^
'Date' is a DynamoDB reserved word. Use expression attribute name '#Date'.

Quick Fix: Replace with '#Date' and add ExpressionAttributeNames
```

#### 6.2.6 UpdateExpression Validation

```
# Error: Multiple clauses of same type
SET Price = :p SET Status = :s
                 ^~~
                 Multiple SET clauses not allowed. Combine with commas.

# Fix: SET Price = :p, Status = :s
```

### 6.3 Diagnostic Codes

```
DDB001: SyntaxError
DDB002: UnknownFunction
DDB003: InvalidOperator
DDB004: ReservedWord
DDB005: TypeMismatch
DDB006: InvalidForExpressionType
DDB007: MissingRequiredKey
DDB008: InvalidPath
DDB009: InvalidUpdateClause
```

---

## 7. Schema Awareness

### 7.1 Schema Format

JSON schema file structure:

```json
{
  "tableName": "ProductCatalog",
  "keySchema": {
    "partitionKey": {
      "name": "Id",
      "type": "N"
    },
    "sortKey": null
  },
  "attributeDefinitions": [
    {
      "name": "Id",
      "type": "N"
    },
    {
      "name": "Title",
      "type": "S"
    },
    {
      "name": "Price",
      "type": "N"
    },
    {
      "name": "Tags",
      "type": "SS"
    },
    {
      "name": "ProductReviews",
      "type": "M",
      "attributes": [
        {
          "name": "FiveStar",
          "type": "L"
        }
      ]
    }
  ],
  "globalSecondaryIndexes": [
    {
      "name": "CategoryIndex",
      "keySchema": {
        "partitionKey": { "name": "Category", "type": "S" },
        "sortKey": { "name": "Price", "type": "N" }
      }
    }
  ]
}
```

### 7.2 Schema Loading

**Priority order:**
1. Inline configuration (workspace settings)
2. `dyscount.schema.json` in workspace root
3. `dyscount.schema.yml` in workspace root
4. DynamoDB API call (if credentials configured)

### 7.3 Schema-Based Validation

**Key attribute validation:**
```
# Error: Using non-key attribute in KeyConditionExpression
Title = :title
^^^^^
'Title' is not a key attribute. Key attributes are: Id (partition), SK (sort)
```

**Type-aware suggestions:**
- For String attributes: suggest `begins_with`, `contains`
- For Number attributes: suggest comparison operators
- For Set attributes: suggest `contains`, `size`

### 7.4 Schema Provider Interface

```typescript
interface SchemaProvider {
  /** Load schema for table */
  load(tableName: string): Promise<TableSchema | null>;
  
  /** Watch for schema changes */
  onChange(callback: (schema: TableSchema) => void): void;
  
  /** List available attributes */
  getAttributes(path?: string[]): Attribute[];
  
  /** Check if attribute is a key */
  isKeyAttribute(name: string): boolean;
  
  /** Get attribute type */
  getAttributeType(path: string[]): string | null;
}
```

---

## 8. Configuration

### 8.1 Initialization Options

```json
{
  "dyscount": {
    "defaultExpressionType": "FilterExpression",
    "schemaPath": "./schemas",
    "validateOnType": true,
    "diagnosticDelayMs": 500,
    "suggestReservedWordAliases": true,
    "includeDeprecatedFunctions": false
  }
}
```

### 8.2 Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `defaultExpressionType` | string | `"FilterExpression"` | Default when type cannot be inferred |
| `schemaPath` | string | `"."` | Path to schema file(s) |
| `validateOnType` | boolean | `true` | Validate while typing |
| `diagnosticDelayMs` | number | `500` | Debounce delay for diagnostics |
| `suggestReservedWordAliases` | boolean | `true` | Auto-suggest `#` for reserved words |
| `includeDeprecatedFunctions` | boolean | `false` | Include deprecated function suggestions |

### 8.3 Workspace Configuration

**VS Code settings.json:**

```json
{
  "dyscount.schemaPath": "./schemas",
  "dyscount.validateOnType": true,
  "[dyscount]": {
    "editor.quickSuggestions": {
      "strings": true
    }
  }
}
```

### 8.4 Per-Document Expression Type

Override via document URI or language ID:

```
# Language IDs:
- dyscount-key-condition
- dyscount-filter  
- dyscount-projection
- dyscount-condition
- dyscount-update
```

Or via comment directive:

```
# dyscount: expression-type=KeyConditionExpression
ForumName = :name AND begins_with(Subject, :prefix)
```

---

## 9. Communication Protocol

### 9.1 Transports

#### 9.1.1 Standard IO (Default)

```bash
# Server startup
dyscount-lsp --stdio

# Environment variables
DYSCOUNT_LOG_LEVEL=debug
DYSCOUNT_LOG_FILE=/tmp/dyscount.log
```

#### 9.1.2 TCP Transport (Optional)

```bash
# Server startup
dyscount-lsp --tcp --port 8123

# Or via environment
DYSCOUNT_TRANSPORT=tcp
DYSCOUNT_PORT=8123
DYSCOUNT_HOST=127.0.0.1
```

### 9.2 JSON-RPC Messages

All communication uses JSON-RPC 2.0:

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "textDocument/completion",
  "params": {
    "textDocument": { "uri": "file:///project/query.ddb" },
    "position": { "line": 0, "character": 15 }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "items": [
      {
        "label": "attribute_exists",
        "kind": 3,
        "detail": "function"
      }
    ]
  }
}
```

### 9.3 Message Headers

Content-Length header required:

```
Content-Length: 256\r\n
\r\n
{"jsonrpc":"2.0","id":1,...}
```

### 9.4 Custom Notifications

**Schema updated:**
```json
{
  "jsonrpc": "2.0",
  "method": "dyscount/schemaChanged",
  "params": {
    "tableName": "ProductCatalog",
    "schemaVersion": "2024-01-15T10:30:00Z"
  }
}
```

---

## 10. Editor Integration

### 10.1 VS Code Extension

**package.json:**

```json
{
  "name": "dyscount-vscode",
  "contributes": {
    "languages": [
      {
        "id": "dyscount",
        "aliases": ["DynamoDB Expression", "dyscount"],
        "extensions": [".ddb", ".dexpr"],
        "configuration": "./language-configuration.json"
      },
      {
        "id": "dyscount-key-condition",
        "aliases": ["DynamoDB KeyConditionExpression"]
      },
      {
        "id": "dyscount-filter",
        "aliases": ["DynamoDB FilterExpression"]
      },
      {
        "id": "dyscount-update",
        "aliases": ["DynamoDB UpdateExpression"]
      }
    ],
    "grammars": [
      {
        "language": "dyscount",
        "scopeName": "source.dyscount",
        "path": "./syntaxes/dyscount.tmLanguage.json"
      }
    ],
    "configuration": {
      "type": "object",
      "title": "Dyscount",
      "properties": {
        "dyscount.server.path": {
          "type": "string",
          "default": "dyscount-lsp",
          "description": "Path to dyscount-lsp executable"
        },
        "dyscount.schemaPath": {
          "type": "string",
          "default": "./schemas",
          "description": "Path to schema files"
        },
        "dyscount.validateOnType": {
          "type": "boolean",
          "default": true
        }
      }
    }
  }
}
```

**Extension activation:**

```typescript
// src/extension.ts
import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';

export function activate(context: vscode.ExtensionContext) {
  const serverOptions = {
    command: vscode.workspace.getConfiguration('dyscount').get('server.path', 'dyscount-lsp'),
    args: ['--stdio']
  };

  const clientOptions = {
    documentSelector: [
      { scheme: 'file', language: 'dyscount' },
      { scheme: 'file', language: 'dyscount-key-condition' },
      { scheme: 'file', language: 'dyscount-filter' },
      { scheme: 'file', language: 'dyscount-update' }
    ],
    synchronize: {
      configurationSection: 'dyscount',
      fileEvents: vscode.workspace.createFileSystemWatcher('**/*.schema.json')
    }
  };

  const client = new LanguageClient('dyscount', 'Dyscount LSP', serverOptions, clientOptions);
  context.subscriptions.push(client.start());
}
```

### 10.2 Neovim (nvim-lspconfig)

**Using lspconfig:**

```lua
-- init.lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

-- Define custom configuration
if not configs.dyscount then
  configs.dyscount = {
    default_config = {
      cmd = { 'dyscount-lsp', '--stdio' },
      filetypes = { 'dyscount', 'ddb', 'dexpr' },
      root_dir = lspconfig.util.root_pattern('.git', 'dyscount.schema.json'),
      settings = {
        dyscount = {
          schemaPath = './schemas',
          validateOnType = true
        }
      }
    }
  }
end

lspconfig.dyscount.setup {}
```

**With filetype detection:**

```vim
" Detect DynamoDB expressions in comments
autocmd BufRead,BufNewFile *.js,*.ts,*.py
  \ if search('KeyConditionExpression\|FilterExpression', 'nw') |
  \   setfiletype dyscount |
  \ endif
```

### 10.3 Emacs (lsp-mode)

**Configuration:**

```elisp
;; init.el
(use-package lsp-mode
  :config
  (add-to-list 'lsp-language-id-configuration '(dyscount-mode . "dyscount"))
  
  (lsp-register-client
   (make-lsp-client
    :new-connection (lsp-stdio-connection '("dyscount-lsp" "--stdio"))
    :activation-fn (lsp-activate-on "dyscount")
    :server-id 'dyscount-lsp
    :initialization-options
    '((:dyscount
       (:schemaPath . "./schemas")
       (:validateOnType . t))))))

;; Define major mode
(define-derived-mode dyscount-mode prog-mode "Dyscount"
  "Major mode for DynamoDB expressions."
  (setq comment-start "# ")
  (setq comment-end ""))

(add-to-list 'auto-mode-alist '("\\.ddb\\'" . dyscount-mode))
(add-to-list 'auto-mode-alist '("\\.dexpr\\'" . dyscount-mode))
```

### 10.4 Vim/Neovim (coc.nvim)

**coc-settings.json:**

```json
{
  "languageserver": {
    "dyscount": {
      "command": "dyscount-lsp",
      "args": ["--stdio"],
      "filetypes": ["dyscount", "ddb"],
      "rootPatterns": [".git", "dyscount.schema.json"],
      "initializationOptions": {
        "dyscount": {
          "schemaPath": "./schemas"
        }
      }
    }
  }
}
```

### 10.5 Sublime Text (LSP)

**LSP.sublime-settings:**

```json
{
  "clients": {
    "dyscount": {
      "enabled": true,
      "command": ["dyscount-lsp", "--stdio"],
      "selector": "source.dyscount",
      "initializationOptions": {
        "dyscount": {
          "schemaPath": "./schemas"
        }
      }
    }
  }
}
```

---

## 11. Implementation Architecture

### 11.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Editor/IDE                               │
└──────────────────────┬──────────────────────────────────────┘
                       │ LSP Protocol (stdio/tcp)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Dyscount LSP Server                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  JSON-RPC   │  │   LSP       │  │    Handlers         │ │
│  │  Transport  │◄─┤   Router    │◄─┤  • Completion       │ │
│  │             │  │             │  │  • Hover            │ │
│  └─────────────┘  └─────────────┘  │  • Diagnostics      │ │
│                                     │  • Document Symbol  │ │
│                                     └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Tree-sitter │  │  Expression │  │   Schema Provider   │ │
│  │   Parser    │  │   Analyzer  │  │                     │ │
│  │             │  │             │  │  • JSON Loader      │ │
│  │  Grammar:   │  │  • Context  │  │  • File Watcher     │ │
│  │  DynamoDB   │  │    Detection│  │  • DynamoDB API     │ │
│  │  Expression │  │  • Type     │  │                     │ │
│  │             │  │    Checking │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 Project Structure

```
dyscount-lsp/
├── Cargo.toml
├── src/
│   ├── main.rs              # Entry point
│   ├── server.rs            # LSP server lifecycle
│   ├── handlers/            # LSP method handlers
│   │   ├── mod.rs
│   │   ├── completion.rs
│   │   ├── hover.rs
│   │   ├── diagnostic.rs
│   │   └── document_symbol.rs
│   ├── parser/              # Tree-sitter integration
│   │   ├── mod.rs
│   │   ├── grammar.js       # Tree-sitter grammar
│   │   └── ast.rs
│   ├── expression/          # Expression type handling
│   │   ├── mod.rs
│   │   ├── types.rs         # ExpressionType enum
│   │   ├── key_condition.rs
│   │   ├── filter.rs
│   │   ├── projection.rs
│   │   ├── condition.rs
│   │   └── update.rs
│   ├── schema/              # Schema management
│   │   ├── mod.rs
│   │   ├── types.rs
│   │   ├── loader.rs
│   │   └── provider.rs
│   ├── completion/          # Completion providers
│   │   ├── mod.rs
│   │   ├── functions.rs
│   │   ├── operators.rs
│   │   └── attributes.rs
│   └── docs/                # Documentation data
│       ├── mod.rs
│       └── functions.json
└── schemas/
    └── example.schema.json
```

### 11.3 Tree-sitter Grammar

Simplified grammar for DynamoDB expressions:

```javascript
// grammar.js
module.exports = grammar({
  name: 'dynamodb_expression',

  rules: {
    expression: $ => choice(
      $.condition_expression,
      $.projection_expression,
      $.update_expression
    ),

    // Condition/Filter expression
    condition_expression: $ => choice(
      $.comparison,
      $.between_expression,
      $.in_expression,
      $.function_call,
      $.logical_expression,
      $.parenthesized_expression
    ),

    comparison: $ => seq(
      $.operand,
      $.comparator,
      $.operand
    ),

    comparator: $ => choice('=', '<>', '<', '<=', '>', '>='),

    between_expression: $ => seq(
      $.operand,
      'BETWEEN',
      $.operand,
      'AND',
      $.operand
    ),

    function_call: $ => seq(
      $.function_name,
      '(',
      optional($.function_arguments),
      ')'
    ),

    function_name: $ => choice(
      'attribute_exists',
      'attribute_not_exists',
      'attribute_type',
      'begins_with',
      'contains',
      'size',
      'if_not_exists'  // UpdateExpression only
    ),

    logical_expression: $ => choice(
      seq($.condition_expression, 'AND', $.condition_expression),
      seq($.condition_expression, 'OR', $.condition_expression),
      seq('NOT', $.condition_expression)
    ),

    operand: $ => choice(
      $.path,
      $.expression_attribute_value
    ),

    path: $ => seq(
      $.identifier,
      repeat(choice(
        seq('.', $.identifier),
        seq('[', $.number, ']')
      ))
    ),

    identifier: $ => choice(
      /[a-zA-Z][a-zA-Z0-9_]*/,
      $.expression_attribute_name
    ),

    expression_attribute_name: $ => /#[a-zA-Z][a-zA-Z0-9_]*/,
    expression_attribute_value: $ => /:[a-zA-Z][a-zA-Z0-9_]*/,

    // Projection expression
    projection_expression: $ => seq(
      $.path,
      repeat(seq(',', $.path))
    ),

    // Update expression
    update_expression: $ => repeat1($.update_clause),

    update_clause: $ => choice(
      $.set_clause,
      $.remove_clause,
      $.add_clause,
      $.delete_clause
    ),

    set_clause: $ => seq(
      'SET',
      $.set_action,
      repeat(seq(',', $.set_action))
    ),

    set_action: $ => seq(
      $.path,
      '=',
      $.set_value
    ),

    set_value: $ => choice(
      $.operand,
      seq($.operand, '+', $.operand),
      seq($.operand, '-', $.operand),
      $.function_call
    ),

    remove_clause: $ => seq(
      'REMOVE',
      $.path,
      repeat(seq(',', $.path))
    ),

    add_clause: $ => seq(
      'ADD',
      $.add_action,
      repeat(seq(',', $.add_action))
    ),

    add_action: $ => seq(
      $.path,
      $.expression_attribute_value
    ),

    delete_clause: $ => seq(
      'DELETE',
      $.delete_action,
      repeat(seq(',', $.delete_action))
    ),

    delete_action: $ => seq(
      $.path,
      $.expression_attribute_value
    )
  }
});
```

### 11.4 Parser Integration

```rust
// src/parser/mod.rs
use tree_sitter::Parser;

pub struct ExpressionParser {
    parser: Parser,
}

impl ExpressionParser {
    pub fn new() -> Self {
        let mut parser = Parser::new();
        parser.set_language(tree_sitter_dyscount::language()).unwrap();
        Self { parser }
    }

    pub fn parse(&mut self, source: &str) -> ParseResult {
        let tree = self.parser.parse(source, None)?;
        let root = tree.root_node();
        
        ParseResult {
            tree,
            errors: self.collect_errors(&root),
        }
    }

    fn collect_errors(&self, node: &Node) -> Vec<SyntaxError> {
        // Walk tree and collect ERROR nodes
    }
}
```

### 11.5 Build & Distribution

**Cargo.toml:**

```toml
[package]
name = "dyscount-lsp"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = { version = "1", features = ["full"] }
tower-lsp = "0.20"
tree-sitter = "0.20"
tree-sitter-dyscount = { path = "../tree-sitter-dyscount" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"
clap = { version = "4", features = ["derive"] }
tracing = "0.1"
tracing-subscriber = "0.3"

[profile.release]
opt-level = 3
lto = true
strip = true
```

**Distribution:**

```bash
# Build release binary
cargo build --release

# Install locally
cargo install --path .

# Create npm package for VS Code
npm run package
```

---

## 12. Appendix: Function Reference

### 12.1 Condition/Filter Functions

| Function | Signature | Return | Description |
|----------|-----------|--------|-------------|
| `attribute_exists` | `(path)` | `boolean` | True if attribute exists |
| `attribute_not_exists` | `(path)` | `boolean` | True if attribute does not exist |
| `attribute_type` | `(path, type)` | `boolean` | True if attribute is of specified type |
| `begins_with` | `(path, substr)` | `boolean` | True if string starts with substring |
| `contains` | `(path, operand)` | `boolean` | True if string/set/list contains value |
| `size` | `(path)` | `number` | Returns size of attribute |

### 12.2 UpdateExpression Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `if_not_exists` | `(path, value)` | Returns value if path doesn't exist, else path value |

### 12.3 DynamoDB Data Types

| Type | Code | Description |
|------|------|-------------|
| String | `S` | UTF-8 string |
| Number | `N` | Numeric value (stored as string) |
| Binary | `B` | Base64-encoded binary |
| Boolean | `BOOL` | true/false |
| Null | `NULL` | Null value |
| String Set | `SS` | Set of strings |
| Number Set | `NS` | Set of numbers |
| Binary Set | `BS` | Set of binary values |
| List | `L` | Ordered list of values |
| Map | `M` | Unordered key-value pairs |

### 12.4 Reserved Words (Partial)

Full list: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ReservedWords.html

Common reserved words requiring `#` alias:
- `ABORT`, `ACTION`, `ADD`, `AFTER`, `AGENT`, `AGGREGATE`
- `AND`, `ANY`, `ARRAY`, `AS`, `ASC`
- `BETWEEN`, `BY`
- `CASCADE`, `CASE`, `CAST`, `CHECK`, `CLUSTER`, `COLUMN`, `COMMIT`, `COMPRESS`, `CONFLICT`, `CONNECT`, `CONSTRAINT`, `CREATE`, `CROSS`, `CURRENT`, `CURRENT_DATE`, `CURRENT_TIME`, `CURRENT_TIMESTAMP`, `CURRENT_USER`
- `DATA`, `DATABASE`, `DATE`, `DATETIME`, `DAY`, `DEALLOCATE`, `DEC`, `DECIMAL`, `DECLARE`, `DEFAULT`, `DELETE`, `DESC`, `DESCRIBE`, `DISTINCT`, `DO`, `DOUBLE`, `DROP`
- `ELSE`, `END`, `ESCAPE`, `EXCEPT`, `EXCLUDE`, `EXISTS`, `EXPLAIN`, `EXTRACT`
- `FALSE`, `FIRST`, `FLOAT`, `FOLLOWING`, `FOR`, `FOREIGN`, `FROM`, `FULL`, `FUNCTION`
- `GET`, `GLOBAL`, `GRANT`, `GROUP`, `GSI`
- `HAVING`, `HOUR`
- `IDENTITY`, `IF`, `IGNORE`, `IMMEDIATE`, `IN`, `INCLUDE`, `INCLUSIVE`, `INDEX`, `INDEXED`, `INLINE`, `INNER`, `INOUT`, `INPUT`, `INSERT`, `INT`, `INTEGER`, `INTERSECT`, `INTERVAL`, `INTO`, `IS`
- `JOIN`
- `KEY`
- `LANGUAGE`, `LARGE`, `LAST`, `LATERAL`, `LEADING`, `LEFT`, `LIKE`, `LIMIT`, `LOCAL`, `LOCALTIME`, `LOCALTIMESTAMP`
- `MAP`, `MATCH`, `MATERIALIZED`, `MAX`, `MIN`, `MINUS`, `MINUTE`, `MODULAR`, `MONTH`
- `NATIONAL`, `NATURAL`, `NCHAR`, `NEXT`, `NO`, `NONE`, `NOT`, `NULL`, `NULLIF`, `NUMBER`, `NUMERIC`
- `OF`, `OFF`, `OFFSET`, `OLD`, `ON`, `ONLY`, `OR`, `ORDER`, `OUT`, `OUTER`, `OUTPUT`, `OVER`, `OVERLAPS`
- `PARAMETER`, `PARTITION`, `PATH`, `PERCENT`, `PLAN`, `PRECISION`, `PRIMARY`, `PRIOR`, `PRIVATE`, `PRIVILEGES`, `PROCEDURE`, `PUBLIC`
- `QUERY`, `QUIET`
- `RANGE`, `REAL`, `REFERENCES`, `REFERENCING`, `REGEXP`, `REINDEX`, `RELEASE`, `RENAME`, `REPLACE`, `RESET`, `RESTART`, `RESTRICT`, `RESULT`, `RETURN`, `RETURNS`, `REVOKE`, `RIGHT`, `ROLLBACK`, `ROW`, `ROWS`
| `SCHEMA`, `SECOND`, `SELECT`, `SERIES`, `SESSION`, `SET`, `SET`, `SHOW`, `SIMILAR`, `SIZE`, `SMALLINT`, `SOME`, `SOURCE`, `SPACE`, `SPLIT`, `START`, `STATIC`, `STATISTICS`, `STORED`, `STRING`, `SUBSTRING`, `SUM`, `SYSTEM`
- `TABLE`, `TABLESAMPLE`, `TEMP`, `TEMPORARY`, `THEN`, `TIME`, `TIMESTAMP`, `TO`, `TRAILING`, `TRANSACTION`, `TRANSFORM`, `TRANSLATE`, `TREAT`, `TRIGGER`, `TRIM`, `TRUE`, `TRUNCATE`
- `UESCAPE`, `UNBOUNDED`, `UNION`, `UNIQUE`, `UNKNOWN`, `UNLOGGED`, `UNNEST`, `UNPROTECTED`, `UNTIL`, `UPDATE`, `USER`, `USING`
- `VALUE`, `VALUES`, `VARCHAR`, `VARIABLE`, `VARIADIC`, `VARYING`, `VIEW`, `VOLATILE`
- `WHEN`, `WHERE`, `WIDTH_BUCKET`, `WINDOW`, `WITH`, `WITHIN`, `WITHOUT`, `WORK`, `WRAPPER`, `WRITE`
- `YEAR`
- `ZONE`

---

## 13. Changelog

### 0.1.0 (Draft)

- Initial specification
- Support for all 5 expression types
- Core LSP features: completion, hover, diagnostics, document symbols
- Schema awareness
- Editor integration examples

---

## 14. References

- [LSP Specification](https://microsoft.github.io/language-server-protocol/specifications/specification-current/)
- [DynamoDB Expressions Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.html)
- [DynamoDB Reserved Words](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ReservedWords.html)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
