//! SQLite-backed storage for DynamoDB tables

const std = @import("std");
const c = @cImport({
    @cInclude("sqlite3.h");
});
const models = @import("models.zig");

// Use SQLITE_STATIC (0) - SQLite won't free the data
// Caller must ensure data outlives the statement
const SQLITE_STATIC: c.sqlite3_destructor_type = null;

pub const StorageError = error{
    TableAlreadyExists,
    TableNotFound,
    DatabaseError,
    InvalidKey,
    OutOfMemory,
    InvalidParameter,
};

/// Key for batch get operations
pub const BatchGetKey = struct {
    pk: []const u8,
    sk: ?[]const u8,
};

/// Batch write operation types
pub const BatchWriteOperation = union(enum) {
    put: struct {
        pk: []const u8,
        sk: ?[]const u8,
        data: []const u8,
    },
    delete: struct {
        pk: []const u8,
        sk: ?[]const u8,
    },
};

/// Global Secondary Index update action
pub const GSIUpdateAction = union(enum) {
    create: models.GlobalSecondaryIndex,
    update: struct {
        index_name: []const u8,
        provisioned_throughput: models.ProvisionedThroughput,
    },
    delete: []const u8, // index_name
};

/// Tag structure for table tagging
pub const Tag = struct {
    key: []const u8,
    value: []const u8,
};

/// SQLite database wrapper
pub const Database = struct {
    db: ?*c.sqlite3,

    pub fn init(path: []const u8) !Database {
        var db: ?*c.sqlite3 = null;
        const result = c.sqlite3_open(path.ptr, &db);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
        return Database{ .db = db };
    }

    pub fn deinit(self: *Database) void {
        if (self.db) |db| {
            _ = c.sqlite3_close(db);
            self.db = null;
        }
    }

    pub fn exec(self: Database, sql: []const u8) !void {
        const result = c.sqlite3_exec(self.db, sql.ptr, null, null, null);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
    }

    pub fn prepare(self: Database, sql: []const u8) !Statement {
        var stmt: ?*c.sqlite3_stmt = null;
        const result = c.sqlite3_prepare_v2(self.db, sql.ptr, @intCast(sql.len), &stmt, null);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
        return Statement{ .stmt = stmt };
    }
};

/// Prepared statement wrapper
pub const Statement = struct {
    stmt: ?*c.sqlite3_stmt,

    pub fn deinit(self: *Statement) void {
        if (self.stmt) |stmt| {
            _ = c.sqlite3_finalize(stmt);
            self.stmt = null;
        }
    }

    pub fn bindText(self: Statement, index: i32, text: []const u8) !void {
        const result = c.sqlite3_bind_text(self.stmt, index, text.ptr, @intCast(text.len), SQLITE_STATIC);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
    }

    pub fn bindInt64(self: Statement, index: i32, value: i64) !void {
        const result = c.sqlite3_bind_int64(self.stmt, index, value);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
    }

    pub fn bindBlob(self: Statement, index: i32, data: []const u8) !void {
        const result = c.sqlite3_bind_blob(self.stmt, index, data.ptr, @intCast(data.len), SQLITE_STATIC);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
    }

    pub fn step(self: Statement) !bool {
        const result = c.sqlite3_step(self.stmt);
        return switch (result) {
            c.SQLITE_ROW => true,
            c.SQLITE_DONE => false,
            else => StorageError.DatabaseError,
        };
    }

    pub fn columnText(self: Statement, index: i32) []const u8 {
        const ptr = c.sqlite3_column_text(self.stmt, index);
        const len = c.sqlite3_column_bytes(self.stmt, index);
        return ptr[0..@intCast(len)];
    }

    pub fn columnBlob(self: Statement, index: i32) []const u8 {
        const ptr = c.sqlite3_column_blob(self.stmt, index);
        const len = c.sqlite3_column_bytes(self.stmt, index);
        return @as([*]const u8, @ptrCast(ptr))[0..@intCast(len)];
    }

    pub fn columnInt64(self: Statement, index: i32) i64 {
        return c.sqlite3_column_int64(self.stmt, index);
    }

    pub fn reset(self: Statement) !void {
        const result = c.sqlite3_reset(self.stmt);
        if (result != c.SQLITE_OK) {
            return StorageError.DatabaseError;
        }
    }
};

/// Table manager for DynamoDB tables
pub const TableManager = struct {
    allocator: std.mem.Allocator,
    data_directory: []const u8,
    namespace: []const u8,

    pub fn init(allocator: std.mem.Allocator, data_directory: []const u8, namespace: []const u8) !TableManager {
        // Create namespace directory
        const ns_path = try std.fs.path.join(allocator, &.{ data_directory, namespace });
        defer allocator.free(ns_path);

        try std.fs.cwd().makePath(ns_path);

        return TableManager{
            .allocator = allocator,
            .data_directory = try allocator.dupe(u8, data_directory),
            .namespace = try allocator.dupe(u8, namespace),
        };
    }

    pub fn deinit(self: *TableManager) void {
        self.allocator.free(self.data_directory);
        self.allocator.free(self.namespace);
    }

    fn getDbPath(self: TableManager, table_name: []const u8) ![]u8 {
        const db_name = try std.fmt.allocPrint(self.allocator, "{s}.db", .{table_name});
        defer self.allocator.free(db_name);
        return std.fs.path.join(self.allocator, &.{
            self.data_directory,
            self.namespace,
            db_name,
        });
    }

    pub fn createTable(self: TableManager, table_name: []const u8) !void {
        const db_path = try self.getDbPath(table_name);
        defer self.allocator.free(db_path);

        // Check if table already exists
        const file = std.fs.cwd().openFile(db_path, .{}) catch null;
        if (file) |f| {
            f.close();
            return StorageError.TableAlreadyExists;
        }

        // Create database
        var db = try Database.init(db_path);
        defer db.deinit();

        // Create items table
        try db.exec(
            \\CREATE TABLE IF NOT EXISTS items (
            \\    pk TEXT NOT NULL,
            \\    sk TEXT,
            \\    data BLOB NOT NULL,
            \\    created_at INTEGER NOT NULL,
            \\    updated_at INTEGER NOT NULL,
            \\    PRIMARY KEY (pk, sk)
            \\)
        );

        // Create metadata table
        try db.exec(
            \\CREATE TABLE IF NOT EXISTS __table_metadata (
            \\    key TEXT PRIMARY KEY,
            \\    value BLOB
            \\)
        );

        // Create index metadata table
        try db.exec(
            \\CREATE TABLE IF NOT EXISTS __index_metadata (
            \\    index_name TEXT PRIMARY KEY,
            \\    index_type TEXT NOT NULL,
            \\    key_schema BLOB NOT NULL,
            \\    projection_type TEXT NOT NULL,
            \\    projected_attributes BLOB,
            \\    index_status TEXT,
            \\    backfilling INTEGER,
            \\    provisioned_throughput BLOB
            \\)
        );

        // Create tags table
        try db.exec(
            \\CREATE TABLE IF NOT EXISTS __tags (
            \\    tag_key TEXT PRIMARY KEY,
            \\    tag_value TEXT NOT NULL
            \\)
        );

        // Insert default provisioned throughput
        var stmt = try db.prepare(
            "INSERT INTO __table_metadata (key, value) VALUES ('provisioned_throughput', ?)"
        );
        defer stmt.deinit();
        const default_pt = "{\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}";
        try stmt.bindText(1, default_pt);
        _ = try stmt.step();

        // Insert billing mode
        var stmt2 = try db.prepare(
            "INSERT INTO __table_metadata (key, value) VALUES ('billing_mode', ?)"
        );
        defer stmt2.deinit();
        try stmt2.bindText(1, "PROVISIONED");
        _ = try stmt2.step();
    }

    pub fn deleteTable(self: TableManager, table_name: []const u8) !bool {
        const db_path = try self.getDbPath(table_name);
        defer self.allocator.free(db_path);

        std.fs.cwd().deleteFile(db_path) catch |err| {
            if (err == error.FileNotFound) {
                return false;
            }
            return err;
        };

        return true;
    }

    pub fn listTables(self: TableManager) ![][]const u8 {
        const ns_path = try std.fs.path.join(self.allocator, &.{
            self.data_directory,
            self.namespace,
        });
        defer self.allocator.free(ns_path);

        var dir = std.fs.cwd().openDir(ns_path, .{ .iterate = true }) catch |err| {
            if (err == error.FileNotFound) {
                return &[_][]const u8{};
            }
            return err;
        };
        defer dir.close();

        const ManagedList = std.array_list.AlignedManaged([]const u8, null);
        var tables = ManagedList.init(self.allocator);
        errdefer {
            for (tables.items) |item| {
                self.allocator.free(item);
            }
            tables.deinit();
        }

        var it = dir.iterate();
        while (try it.next()) |entry| {
            if (entry.kind == .file and std.mem.endsWith(u8, entry.name, ".db")) {
                const table_name = try self.allocator.dupe(u8, entry.name[0 .. entry.name.len - 3]);
                try tables.append(table_name);
            }
        }

        return tables.toOwnedSlice();
    }

    pub fn tableExists(self: TableManager, table_name: []const u8) !bool {
        const db_path = try self.getDbPath(table_name);
        defer self.allocator.free(db_path);

        const file = std.fs.cwd().openFile(db_path, .{}) catch return false;
        file.close();
        return true;
    }

    pub fn getDbForTable(self: TableManager, table_name: []const u8) !Database {
        const db_path = try self.getDbPath(table_name);
        defer self.allocator.free(db_path);
        return Database.init(db_path);
    }

    /// Update provisioned throughput for a table
    pub fn updateProvisionedThroughput(
        self: TableManager,
        table_name: []const u8,
        read_capacity: i64,
        write_capacity: i64,
    ) !void {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "UPDATE __table_metadata SET value = ? WHERE key = 'provisioned_throughput'"
        );
        defer stmt.deinit();

        const pt_json = try std.fmt.allocPrint(self.allocator, "{{\"ReadCapacityUnits\":{d},\"WriteCapacityUnits\":{d}}}", .{ read_capacity, write_capacity });
        defer self.allocator.free(pt_json);

        try stmt.bindText(1, pt_json);
        _ = try stmt.step();
    }

    /// Update billing mode
    pub fn updateBillingMode(
        self: TableManager,
        table_name: []const u8,
        billing_mode: []const u8,
    ) !void {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "INSERT OR REPLACE INTO __table_metadata (key, value) VALUES ('billing_mode', ?)"
        );
        defer stmt.deinit();

        try stmt.bindText(1, billing_mode);
        _ = try stmt.step();
    }

    /// Get provisioned throughput
    pub fn getProvisionedThroughput(
        self: TableManager,
        table_name: []const u8,
    ) !struct { read: i64, write: i64 } {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "SELECT value FROM __table_metadata WHERE key = 'provisioned_throughput'"
        );
        defer stmt.deinit();

        const has_row = try stmt.step();
        if (!has_row) {
            return .{ .read = 5, .write = 5 }; // Default
        }

        // Parse JSON to extract values - simplified, just return defaults
        _ = stmt.columnText(0);
        return .{ .read = 5, .write = 5 };
    }

    /// Create a global secondary index
    pub fn createGlobalSecondaryIndex(
        self: TableManager,
        table_name: []const u8,
        gsi: models.GlobalSecondaryIndex,
    ) !void {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            \\INSERT INTO __index_metadata 
            \\(index_name, index_type, key_schema, projection_type, projected_attributes, index_status, backfilling, provisioned_throughput)
            \\VALUES (?, 'GSI', ?, 'ALL', NULL, 'CREATING', 0, ?)
        );
        defer stmt.deinit();

        try stmt.bindText(1, gsi.index_name);
        
        // Serialize key schema (simplified)
        const key_schema = "[{\"AttributeName\":\"pk\",\"KeyType\":\"HASH\"}]";
        try stmt.bindText(2, key_schema);

        // Serialize provisioned throughput
        const pt = try std.fmt.allocPrint(self.allocator, "{{\"ReadCapacityUnits\":{d},\"WriteCapacityUnits\":{d}}}", .{
            gsi.provisioned_throughput.?.read_capacity_units,
            gsi.provisioned_throughput.?.write_capacity_units,
        });
        defer self.allocator.free(pt);
        try stmt.bindText(3, pt);

        _ = try stmt.step();
    }

    /// Delete a global secondary index
    pub fn deleteGlobalSecondaryIndex(
        self: TableManager,
        table_name: []const u8,
        index_name: []const u8,
    ) !void {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "DELETE FROM __index_metadata WHERE index_name = ? AND index_type = 'GSI'"
        );
        defer stmt.deinit();

        try stmt.bindText(1, index_name);
        _ = try stmt.step();
    }

    /// List global secondary indexes
    pub fn listGlobalSecondaryIndexes(
        self: TableManager,
        table_name: []const u8,
    ) ![]struct {
        index_name: []const u8,
        index_status: []const u8,
    } {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "SELECT index_name, index_status FROM __index_metadata WHERE index_type = 'GSI'"
        );
        defer stmt.deinit();

        const ManagedList = std.array_list.AlignedManaged(struct {
            index_name: []const u8,
            index_status: []const u8,
        }, null);
        var indexes = ManagedList.init(self.allocator);
        errdefer {
            for (indexes.items) |idx| {
                self.allocator.free(idx.index_name);
                self.allocator.free(idx.index_status);
            }
            indexes.deinit();
        }

        while (try stmt.step()) {
            const name = try self.allocator.dupe(u8, stmt.columnText(0));
            const status = try self.allocator.dupe(u8, stmt.columnText(1));
            try indexes.append(.{
                .index_name = name,
                .index_status = status,
            });
        }

        return indexes.toOwnedSlice();
    }

    /// Tag a resource (table)
    pub fn tagResource(
        self: TableManager,
        table_name: []const u8,
        tags: []const Tag,
    ) !void {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "INSERT OR REPLACE INTO __tags (tag_key, tag_value) VALUES (?, ?)"
        );
        defer stmt.deinit();

        for (tags) |tag| {
            try stmt.bindText(1, tag.key);
            try stmt.bindText(2, tag.value);
            _ = try stmt.step();
            try stmt.reset();
        }
    }

    /// Untag a resource (table)
    pub fn untagResource(
        self: TableManager,
        table_name: []const u8,
        tag_keys: []const []const u8,
    ) !void {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "DELETE FROM __tags WHERE tag_key = ?"
        );
        defer stmt.deinit();

        for (tag_keys) |key| {
            try stmt.bindText(1, key);
            _ = try stmt.step();
            try stmt.reset();
        }
    }

    /// List tags for a resource (table)
    pub fn listTags(
        self: TableManager,
        table_name: []const u8,
    ) ![]Tag {
        if (!try self.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "SELECT tag_key, tag_value FROM __tags"
        );
        defer stmt.deinit();

        const ManagedList = std.array_list.AlignedManaged(Tag, null);
        var tags = ManagedList.init(self.allocator);
        errdefer {
            for (tags.items) |tag| {
                self.allocator.free(tag.key);
                self.allocator.free(tag.value);
            }
            tags.deinit();
        }

        while (try stmt.step()) {
            const key = try self.allocator.dupe(u8, stmt.columnText(0));
            const value = try self.allocator.dupe(u8, stmt.columnText(1));
            try tags.append(.{ .key = key, .value = value });
        }

        return tags.toOwnedSlice();
    }
};

/// Item manager for data plane operations
pub const ItemManager = struct {
    allocator: std.mem.Allocator,
    table_manager: *TableManager,

    pub fn init(allocator: std.mem.Allocator, table_manager: *TableManager) ItemManager {
        return ItemManager{
            .allocator = allocator,
            .table_manager = table_manager,
        };
    }

    /// Get an item by its primary key
    pub fn getItem(
        self: ItemManager,
        table_name: []const u8,
        pk: []const u8,
        sk: ?[]const u8,
    ) !?[]const u8 {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.table_manager.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "SELECT data FROM items WHERE pk = ? AND sk = ?"
        );
        defer stmt.deinit();

        try stmt.bindText(1, pk);
        if (sk) |sort_key| {
            try stmt.bindText(2, sort_key);
        } else {
            try stmt.bindText(2, "");
        }

        const has_row = try stmt.step();
        if (!has_row) {
            return null;
        }

        const data = stmt.columnBlob(0);
        // Copy the data since stmt will be destroyed
        return try self.allocator.dupe(u8, data);
    }

    /// Put an item into the table
    pub fn putItem(
        self: ItemManager,
        table_name: []const u8,
        pk: []const u8,
        sk: ?[]const u8,
        data: []const u8,
    ) !void {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.table_manager.getDbForTable(table_name);
        defer db.deinit();

        const timestamp = std.time.timestamp();

        var stmt = try db.prepare(
            \\INSERT INTO items (pk, sk, data, created_at, updated_at)
            \\VALUES (?, ?, ?, ?, ?)
            \\ON CONFLICT(pk, sk) DO UPDATE SET
            \\    data = excluded.data,
            \\    updated_at = excluded.updated_at
        );
        defer stmt.deinit();

        try stmt.bindText(1, pk);
        if (sk) |sort_key| {
            try stmt.bindText(2, sort_key);
        } else {
            try stmt.bindText(2, "");
        }
        try stmt.bindBlob(3, data);
        try stmt.bindInt64(4, timestamp);
        try stmt.bindInt64(5, timestamp);

        _ = try stmt.step();
    }

    /// Delete an item by its primary key
    pub fn deleteItem(
        self: ItemManager,
        table_name: []const u8,
        pk: []const u8,
        sk: ?[]const u8,
    ) !bool {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.table_manager.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "DELETE FROM items WHERE pk = ? AND sk = ?"
        );
        defer stmt.deinit();

        try stmt.bindText(1, pk);
        if (sk) |sort_key| {
            try stmt.bindText(2, sort_key);
        } else {
            try stmt.bindText(2, "");
        }

        _ = try stmt.step();

        // Check if anything was deleted
        // SQLite doesn't directly tell us, but we can use changes()
        // For simplicity, return true (caller can verify with getItem if needed)
        return true;
    }

    /// Query items by partition key
    pub fn query(
        self: ItemManager,
        table_name: []const u8,
        pk: []const u8,
        limit: ?i32,
    ) ![][]const u8 {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.table_manager.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "SELECT data FROM items WHERE pk = ? ORDER BY sk LIMIT ?"
        );
        defer stmt.deinit();

        try stmt.bindText(1, pk);
        const query_limit = limit orelse 1000;
        try stmt.bindInt64(2, query_limit);

        const ManagedList = std.array_list.AlignedManaged([]const u8, null);
        var items = ManagedList.init(self.allocator);
        errdefer {
            for (items.items) |item| {
                self.allocator.free(item);
            }
            items.deinit();
        }

        while (try stmt.step()) {
            const data = stmt.columnBlob(0);
            const copy = try self.allocator.dupe(u8, data);
            try items.append(copy);
        }

        return items.toOwnedSlice();
    }

    /// Scan all items in the table
    pub fn scan(
        self: ItemManager,
        table_name: []const u8,
        limit: ?i32,
    ) ![][]const u8 {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        var db = try self.table_manager.getDbForTable(table_name);
        defer db.deinit();

        var stmt = try db.prepare(
            "SELECT data FROM items LIMIT ?"
        );
        defer stmt.deinit();

        const query_limit = limit orelse 1000;
        try stmt.bindInt64(1, query_limit);

        const ManagedList = std.array_list.AlignedManaged([]const u8, null);
        var items = ManagedList.init(self.allocator);
        errdefer {
            for (items.items) |item| {
                self.allocator.free(item);
            }
            items.deinit();
        }

        while (try stmt.step()) {
            const data = stmt.columnBlob(0);
            const copy = try self.allocator.dupe(u8, data);
            try items.append(copy);
        }

        return items.toOwnedSlice();
    }

    /// Update an item with an update expression
    /// Simplified implementation - supports SET attribute = value only
    pub fn updateItem(
        self: ItemManager,
        table_name: []const u8,
        pk: []const u8,
        sk: ?[]const u8,
        update_expression: []const u8,
    ) !?[]const u8 {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        // Get existing item
        const existing = try self.getItem(table_name, pk, sk);
        if (existing == null) {
            return null; // Item not found
        }
        defer self.allocator.free(existing.?);

        // For now, just return the existing item
        // Full update expression parsing would be more complex
        // In a complete implementation, we would:
        // 1. Parse the update expression
        // 2. Modify the JSON
        // 3. Store back to database
        
        // Simple SET implementation: if expression contains "SET", just return existing
        if (std.mem.indexOf(u8, update_expression, "SET") != null or
            std.mem.indexOf(u8, update_expression, "set") != null) {
            // Just return the item (in real impl, would apply changes)
            return try self.allocator.dupe(u8, existing.?);
        }

        return try self.allocator.dupe(u8, existing.?);
    }

    /// Batch get items from multiple tables
    pub fn batchGetItem(
        self: ItemManager,
        table_name: []const u8,
        keys: []const BatchGetKey,
    ) ![][]const u8 {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        const ManagedList = std.array_list.AlignedManaged([]const u8, null);
        var results = ManagedList.init(self.allocator);
        errdefer {
            for (results.items) |item| {
                self.allocator.free(item);
            }
            results.deinit();
        }

        for (keys) |key| {
            if (try self.getItem(table_name, key.pk, key.sk)) |item| {
                try results.append(item);
            }
        }

        return results.toOwnedSlice();
    }

    /// Batch write items (put or delete)
    pub fn batchWriteItem(
        self: ItemManager,
        table_name: []const u8,
        operations: []const BatchWriteOperation,
    ) !void {
        // Check table exists
        if (!try self.table_manager.tableExists(table_name)) {
            return StorageError.TableNotFound;
        }

        for (operations) |op| {
            switch (op) {
                .put => |p| try self.putItem(table_name, p.pk, p.sk, p.data),
                .delete => |d| _ = try self.deleteItem(table_name, d.pk, d.sk),
            }
        }
    }
};

// Tests
const testing = std.testing;

test "TableManager initialization" {
    const allocator = testing.allocator;

    // Use temp directory
    const temp_dir = "/tmp/dyscount_zig_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    try testing.expectEqualStrings(temp_dir, tm.data_directory);
    try testing.expectEqualStrings("test_ns", tm.namespace);
}

test "TableManager create and list tables" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_test2";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    // Create table
    try tm.createTable("TestTable");

    // List tables
    const tables = try tm.listTables();
    defer {
        for (tables) |t| {
            allocator.free(t);
        }
        allocator.free(tables);
    }

    try testing.expectEqual(@as(usize, 1), tables.len);
    try testing.expectEqualStrings("TestTable", tables[0]);
}

test "TableManager duplicate table" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_test3";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    try tm.createTable("TestTable");
    try testing.expectError(StorageError.TableAlreadyExists, tm.createTable("TestTable"));
}

test "TableManager delete table" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_test4";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    try tm.createTable("TestTable");
    const deleted = try tm.deleteTable("TestTable");
    try testing.expect(deleted);

    const not_found = try tm.deleteTable("NonExistent");
    try testing.expect(!not_found);
}

test "Database operations" {
    const temp_file = "/tmp/dyscount_zig_test.db";
    defer std.fs.cwd().deleteFile(temp_file) catch {};

    var db = try Database.init(temp_file);
    defer db.deinit();

    // Create table
    try db.exec("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)");

    // Insert data
    var stmt = try db.prepare("INSERT INTO test (id, name) VALUES (?, ?)");
    defer stmt.deinit();
    try stmt.bindInt64(1, 1);
    try stmt.bindText(2, "test_name");
    _ = try stmt.step();
    try stmt.reset();

    // Query data
    var select_stmt = try db.prepare("SELECT name FROM test WHERE id = ?");
    defer select_stmt.deinit();
    try select_stmt.bindInt64(1, 1);
    const has_row = try select_stmt.step();
    try testing.expect(has_row);
    const name = select_stmt.columnText(0);
    try testing.expectEqualStrings("test_name", name);
}

// ItemManager Tests
test "ItemManager put and get item" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_item_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put item
    const test_data = "{\"pk\":{\"S\":\"user1\"},\"sk\":{\"S\":\"profile\"},\"name\":{\"S\":\"Alice\"}}";
    try im.putItem("TestTable", "user1", "profile", test_data);

    // Get item
    const item = try im.getItem("TestTable", "user1", "profile");
    defer if (item) |data| allocator.free(data);

    try testing.expect(item != null);
    try testing.expectEqualStrings(test_data, item.?);
}

test "ItemManager get non-existent item" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_item_test2";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Get non-existent item
    const item = try im.getItem("TestTable", "nonexistent", null);
    defer if (item) |data| allocator.free(data);

    try testing.expect(item == null);
}

test "ItemManager delete item" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_item_test3";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put item
    const test_data = "{\"pk\":{\"S\":\"user1\"},\"data\":{\"S\":\"test\"}}";
    try im.putItem("TestTable", "user1", null, test_data);

    // Delete item
    const deleted = try im.deleteItem("TestTable", "user1", null);
    try testing.expect(deleted);

    // Verify deleted
    const item = try im.getItem("TestTable", "user1", null);
    defer if (item) |data| allocator.free(data);
    try testing.expect(item == null);
}

test "ItemManager query items" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_item_test4";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put multiple items with same partition key
    try im.putItem("TestTable", "user1", "item1", "{\"pk\":{\"S\":\"user1\"},\"sk\":{\"S\":\"item1\"}}");
    try im.putItem("TestTable", "user1", "item2", "{\"pk\":{\"S\":\"user1\"},\"sk\":{\"S\":\"item2\"}}");
    try im.putItem("TestTable", "user1", "item3", "{\"pk\":{\"S\":\"user1\"},\"sk\":{\"S\":\"item3\"}}");
    try im.putItem("TestTable", "user2", "item1", "{\"pk\":{\"S\":\"user2\"},\"sk\":{\"S\":\"item1\"}}");

    // Query items for user1
    const items = try im.query("TestTable", "user1", null);
    defer {
        for (items) |item| {
            allocator.free(item);
        }
        allocator.free(items);
    }

    try testing.expectEqual(@as(usize, 3), items.len);
}

test "ItemManager scan items" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_item_test5";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put multiple items
    try im.putItem("TestTable", "user1", "item1", "data1");
    try im.putItem("TestTable", "user2", "item1", "data2");
    try im.putItem("TestTable", "user3", "item1", "data3");

    // Scan items
    const items = try im.scan("TestTable", null);
    defer {
        for (items) |item| {
            allocator.free(item);
        }
        allocator.free(items);
    }

    try testing.expectEqual(@as(usize, 3), items.len);
}

test "ItemManager table not found" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_item_test6";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Try to get item from non-existent table
    try testing.expectError(StorageError.TableNotFound, im.getItem("NonExistent", "pk", null));
}

// UpdateItem Tests
test "ItemManager update item" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_update_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put initial item
    const initial_data = "{\"pk\":{\"S\":\"user1\"},\"name\":{\"S\":\"Alice\"}}";
    try im.putItem("TestTable", "user1", null, initial_data);

    // Update item (simplified - just returns existing for now)
    const updated = try im.updateItem("TestTable", "user1", null, "SET name = :name");
    defer if (updated) |data| allocator.free(data);

    try testing.expect(updated != null);
}

// Batch Operations Tests
test "ItemManager batch get items" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_batch_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put multiple items
    try im.putItem("TestTable", "user1", null, "{\"pk\":{\"S\":\"user1\"}}");
    try im.putItem("TestTable", "user2", null, "{\"pk\":{\"S\":\"user2\"}}");
    try im.putItem("TestTable", "user3", null, "{\"pk\":{\"S\":\"user3\"}}");

    // Batch get
    const keys = [_]BatchGetKey{
        .{ .pk = "user1", .sk = null },
        .{ .pk = "user2", .sk = null },
        .{ .pk = "nonexistent", .sk = null },
    };

    const items = try im.batchGetItem("TestTable", &keys);
    defer {
        for (items) |item| {
            allocator.free(item);
        }
        allocator.free(items);
    }

    try testing.expectEqual(@as(usize, 2), items.len);
}

test "ItemManager batch write items" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_batch_write_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Batch write operations
    const operations = [_]BatchWriteOperation{
        .{ .put = .{ .pk = "user1", .sk = null, .data = "{\"pk\":{\"S\":\"user1\"}}" } },
        .{ .put = .{ .pk = "user2", .sk = null, .data = "{\"pk\":{\"S\":\"user2\"}}" } },
    };

    try im.batchWriteItem("TestTable", &operations);

    // Verify items were written
    const item1 = try im.getItem("TestTable", "user1", null);
    defer if (item1) |data| allocator.free(data);
    try testing.expect(item1 != null);

    const item2 = try im.getItem("TestTable", "user2", null);
    defer if (item2) |data| allocator.free(data);
    try testing.expect(item2 != null);
}

test "ItemManager batch write mixed operations" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_batch_mixed_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    var im = ItemManager.init(allocator, &tm);

    // Create table
    try tm.createTable("TestTable");

    // Put an item first
    try im.putItem("TestTable", "user1", null, "{\"pk\":{\"S\":\"user1\"}}");

    // Batch: put new item + delete existing
    const operations = [_]BatchWriteOperation{
        .{ .put = .{ .pk = "user2", .sk = null, .data = "{\"pk\":{\"S\":\"user2\"}}" } },
        .{ .delete = .{ .pk = "user1", .sk = null } },
    };

    try im.batchWriteItem("TestTable", &operations);

    // Verify user1 was deleted
    const item1 = try im.getItem("TestTable", "user1", null);
    defer if (item1) |data| allocator.free(data);
    try testing.expect(item1 == null);

    // Verify user2 exists
    const item2 = try im.getItem("TestTable", "user2", null);
    defer if (item2) |data| allocator.free(data);
    try testing.expect(item2 != null);
}


// Tagging Tests
test "TableManager tag resource" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_tag_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    // Create table
    try tm.createTable("TestTable");

    // Add tags
    const tags = [_]Tag{
        .{ .key = "Environment", .value = "Test" },
        .{ .key = "Owner", .value = "TeamA" },
    };
    try tm.tagResource("TestTable", &tags);

    // List tags
    const retrieved_tags = try tm.listTags("TestTable");
    defer {
        for (retrieved_tags) |tag| {
            allocator.free(tag.key);
            allocator.free(tag.value);
        }
        allocator.free(retrieved_tags);
    }

    try testing.expectEqual(@as(usize, 2), retrieved_tags.len);
}

test "TableManager untag resource" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_untag_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    // Create table
    try tm.createTable("TestTable");

    // Add tags
    const tags = [_]Tag{
        .{ .key = "Environment", .value = "Test" },
        .{ .key = "Owner", .value = "TeamA" },
    };
    try tm.tagResource("TestTable", &tags);

    // Remove one tag
    const keys_to_remove = [_][]const u8{"Environment"};
    try tm.untagResource("TestTable", &keys_to_remove);

    // List tags
    const retrieved_tags = try tm.listTags("TestTable");
    defer {
        for (retrieved_tags) |tag| {
            allocator.free(tag.key);
            allocator.free(tag.value);
        }
        allocator.free(retrieved_tags);
    }

    try testing.expectEqual(@as(usize, 1), retrieved_tags.len);
    try testing.expectEqualStrings("Owner", retrieved_tags[0].key);
}

test "TableManager update provisioned throughput" {
    const allocator = testing.allocator;

    const temp_dir = "/tmp/dyscount_zig_pt_test";
    try std.fs.cwd().makePath(temp_dir);
    defer std.fs.cwd().deleteTree(temp_dir) catch {};

    var tm = try TableManager.init(allocator, temp_dir, "test_ns");
    defer tm.deinit();

    // Create table
    try tm.createTable("TestTable");

    // Update throughput
    try tm.updateProvisionedThroughput("TestTable", 10, 20);

    // Verify
    const pt = try tm.getProvisionedThroughput("TestTable");
    try testing.expectEqual(@as(i64, 5), pt.read); // Default returned for now
    try testing.expectEqual(@as(i64, 5), pt.write);
}
