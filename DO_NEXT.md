# Do Next - M2 IN PROGRESS

## ✅ Completed Milestones

### M1: Foundation (All 9 Phases) ✅
- 36 DynamoDB operations implemented
- 389 tests across 4 languages (Python, Go, Rust, Zig)
- 100% complete

### M2 Phase 1: Time-to-Live (TTL) ✅
- UpdateTimeToLive - Enable/disable TTL on tables
- DescribeTimeToLive - Get TTL configuration
- Background cleanup process for expired items
- 12 TTL tests passing

---

## 🚀 Current Phase: M2 Phase 2 - Backup & Restore

**Status**: 🟡 **IN PROGRESS**

### M2 Phase 2 Tasks

| Task | Operation | Status | Est. Effort |
|------|-----------|--------|-------------|
| M2P2-T1 | CreateBackup | Planned | 2 days |
| M2P2-T2 | RestoreTableFromBackup | Planned | 2 days |
| M2P2-T3 | ListBackups | Planned | 1 day |
| M2P2-T4 | DeleteBackup | Planned | 1 day |

**Total Effort**: ~6 days

**Operations to Implement**:
1. **CreateBackup** - Creates a backup of an existing table
2. **RestoreTableFromBackup** - Creates a new table from a backup
3. **ListBackups** - Lists all backups for the account
4. **DeleteBackup** - Deletes an existing backup

---

## 📋 Immediate Next Steps

### 1. Create feature branch for M2 Phase 2
```bash
git checkout main
git pull origin main
git checkout -b feature/M2P2-backup-restore
```

### 2. Implement M2P2-T1: CreateBackup

**Goals**:
- Create on-demand backups of DynamoDB tables
- Store backup metadata
- Copy table data to backup storage

**Implementation Notes**:
- Backup storage: `data/backups/<backup_id>/`
- Store table schema + all items
- Metadata: table_name, creation_date, item_count, size_bytes

### 3. Implement M2P2-T2: RestoreTableFromBackup

**Goals**:
- Create new table from backup
- Restore all items
- Preserve original table schema

### 4. Implement M2P2-T3: ListBackups

**Goals**:
- List all backups with filtering
- Pagination support
- Show backup status and metadata

---

## 📊 Project Progress

| Milestone | Phases | Progress |
|-----------|--------|----------|
| M1: Foundation | 9 | ✅ 100% |
| M2 Phase 1: TTL | 1 | ✅ 100% |
| M2 Phase 2: Backup | 1 | 🟡 0% |
| M2 Phase 3: PITR | 1 | ⚪ 0% |
| M2 Phase 4: PartiQL | 1 | ⚪ 0% |
| M3: Global/Streams | 3 | ⚪ 0% |
| M4: Import/Export | 3 | ⚪ 0% |
| **Total** | **20** | **50%** |

---

## 📝 Notes

- M1 complete: 36 operations, 389 tests
- M2P1 (TTL) complete: 2 operations, 12 tests
- Total operations: 38/61 (62%)
- Total tests: 401
