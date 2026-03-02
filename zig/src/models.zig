//! DynamoDB-compatible data models for Zig

const std = @import("std");

/// DynamoDB attribute value types
pub const AttributeValue = union(enum) {
    S: []const u8,      // String
    N: []const u8,      // Number (stored as string)
    B: []const u8,      // Binary (base64)
    SS: [][]const u8,   // String Set
    NS: [][]const u8,   // Number Set
    BS: [][]const u8,   // Binary Set
    L: []AttributeValue, // List
    M: std.StringHashMap(AttributeValue), // Map
    BOOL: bool,         // Boolean
    NULL: bool,         // Null

    pub fn deinit(self: *AttributeValue, allocator: std.mem.Allocator) void {
        switch (self.*) {
            .S => |s| allocator.free(s),
            .N => |n| allocator.free(n),
            .B => |b| allocator.free(b),
            .SS => |ss| {
                for (ss) |s| allocator.free(s);
                allocator.free(ss);
            },
            .NS => |ns| {
                for (ns) |n| allocator.free(n);
                allocator.free(ns);
            },
            .BS => |bs| {
                for (bs) |b| allocator.free(b);
                allocator.free(bs);
            },
            .L => |l| {
                for (l) |*item| item.deinit(allocator);
                allocator.free(l);
            },
            .M => |*m| {
                var it = m.iterator();
                while (it.next()) |entry| {
                    allocator.free(entry.key_ptr.*);
                    entry.value_ptr.deinit(allocator);
                }
                m.deinit();
            },
            else => {},
        }
    }
};

/// Item is a map of attribute names to attribute values
pub const Item = std.StringHashMap(AttributeValue);

/// Key schema element
pub const KeySchemaElement = struct {
    attribute_name: []const u8,
    key_type: []const u8, // "HASH" or "RANGE"
};

/// Attribute definition
pub const AttributeDefinition = struct {
    attribute_name: []const u8,
    attribute_type: []const u8, // "S", "N", or "B"
};

/// Provisioned throughput
pub const ProvisionedThroughput = struct {
    read_capacity_units: i64,
    write_capacity_units: i64,

    pub fn default() ProvisionedThroughput {
        return .{
            .read_capacity_units = 5,
            .write_capacity_units = 5,
        };
    }
};

/// Projection for secondary indexes
pub const Projection = struct {
    projection_type: []const u8, // "ALL", "KEYS_ONLY", "INCLUDE"
    non_key_attributes: ?[][]const u8 = null,
};

/// Global secondary index
pub const GlobalSecondaryIndex = struct {
    index_name: []const u8,
    key_schema: []const KeySchemaElement,
    projection: Projection,
    provisioned_throughput: ?ProvisionedThroughput = null,
};

/// Local secondary index
pub const LocalSecondaryIndex = struct {
    index_name: []const u8,
    key_schema: []const KeySchemaElement,
    projection: Projection,
};

/// Tag
pub const Tag = struct {
    key: []const u8,
    value: []const u8,
};

/// Billing mode summary
pub const BillingModeSummary = struct {
    billing_mode: []const u8,
    last_update_to_pay_per_request_date_time: ?i64 = null,
};

/// Table metadata
pub const TableMetadata = struct {
    table_name: []const u8,
    table_arn: ?[]const u8 = null,
    table_id: ?[]const u8 = null,
    table_status: []const u8,
    key_schema: []const KeySchemaElement,
    attribute_definitions: []const AttributeDefinition,
    item_count: i64,
    table_size_bytes: i64,
    creation_date_time: i64,
    billing_mode_summary: ?BillingModeSummary = null,
    provisioned_throughput: ?ProvisionedThroughput = null,
    global_secondary_indexes: ?[]const GlobalSecondaryIndex = null,
    local_secondary_indexes: ?[]const LocalSecondaryIndex = null,
    tags: ?[]const Tag = null,
};

/// DynamoDB API error response
pub const ErrorResponse = struct {
    __type: []const u8,
    message: []const u8,

    pub fn validation_exception(msg: []const u8) ErrorResponse {
        return .{
            .__type = "com.amazonaws.dynamodb.v20120810#ValidationException",
            .message = msg,
        };
    }

    pub fn resourceNotFound(msg: []const u8) ErrorResponse {
        return .{
            .__type = "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
            .message = msg,
        };
    }

    pub fn resourceInUse(msg: []const u8) ErrorResponse {
        return .{
            .__type = "com.amazonaws.dynamodb.v20120810#ResourceInUseException",
            .message = msg,
        };
    }

    pub fn internalServerError(msg: []const u8) ErrorResponse {
        return .{
            .__type = "com.amazonaws.dynamodb.v20120810#InternalServerError",
            .message = msg,
        };
    }
};

/// DynamoDB request
pub const DynamoDBRequest = struct {
    // Table operations
    table_name: ?[]const u8 = null,
    key_schema: ?[]const KeySchemaElement = null,
    attribute_definitions: ?[]const AttributeDefinition = null,
    billing_mode: ?[]const u8 = null,
    global_secondary_indexes: ?[]const GlobalSecondaryIndex = null,
    local_secondary_indexes: ?[]const LocalSecondaryIndex = null,
    provisioned_throughput: ?ProvisionedThroughput = null,
    tags: ?[]const Tag = null,
    resource_arn: ?[]const u8 = null,
    tag_keys: ?[][]const u8 = null,

    // Item operations
    key: ?Item = null,
    item: ?Item = null,
    index_name: ?[]const u8 = null,
    consistent_read: ?bool = null,
    exclusive_start_key: ?Item = null,
    expression_attribute_names: ?std.StringHashMap([]const u8) = null,
    expression_attribute_values: ?std.StringHashMap(AttributeValue) = null,
    filter_expression: ?[]const u8 = null,
    key_condition_expression: ?[]const u8 = null,
    limit: ?i32 = null,
    projection_expression: ?[]const u8 = null,
    return_consumed_capacity: ?[]const u8 = null,
    return_values: ?[]const u8 = null,
    scan_index_forward: ?bool = null,
    select: ?[]const u8 = null,
    update_expression: ?[]const u8 = null,
    condition_expression: ?[]const u8 = null,
};

/// DynamoDB response
pub const DynamoDBResponse = struct {
    table_description: ?TableMetadata = null,
    table_names: ?[][]const u8 = null,
    table: ?TableMetadata = null,
    tags: ?[]const Tag = null,
    endpoints: ?[]const Endpoint = null,

    // Item operations
    item: ?Item = null,
    attributes: ?Item = null,
    items: ?[]const Item = null,
    count: ?i32 = null,
    scanned_count: ?i32 = null,
    last_evaluated_key: ?Item = null,
};

/// Endpoint information
pub const Endpoint = struct {
    address: []const u8,
    cache_period_in_minutes: i64,
};

// Tests
const testing = std.testing;

test "AttributeValue creation" {
    const s = AttributeValue{ .S = "test" };
    try testing.expectEqualStrings("test", s.S);

    const n = AttributeValue{ .N = "123" };
    try testing.expectEqualStrings("123", n.N);

    const b = AttributeValue{ .BOOL = true };
    try testing.expect(b.BOOL);

    const null_val = AttributeValue{ .NULL = true };
    try testing.expect(null_val.NULL);
}

test "ProvisionedThroughput default" {
    const pt = ProvisionedThroughput.default();
    try testing.expectEqual(@as(i64, 5), pt.read_capacity_units);
    try testing.expectEqual(@as(i64, 5), pt.write_capacity_units);
}

test "ErrorResponse creation" {
    const err = ErrorResponse.validationException("test error");
    try testing.expectEqualStrings("com.amazonaws.dynamodb.v20120810#ValidationException", err.__type);
    try testing.expectEqualStrings("test error", err.message);
}
