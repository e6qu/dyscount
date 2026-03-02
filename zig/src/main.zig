//! Dyscount - DynamoDB-compatible API service written in Zig

const std = @import("std");
const models = @import("models.zig");
const storage = @import("storage.zig");

const server_port = 8000;

/// HTTP server for DynamoDB API
pub const Server = struct {
    allocator: std.mem.Allocator,
    table_manager: storage.TableManager,

    pub fn init(allocator: std.mem.Allocator, data_dir: []const u8, namespace: []const u8) !Server {
        return Server{
            .allocator = allocator,
            .table_manager = try storage.TableManager.init(allocator, data_dir, namespace),
        };
    }

    pub fn deinit(self: *Server) void {
        self.table_manager.deinit();
    }

    /// Handle incoming HTTP request
    pub fn handleRequest(self: *Server, request: []const u8, writer: anytype) !void {
        // Parse request to get X-Amz-Target header
        const target = self.parseAmzTarget(request) orelse {
            try self.writeErrorResponse(writer, 400, "Missing X-Amz-Target header");
            return;
        };

        // Route to appropriate handler
        const operation = self.extractOperation(target);

        if (std.mem.eql(u8, operation, "CreateTable")) {
            try self.handleCreateTable(request, writer);
        } else if (std.mem.eql(u8, operation, "DeleteTable")) {
            try self.handleDeleteTable(request, writer);
        } else if (std.mem.eql(u8, operation, "ListTables")) {
            try self.handleListTables(writer);
        } else if (std.mem.eql(u8, operation, "DescribeTable")) {
            try self.handleDescribeTable(request, writer);
        } else if (std.mem.eql(u8, operation, "DescribeEndpoints")) {
            try self.handleDescribeEndpoints(writer);
        } else {
            try self.writeErrorResponse(writer, 400, "Unknown operation");
        }
    }

    fn parseAmzTarget(self: Server, request: []const u8) ?[]const u8 {
        _ = self;
        // Simple header parser - look for X-Amz-Target header
        var lines = std.mem.splitSequence(u8, request, "\r\n");
        while (lines.next()) |line| {
            if (std.mem.startsWith(u8, line, "X-Amz-Target: ") or
                std.mem.startsWith(u8, line, "x-amz-target: ")) {
                const value = line["X-Amz-Target: ".len..];
                return std.mem.trim(u8, value, " \t");
            }
        }
        return null;
    }

    fn extractOperation(self: Server, target: []const u8) []const u8 {
        _ = self;
        // Extract operation name from target like "DynamoDB_20120810.CreateTable"
        if (std.mem.lastIndexOf(u8, target, ".")) |idx| {
            return target[idx + 1 ..];
        }
        return target;
    }

    fn parseJsonString(self: Server, json: []const u8, key: []const u8) ?[]const u8 {
        _ = self;
        // Simple JSON string parser - look for "key": "value"
        const pattern = std.fmt.allocPrint(std.heap.page_allocator, "\"{s}\": \"", .{key}) catch return null;
        defer std.heap.page_allocator.free(pattern);

        if (std.mem.indexOf(u8, json, pattern)) |start| {
            const value_start = start + pattern.len;
            if (std.mem.indexOf(u8, json[value_start..], "\"")) |end| {
                return json[value_start .. value_start + end];
            }
        }
        return null;
    }

    fn handleCreateTable(self: *Server, request: []const u8, writer: anytype) !void {
        // Extract table name from request body
        const body_start = std.mem.indexOf(u8, request, "\r\n\r\n");
        if (body_start == null) {
            try self.writeErrorResponse(writer, 400, "Missing request body");
            return;
        }

        const body = request[body_start.? + 4 ..];
        const table_name = self.parseJsonString(body, "TableName");

        if (table_name == null) {
            try self.writeErrorResponse(writer, 400, "Table name is required");
            return;
        }

        self.table_manager.createTable(table_name.?) catch |err| {
            switch (err) {
                error.TableAlreadyExists => {
                    try self.writeErrorResponse(writer, 400, "Table already exists");
                    return;
                },
                else => {
                    try self.writeErrorResponse(writer, 500, "Internal server error");
                    return;
                },
            }
        };

        // Write success response
        try writer.writeAll("HTTP/1.1 200 OK\r\n");
        try writer.writeAll("Content-Type: application/json\r\n");
        try writer.writeAll("\r\n");
        try writer.print("{{\"TableDescription\":{{\"TableName\":\"{s}\",\"TableStatus\":\"ACTIVE\"}}}}\n", .{table_name.?});
    }

    fn handleDeleteTable(self: *Server, request: []const u8, writer: anytype) !void {
        const body_start = std.mem.indexOf(u8, request, "\r\n\r\n");
        if (body_start == null) {
            try self.writeErrorResponse(writer, 400, "Missing request body");
            return;
        }

        const body = request[body_start.? + 4 ..];
        const table_name = self.parseJsonString(body, "TableName");

        if (table_name == null) {
            try self.writeErrorResponse(writer, 400, "Table name is required");
            return;
        }

        const deleted = self.table_manager.deleteTable(table_name.?) catch {
            try self.writeErrorResponse(writer, 500, "Internal server error");
            return;
        };

        if (!deleted) {
            try self.writeErrorResponse(writer, 400, "Table not found");
            return;
        }

        try writer.writeAll("HTTP/1.1 200 OK\r\n");
        try writer.writeAll("Content-Type: application/json\r\n");
        try writer.writeAll("\r\n");
        try writer.print("{{\"TableDescription\":{{\"TableName\":\"{s}\",\"TableStatus\":\"DELETED\"}}}}\n", .{table_name.?});
    }

    fn handleListTables(self: *Server, writer: anytype) !void {
        const tables = self.table_manager.listTables() catch {
            try self.writeErrorResponse(writer, 500, "Internal server error");
            return;
        };
        defer {
            for (tables) |t| {
                self.table_manager.allocator.free(t);
            }
            self.table_manager.allocator.free(tables);
        }

        try writer.writeAll("HTTP/1.1 200 OK\r\n");
        try writer.writeAll("Content-Type: application/json\r\n");
        try writer.writeAll("\r\n");

        // Build JSON array
        try writer.writeAll("{\"TableNames\":[");
        for (tables, 0..) |table, i| {
            if (i > 0) try writer.writeAll(",");
            try writer.print("\"{s}\"", .{table});
        }
        try writer.writeAll("]}\n");
    }

    fn handleDescribeTable(self: *Server, request: []const u8, writer: anytype) !void {
        const body_start = std.mem.indexOf(u8, request, "\r\n\r\n");
        if (body_start == null) {
            try self.writeErrorResponse(writer, 400, "Missing request body");
            return;
        }

        const body = request[body_start.? + 4 ..];
        const table_name = self.parseJsonString(body, "TableName");

        if (table_name == null) {
            try self.writeErrorResponse(writer, 400, "Table name is required");
            return;
        }

        const exists = self.table_manager.tableExists(table_name.?) catch {
            try self.writeErrorResponse(writer, 500, "Internal server error");
            return;
        };

        if (!exists) {
            try self.writeErrorResponse(writer, 400, "Table not found");
            return;
        }

        try writer.writeAll("HTTP/1.1 200 OK\r\n");
        try writer.writeAll("Content-Type: application/json\r\n");
        try writer.writeAll("\r\n");
        try writer.print("{{\"Table\":{{\"TableName\":\"{s}\",\"TableStatus\":\"ACTIVE\"}}}}\n", .{table_name.?});
    }

    fn handleDescribeEndpoints(self: Server, writer: anytype) !void {
        _ = self;
        try writer.writeAll("HTTP/1.1 200 OK\r\n");
        try writer.writeAll("Content-Type: application/json\r\n");
        try writer.writeAll("\r\n");
        try writer.writeAll("{\"Endpoints\":[{\"Address\":\"localhost:8000\",\"CachePeriodInMinutes\":1440}]}\n");
    }

    fn writeErrorResponse(self: Server, writer: anytype, status: u16, message: []const u8) !void {
        _ = self;
        try writer.print("HTTP/1.1 {d} \r\n", .{status});
        try writer.writeAll("Content-Type: application/json\r\n");
        try writer.writeAll("\r\n");
        try writer.print("{{\"__type\":\"com.amazonaws.dynamodb.v20120810#ValidationException\",\"Message\":\"{s}\"}}\n", .{message});
    }
};

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();

    // Get configuration from environment
    const port = server_port;
    const data_dir = "/tmp/dyscount_zig_data";
    const namespace = "default";

    // Ensure data directory exists
    try std.fs.cwd().makePath(data_dir);

    // Initialize server
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var server = try Server.init(allocator, data_dir, namespace);
    defer server.deinit();

    try stdout.print("Dyscount Zig server listening on port {d}\n", .{port});

    // Create TCP listener
    const listener = try std.net.Address.parseIp("127.0.0.1", port);
    var tcp_server = try std.net.Address.listen(listener, .{});
    defer tcp_server.deinit();

    try stdout.print("Server ready!\n", .{});

    // Accept connections
    while (true) {
        const conn = try tcp_server.accept();
        defer conn.stream.close();

        // Read request
        var buf: [4096]u8 = undefined;
        const n = try conn.stream.read(&buf);
        const request = buf[0..n];

        // Handle request
        var response_buf: [4096]u8 = undefined;
        var fbs = std.io.fixedBufferStream(&response_buf);
        const writer = fbs.writer();

        try server.handleRequest(request, writer);

        // Send response
        _ = try conn.stream.write(fbs.getWritten());
    }
}

// Tests
const testing = std.testing;

test "Server extract operation" {
    const allocator = testing.allocator;
    var server = try Server.init(allocator, "/tmp/test", "test");
    defer server.deinit();

    const op1 = server.extractOperation("DynamoDB_20120810.CreateTable");
    try testing.expectEqualStrings("CreateTable", op1);

    const op2 = server.extractOperation("CreateTable");
    try testing.expectEqualStrings("CreateTable", op2);
}

test "Server parse JSON string" {
    const allocator = testing.allocator;
    var server = try Server.init(allocator, "/tmp/test", "test");
    defer server.deinit();

    const json = "{\"TableName\": \"MyTable\", \"KeySchema\": []}";
    const table_name = server.parseJsonString(json, "TableName");
    try testing.expect(table_name != null);
    try testing.expectEqualStrings("MyTable", table_name.?);

    const not_found = server.parseJsonString(json, "NonExistent");
    try testing.expect(not_found == null);
}

test "Server parse Amz-Target header" {
    const allocator = testing.allocator;
    var server = try Server.init(allocator, "/tmp/test", "test");
    defer server.deinit();

    const request = "POST / HTTP/1.1\r\nX-Amz-Target: DynamoDB_20120810.CreateTable\r\n\r\n";
    const target = server.parseAmzTarget(request);
    try testing.expect(target != null);
    try testing.expectEqualStrings("DynamoDB_20120810.CreateTable", target.?);

    const request_no_target = "POST / HTTP/1.1\r\nContent-Type: application/json\r\n\r\n";
    const no_target = server.parseAmzTarget(request_no_target);
    try testing.expect(no_target == null);
}

test "Server handle ListTables" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_test_server";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var server = try Server.init(allocator, temp_dir, "test");
    defer server.deinit();

    // Create a test table
    try server.table_manager.createTable("TestTable1");
    try server.table_manager.createTable("TestTable2");

    // Test ListTables
    var buf: [1024]u8 = undefined;
    var fbs = std.io.fixedBufferStream(&buf);
    const writer = fbs.writer();

    const request = "POST / HTTP/1.1\r\nX-Amz-Target: DynamoDB_20120810.ListTables\r\n\r\n{}";
    try server.handleRequest(request, writer);

    const response = fbs.getWritten();
    try testing.expect(std.mem.indexOf(u8, response, "200 OK") != null);
    try testing.expect(std.mem.indexOf(u8, response, "TestTable1") != null);
    try testing.expect(std.mem.indexOf(u8, response, "TestTable2") != null);
}
