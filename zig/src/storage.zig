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
