# DynamoDB Data Types and JSON Protocol Format

This document describes Amazon DynamoDB data types, their JSON wire format representation, and primary key concepts based on official AWS documentation.

---

## Table of Contents

1. [Overview](#overview)
2. [Scalar Types](#scalar-types)
3. [Document Types](#document-types)
4. [Set Types](#set-types)
5. [JSON Wire Format](#json-wire-format)
6. [Primary Key Types](#primary-key-types)
7. [AttributeValue Structure](#attributevalue-structure)
8. [Important Constraints](#important-constraints)

---

## Overview

DynamoDB supports three categories of data types:

- **Scalar Types** - Single value types (String, Number, Binary, Boolean, Null)
- **Document Types** - Complex nested structures (Map, List)
- **Set Types** - Collections of scalar values (String Set, Number Set, Binary Set)

DynamoDB uses JSON as a **transport protocol only**, not as a storage format. The AWS SDKs use JSON to send data to DynamoDB, and DynamoDB responds with JSON.

---

## Scalar Types

Scalar types represent exactly one value.

### String (S)

- Unicode strings with UTF-8 binary encoding
- Minimum length: 0 bytes (if not used as a key)
- Maximum item size: 400 KB (constrained by item size limit)
- String comparison uses byte-level UTF-8 encoding

**JSON Format:**
```json
{"S": "Hello World"}
```

**Primary Key Constraints:**
- Simple primary key (partition key): Maximum 2048 bytes
- Composite primary key (sort key): Maximum 1024 bytes

**Use Cases:**
- Text data, identifiers, dates (ISO 8601 format recommended)

---

### Number (N)

- Variable length representation
- Up to 38 digits of precision
- Leading and trailing zeros are trimmed
- **Always sent as strings in JSON** to preserve precision across languages

**Range:**
- Positive: 1E-130 to 9.9999999999999999999999999999999999999E+125
- Negative: -9.9999999999999999999999999999999999999E+125 to -1E-130

**JSON Format:**
```json
{"N": "123.45"}
```

**Primary Key Constraints:**
- Simple primary key (partition key): Maximum 2048 bytes
- Composite primary key (sort key): Maximum 1024 bytes

**Use Cases:**
- Integers, decimals, timestamps (Unix epoch time)

---

### Binary (B)

- Stores any binary data (compressed text, encrypted data, images)
- Each byte treated as unsigned during comparison
- Must be **base64-encoded** when sent over JSON

**JSON Format:**
```json
{"B": "dGhpcyB0ZXh0IGlzIGJhc2U2NC1lbmNvZGVk"}
```

**Primary Key Constraints:**
- Simple primary key (partition key): Maximum 2048 bytes
- Composite primary key (sort key): Maximum 1024 bytes

**Use Cases:**
- Binary payloads, encrypted data, file content

---

### Boolean (BOOL)

- Stores `true` or `false` values
- Uses native JSON boolean type

**JSON Format:**
```json
{"BOOL": true}
```

**Use Cases:**
- Flags, status indicators, true/false conditions

---

### Null (NULL)

- Represents an attribute with unknown or undefined state
- Uses JSON boolean `true` as the value

**JSON Format:**
```json
{"NULL": true}
```

**Use Cases:**
- Explicitly marking attributes as null

---

## Document Types

Document types can represent complex structures with nested attributes up to **32 levels deep**.

### Map (M)

- Unordered collection of name-value pairs
- Similar to JSON objects
- Values can be any DynamoDB data type (including nested Maps and Lists)

**JSON Format:**
```json
{
  "M": {
    "Name": {"S": "John Doe"},
    "Age": {"N": "30"},
    "Address": {
      "M": {
        "Street": {"S": "123 Main St"},
        "City": {"S": "Anytown"}
      }
    }
  }
}
```

**Use Cases:**
- Complex nested objects, hierarchical data

---

### List (L)

- Ordered collection of values
- Similar to JSON arrays
- Elements can be of different types
- Elements do not need to be homogeneous

**JSON Format:**
```json
{
  "L": [
    {"S": "Cookies"},
    {"S": "Coffee"},
    {"N": "3.14159"},
    {"BOOL": true}
  ]
}
```

**Use Cases:**
- Arrays, ordered collections, mixed-type lists

---

## Set Types

Set types represent multiple scalar values. All elements in a set must be of the same type. Sets do not preserve order.

**Important:** Empty sets are NOT allowed in DynamoDB.

### String Set (SS)

- Collection of unique string values
- JSON array of strings

**JSON Format:**
```json
{"SS": ["Giraffe", "Hippo", "Zebra"]}
```

---

### Number Set (NS)

- Collection of unique number values
- JSON array of number strings (not numbers)

**JSON Format:**
```json
{"NS": ["42.2", "-19", "7.5", "3.14"]}
```

---

### Binary Set (BS)

- Collection of unique binary values
- JSON array of base64-encoded strings

**JSON Format:**
```json
{"BS": ["U3Vubnk=", "UmFpbnk=", "U25vd3k="]}
```

---

## JSON Wire Format

### Type Annotations

Every attribute value in DynamoDB's JSON protocol must be accompanied by a **type descriptor** (type annotation) that tells DynamoDB how to interpret the value.

### Complete Type Descriptor Reference

| Descriptor | Type | JSON Format | Value Type |
|------------|------|-------------|------------|
| `S` | String | `{"S": "Hello"}` | JSON string |
| `N` | Number | `{"N": "123.45"}` | JSON string (number as string) |
| `B` | Binary | `{"B": "dGhpcyB0ZXh0"}` | Base64-encoded string |
| `BOOL` | Boolean | `{"BOOL": true}` | JSON boolean |
| `NULL` | Null | `{"NULL": true}` | JSON boolean (`true`) |
| `M` | Map | `{"M": {"key": {"S": "value"}}}` | JSON object |
| `L` | List | `{"L": [{"S": "item"}]}` | JSON array |
| `SS` | String Set | `{"SS": ["a", "b"]}` | JSON array of strings |
| `NS` | Number Set | `{"NS": ["1", "2"]}` | JSON array of number strings |
| `BS` | Binary Set | `{"BS": ["abc", "def"]}` | JSON array of base64 strings |

### Number Format

**Critical:** Numbers are always represented as **strings** in JSON:

```json
{"N": "123.45"}        // Correct
{"N": 123.45}            // Incorrect - will cause errors
```

This string representation:
- Preserves precision across different programming languages
- Avoids implicit double conversions
- Maintains proper sorting semantics
- Supports fixed-precision numeric values

### Binary Encoding

Binary data must be **base64-encoded** (RFC 4648):

```json
{"B": "dGhpcyBpcyBhIHRlc3Q="}   // "this is a test" encoded
```

### Request Format Example

```http
POST / HTTP/1.1
Host: dynamodb.us-east-1.amazonaws.com
Content-Type: application/x-amz-json-1.0
X-Amz-Target: DynamoDB_20120810.GetItem

{
    "TableName": "Pets",
    "Key": {
        "AnimalType": {"S": "Dog"},
        "Name": {"S": "Fido"}
    }
}
```

### Response Format Example

```json
{
    "Item": {
        "AnimalType": {"S": "Dog"},
        "Name": {"S": "Fido"},
        "Age": {"N": "8"},
        "Breed": {"S": "Beagle"},
        "Colors": {
            "L": [
                {"S": "White"},
                {"S": "Brown"},
                {"S": "Black"}
            ]
        },
        "Vaccinations": {
            "M": {
                "Rabies": {
                    "L": [
                        {"S": "2009-03-17"},
                        {"S": "2011-09-21"}
                    ]
                }
            }
        }
    }
}
```

---

## Primary Key Types

DynamoDB uses primary keys to uniquely identify each item in a table.

### Simple Primary Key (Partition Key Only)

- Composed of **one attribute** (the partition key, also called hash key)
- DynamoDB uses an internal hash function on the partition key value
- **No two items can have the same partition key value**
- Direct access by providing the partition key value

**Characteristics:**
- Also known as: Hash Key
- Partition key attribute must be scalar (String, Number, or Binary)
- Maximum partition key size: 2048 bytes (String or Binary)

**Example Table Structure:**
```
Table: People
Primary Key: PersonID (partition key)

Items:
{ "PersonID": {"S": "101"}, "Name": {"S": "John"} }
{ "PersonID": {"S": "102"}, "Name": {"S": "Jane"} }
```

---

### Composite Primary Key (Partition Key + Sort Key)

- Composed of **two attributes**: partition key + sort key (range key)
- Multiple items can have the same partition key value
- Items with same partition key are stored together, sorted by sort key
- Combination of partition key + sort key must be unique

**Characteristics:**
- Also known as: Hash Key + Range Key
- Both key attributes must be scalar (String, Number, or Binary)
- Partition key max: 2048 bytes (String or Binary)
- Sort key max: 1024 bytes (String or Binary)
- No practical limit on distinct sort key values per partition key

**Item Collection:**
Items with the same partition key form an "item collection".

**Query Flexibility:**
- Query by partition key alone: Returns all items with that partition key
- Query by partition key + sort key condition: Returns subset
- Sort order can be ascending (default) or descending

**Example Table Structure:**
```
Table: Music
Primary Key: Artist (partition key) + SongTitle (sort key)

Items:
{ "Artist": {"S": "No One You Know"}, "SongTitle": {"S": "My Dog Spot"}, ... }
{ "Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Somewhere Down The Road"}, ... }
{ "Artist": {"S": "The Acme Band"}, "SongTitle": {"S": "Still in Love"}, ... }
```

---

## AttributeValue Structure

The `AttributeValue` is the fundamental structure used to represent attribute values in DynamoDB API operations.

### Structure Definition

Each `AttributeValue` is a name-value pair where:
- **Name** is the data type descriptor (one of: S, N, B, BOOL, NULL, M, L, SS, NS, BS)
- **Value** is the data itself in the appropriate format

### Complete Type Specifications

| Type | JSON Key | Value Type | Description |
|------|----------|------------|-------------|
| String | `S` | String | UTF-8 encoded string |
| Number | `N` | String | Numeric value as string |
| Binary | `B` | Base64 String | Base64-encoded binary data |
| Boolean | `BOOL` | Boolean | `true` or `false` |
| Null | `NULL` | Boolean | Always `true` |
| Map | `M` | Object | String to AttributeValue map |
| List | `L` | Array | Array of AttributeValue objects |
| String Set | `SS` | Array of Strings | Unique string values |
| Number Set | `NS` | Array of Strings | Unique number strings |
| Binary Set | `BS` | Array of Strings | Unique base64-encoded values |

### Nested Structure Example

```json
{
    "ProductID": {"S": "PROD-12345"},
    "Name": {"S": "Wireless Mouse"},
    "Price": {"N": "29.99"},
    "InStock": {"BOOL": true},
    "Tags": {"SS": ["electronics", "computer", "wireless"]},
    "Dimensions": {
        "M": {
            "Length": {"N": "4.5"},
            "Width": {"N": "2.5"},
            "Height": {"N": "1.5"},
            "Unit": {"S": "inches"}
        }
    },
    "Reviews": {
        "L": [
            {
                "M": {
                    "Rating": {"N": "5"},
                    "Comment": {"S": "Great product!"}
                }
            },
            {
                "M": {
                    "Rating": {"N": "4"},
                    "Comment": {"NULL": true}
                }
            }
        ]
    },
    "ImageData": {"B": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
}
```

---

## Important Constraints

### Item Size Limits

- Maximum item size: **400 KB** (including attribute names and values)
- Attribute names count toward item size
- Nested levels: Maximum **32 levels deep**

### Primary Key Constraints

- Primary key attributes must be scalar types (String, Number, or Binary only)
- Boolean, Null, Map, List, and Set types **cannot** be used as primary key attributes

### Key Size Limits

| Key Type | String/Binary Max | Number Max |
|----------|-------------------|------------|
| Partition Key (Simple) | 2048 bytes | 38 digits |
| Sort Key (Composite) | 1024 bytes | 38 digits |

### Set Constraints

- Empty sets are **not allowed**
- All elements must be of the same type
- Elements must be unique
- Order is not preserved

### Naming Rules

**Table and Index Names:**
- Length: 3-255 characters
- Characters: `a-z`, `A-Z`, `0-9`, `_`, `-`, `.`
- Case-sensitive
- UTF-8 encoded

**Attribute Names:**
- Minimum: 1 character
- Maximum: 64 KB (but shorter is better for efficiency)
- Special characters `#` and `:` have special meaning
- Reserved words should be avoided

### Reserved Characters

- `#` (hash) - Used for expression attribute names
- `:` (colon) - Used for expression attribute values

---

## References

- [AWS DynamoDB Developer Guide - Data Types](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html)
- [AWS DynamoDB API Reference - AttributeValue](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_AttributeValue.html)
- [AWS DynamoDB Developer Guide - Core Components](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html)
- [AWS DynamoDB Developer Guide - Low-Level API](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.LowLevelAPI.html)
- [RFC 4648 - Base64 Encoding](https://tools.ietf.org/html/rfc4648)
