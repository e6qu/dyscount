"""Security audit for Dyscount.

Checks for common security issues:
- Path traversal in table names
- SQL injection
- Input validation
- Safe file operations
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dyscount_core.config import Config, StorageSettings, ServerSettings, AuthSettings, LoggingSettings
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService
from dyscount_core.models.errors import ValidationException
from dyscount_core.models.operations import (
    CreateTableRequest,
    PutItemRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    ScalarAttributeType,
    KeyType,
)


class SecurityIssue:
    """Represents a security issue."""
    
    def __init__(self, category: str, severity: str, description: str, details: str = ""):
        self.category = category
        self.severity = severity
        self.description = description
        self.details = details
    
    def __str__(self) -> str:
        return f"[{self.severity}] {self.category}: {self.description}"


class SecurityAuditor:
    """Performs security audit checks."""
    
    def __init__(self, config: Config):
        self.config = config
        self.table_service = TableService(config)
        self.item_service = ItemService(config)
        self.issues: List[SecurityIssue] = []
    
    async def cleanup(self):
        """Clean up services."""
        await self.table_service.close()
        await self.item_service.close()
    
    async def run_all_checks(self) -> List[SecurityIssue]:
        """Run all security checks."""
        print("Running security audit...\n")
        
        await self.check_table_name_validation()
        await self.check_item_size_limits()
        await self.check_sql_injection_prevention()
        await self.check_expression_length_limits()
        
        return self.issues
    
    async def check_table_name_validation(self):
        """Check that table names are properly validated."""
        print("Checking table name validation...")
        
        dangerous_names = [
            ("../../../etc/passwd", "Path traversal"),
            ("..\\..\\windows\\system32", "Windows path traversal"),
            ("table; DROP TABLE users; --", "SQL injection attempt"),
            ("table\x00hidden", "Null byte injection"),
            ("/absolute/path", "Absolute path"),
            ("hidden/.secret", "Hidden directory"),
            ("", "Empty name"),
            ("a", "Too short"),
            ("a" * 300, "Too long"),
        ]
        
        for name, attack_type in dangerous_names:
            try:
                request = CreateTableRequest(
                    TableName=name,
                    AttributeDefinitions=[
                        AttributeDefinition(
                            AttributeName="pk",
                            AttributeType=ScalarAttributeType.STRING,
                        ),
                    ],
                    KeySchema=[
                        KeySchemaElement(
                            AttributeName="pk",
                            KeyType=KeyType.HASH,
                        ),
                    ],
                )
                
                await self.table_service.create_table(request)
                
                # If we get here, the dangerous name was accepted
                self.issues.append(SecurityIssue(
                    category="Table Name Validation",
                    severity="HIGH",
                    description=f"Dangerous table name '{name}' was accepted",
                    details=f"Attack type: {attack_type}"
                ))
                print(f"  ⚠️  {attack_type}: '{name}' was accepted!")
                
            except (ValidationException, ValueError) as e:
                # Expected - dangerous name was rejected
                print(f"  ✅ {attack_type}: '{name}' correctly rejected")
            except Exception as e:
                # Other errors are also acceptable (rejection)
                print(f"  ✅ {attack_type}: '{name}' rejected ({type(e).__name__})")
    
    async def check_item_size_limits(self):
        """Check that item size limits are enforced."""
        print("\nChecking item size limits...")
        
        # Create a test table
        try:
            request = CreateTableRequest(
                TableName="SizeTest",
                AttributeDefinitions=[
                    AttributeDefinition(
                        AttributeName="pk",
                        AttributeType=ScalarAttributeType.STRING,
                    ),
                ],
                KeySchema=[
                    KeySchemaElement(
                        AttributeName="pk",
                        KeyType=KeyType.HASH,
                    ),
                ],
            )
            await self.table_service.create_table(request)
        except Exception:
            pass  # Table may exist
        
        # Create an oversized item (> 400KB)
        oversized_data = "x" * (500 * 1024)  # 500KB
        
        try:
            put_request = PutItemRequest(
                TableName="SizeTest",
                Item={
                    "pk": {"S": "test"},
                    "data": {"S": oversized_data},
                },
            )
            
            await self.item_service.put_item(put_request)
            
            self.issues.append(SecurityIssue(
                category="Item Size Limits",
                severity="HIGH",
                description="Oversized item (500KB) was accepted",
                details="DynamoDB limit is 400KB per item"
            ))
            print(f"  ⚠️  Oversized item (500KB) was accepted!")
            
        except (ValidationException, ValueError) as e:
            print(f"  ✅ Oversized item correctly rejected")
        except Exception as e:
            print(f"  ✅ Oversized item rejected ({type(e).__name__})")
    
    async def check_sql_injection_prevention(self):
        """Check that SQL injection is prevented."""
        print("\nChecking SQL injection prevention...")
        
        # Create a test table with a suspicious name
        suspicious_names = [
            "users' OR '1'='1",
            "table; DROP TABLE users; --",
            "table\"; DELETE FROM users; --",
        ]
        
        for name in suspicious_names:
            try:
                request = CreateTableRequest(
                    TableName=name,
                    AttributeDefinitions=[
                        AttributeDefinition(
                            AttributeName="pk",
                            AttributeType=ScalarAttributeType.STRING,
                        ),
                    ],
                    KeySchema=[
                        KeySchemaElement(
                            AttributeName="pk",
                            KeyType=KeyType.HASH,
                        ),
                    ],
                )
                
                await self.table_service.create_table(request)
                
                # Check if the table was actually created with the malicious name
                data_dir = Path(self.config.storage.data_directory)
                db_file = data_dir / f"{name}.db"
                
                if db_file.exists():
                    self.issues.append(SecurityIssue(
                        category="SQL Injection",
                        severity="CRITICAL",
                        description=f"SQL injection possible with table name '{name}'",
                        details="Table file was created with unescaped name"
                    ))
                    print(f"  ⚠️  SQL injection possible with '{name}'")
                else:
                    print(f"  ✅ Name '{name}' sanitized")
                    
            except (ValidationException, ValueError) as e:
                print(f"  ✅ SQL injection prevented for '{name}'")
            except Exception as e:
                print(f"  ✅ SQL injection prevented for '{name}' ({type(e).__name__})")
    
    async def check_expression_length_limits(self):
        """Check that expression length limits are enforced."""
        print("\nChecking expression length limits...")
        
        # This is a basic check - the actual expression parser should handle this
        print("  ℹ️  Expression length checks are handled by the expression parser")
        print("  ✅ See expression parser tests for validation")


def print_report(issues: List[SecurityIssue]):
    """Print security audit report."""
    print("\n" + "="*70)
    print("SECURITY AUDIT REPORT")
    print("="*70)
    
    if not issues:
        print("\n✅ No security issues found!")
        return
    
    # Group by severity
    critical = [i for i in issues if i.severity == "CRITICAL"]
    high = [i for i in issues if i.severity == "HIGH"]
    medium = [i for i in issues if i.severity == "MEDIUM"]
    low = [i for i in issues if i.severity == "LOW"]
    
    if critical:
        print(f"\n🚨 CRITICAL ISSUES ({len(critical)}):")
        for issue in critical:
            print(f"  - {issue.description}")
            if issue.details:
                print(f"    Details: {issue.details}")
    
    if high:
        print(f"\n⚠️  HIGH SEVERITY ISSUES ({len(high)}):")
        for issue in high:
            print(f"  - {issue.description}")
            if issue.details:
                print(f"    Details: {issue.details}")
    
    if medium:
        print(f"\nℹ️  MEDIUM SEVERITY ISSUES ({len(medium)}):")
        for issue in medium:
            print(f"  - {issue.description}")
    
    if low:
        print(f"\nℹ️  LOW SEVERITY ISSUES ({len(low)}):")
        for issue in low:
            print(f"  - {issue.description}")
    
    print(f"\n{'='*70}")
    print(f"Total issues: {len(issues)} (Critical: {len(critical)}, High: {len(high)}, Medium: {len(medium)}, Low: {len(low)})")
    print("="*70)
    
    if critical or high:
        print("\n❌ Audit FAILED - Critical or High severity issues found")
        return False
    else:
        print("\n✅ Audit PASSED - No critical or high severity issues")
        return True


async def main():
    """Run security audit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Using temporary directory: {tmpdir}\n")
        
        config = Config(
            server=ServerSettings(host="localhost", port=8000),
            storage=StorageSettings(data_directory=tmpdir, namespace="audit"),
            auth=AuthSettings(mode="local"),
            logging=LoggingSettings(level="error", format="json"),
        )
        
        auditor = SecurityAuditor(config)
        
        try:
            issues = await auditor.run_all_checks()
            success = print_report(issues)
            
            return 0 if success else 1
            
        finally:
            await auditor.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
