"""DynamoDB table metadata models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScalarAttributeType(str, Enum):
    """DynamoDB scalar attribute types."""
    STRING = "S"
    NUMBER = "N"
    BINARY = "B"


class KeyType(str, Enum):
    """DynamoDB key types."""
    HASH = "HASH"  # Partition key
    RANGE = "RANGE"  # Sort key


class BillingMode(str, Enum):
    """DynamoDB billing modes."""
    PROVISIONED = "PROVISIONED"
    PAY_PER_REQUEST = "PAY_PER_REQUEST"


class TableStatus(str, Enum):
    """DynamoDB table statuses."""
    CREATING = "CREATING"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    ACTIVE = "ACTIVE"
    INACCESSIBLE_ENCRYPTION_CREDENTIALS = "INACCESSIBLE_ENCRYPTION_CREDENTIALS"
    ARCHIVING = "ARCHIVING"
    ARCHIVED = "ARCHIVED"


class KeySchemaElement(BaseModel):
    """Represents a key schema element for a table or index.
    
    Attributes:
        AttributeName: The name of a key attribute
        KeyType: The role of the key (HASH or RANGE)
    """
    AttributeName: str
    KeyType: KeyType


class AttributeDefinition(BaseModel):
    """Represents an attribute for describing the key schema.
    
    Attributes:
        AttributeName: A name for the attribute
        AttributeType: The data type (S, N, or B)
    """
    AttributeName: str
    AttributeType: ScalarAttributeType


class ProvisionedThroughput(BaseModel):
    """Represents the provisioned throughput settings for a table or index.
    
    Attributes:
        ReadCapacityUnits: The maximum number of strongly consistent reads per second
        WriteCapacityUnits: The maximum number of writes per second
        NumberOfDecreasesToday: The number of provisioned throughput decreases (read-only)
    """
    ReadCapacityUnits: int = Field(..., ge=1)
    WriteCapacityUnits: int = Field(..., ge=1)
    NumberOfDecreasesToday: Optional[int] = None


class SSESpecification(BaseModel):
    """Server-side encryption specification.
    
    Attributes:
        Enabled: Whether server-side encryption is enabled
        SSEType: Server-side encryption type (AES256 or KMS)
        KMSMasterKeyId: The KMS key ID
    """
    Enabled: Optional[bool] = None
    SSEType: Optional[str] = None
    KMSMasterKeyId: Optional[str] = None


class SSEDescription(BaseModel):
    """Server-side encryption description.
    
    Attributes:
        Status: Encryption status (ENABLED, DISABLED, ENABLING, DISABLING)
        SSEType: Server-side encryption type
        KMSMasterKeyArn: The KMS master key ARN
    """
    Status: Optional[str] = None
    SSEType: Optional[str] = None
    KMSMasterKeyArn: Optional[str] = None


class StreamSpecification(BaseModel):
    """Stream specification for DynamoDB Streams.
    
    Attributes:
        StreamEnabled: Whether DynamoDB Streams is enabled
        StreamViewType: Determines what information is written to the stream
    """
    StreamEnabled: bool
    StreamViewType: Optional[str] = None  # NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES, KEYS_ONLY


class StreamDescription(BaseModel):
    """Stream description.
    
    Attributes:
        StreamLabel: A timestamp for when the stream was created
        StreamStatus: The current status of the stream
        StreamViewType: The stream view type
    """
    StreamLabel: Optional[str] = None
    StreamStatus: Optional[str] = None  # ENABLING, ENABLED, DISABLING, DISABLED
    StreamViewType: Optional[str] = None


class GlobalSecondaryIndex(BaseModel):
    """Represents the properties of a global secondary index.
    
    Attributes:
        IndexName: The name of the global secondary index
        KeySchema: The complete key schema for the index
        Projection: Attributes projected into the index
        ProvisionedThroughput: The provisioned throughput settings
    """
    IndexName: str
    KeySchema: List[KeySchemaElement]
    Projection: Dict[str, Any]  # { ProjectionType: "ALL"|"KEYS_ONLY"|"INCLUDE", NonKeyAttributes: [...] }
    ProvisionedThroughput: Optional[Any] = None  # Using Any to avoid name collision with type


class LocalSecondaryIndex(BaseModel):
    """Represents the properties of a local secondary index.
    
    Attributes:
        IndexName: The name of the local secondary index
        KeySchema: The complete key schema for the index
        Projection: Attributes projected into the index
    """
    IndexName: str
    KeySchema: List[KeySchemaElement]
    Projection: Dict[str, Any]


class TableMetadata(BaseModel):
    """Complete table metadata.
    
    This represents the table description returned by CreateTable, DescribeTable, etc.
    
    Attributes:
        TableName: The name of the table
        TableArn: The Amazon Resource Name (ARN) for the table
        TableId: Unique identifier for the table
        TableStatus: The current state of the table
        KeySchema: The primary key structure for the table
        AttributeDefinitions: List of attribute definitions
        ItemCount: The number of items in the table
        TableSizeBytes: The total size of the specified table in bytes
        CreationDateTime: The date and time when the table was created
        BillingModeSummary: Contains the billing mode details
        ProvisionedThroughput: The provisioned throughput settings
        GlobalSecondaryIndexes: List of global secondary indexes
        LocalSecondaryIndexes: List of local secondary indexes
        StreamSpecification: The current DynamoDB Streams configuration
        LatestStreamArn: The ARN of the stream
        LatestStreamLabel: A timestamp for when the stream was created
        SSEDescription: The description of the server-side encryption status
        DeletionProtectionEnabled: Whether deletion protection is enabled
    """
    model_config = {"populate_by_name": True, "use_enum_values": True}
    
    TableName: str
    TableArn: Optional[str] = None
    TableId: Optional[str] = None
    table_status: TableStatus = Field(default=TableStatus.CREATING, alias="TableStatus")
    KeySchema: List[KeySchemaElement]
    AttributeDefinitions: List[AttributeDefinition]
    ItemCount: int = 0
    TableSizeBytes: int = 0
    CreationDateTime: Optional[datetime] = None
    billing_mode_summary: Optional[Dict[str, Any]] = Field(default=None, alias="BillingModeSummary")
    provisioned_throughput: Optional[ProvisionedThroughput] = Field(default=None, alias="ProvisionedThroughput")
    GlobalSecondaryIndexes: Optional[List[GlobalSecondaryIndex]] = None
    LocalSecondaryIndexes: Optional[List[LocalSecondaryIndex]] = None
    StreamSpecification: Optional[StreamSpecification] = None
    LatestStreamArn: Optional[str] = None
    LatestStreamLabel: Optional[str] = None
    SSEDescription: Optional[SSEDescription] = None
    DeletionProtectionEnabled: Optional[bool] = None

    def get_key_schema_dict(self) -> Dict[str, str]:
        """Get key schema as a dict mapping attribute name to key type.
        
        Returns:
            Dictionary mapping attribute names to 'HASH' or 'RANGE'
        """
        return {elem.AttributeName: elem.KeyType.value for elem in self.KeySchema}

    def get_attribute_type(self, attr_name: str) -> Optional[ScalarAttributeType]:
        """Get the type of an attribute by name.
        
        Args:
            attr_name: Name of the attribute
            
        Returns:
            The scalar attribute type or None if not found
        """
        for attr in self.AttributeDefinitions:
            if attr.AttributeName == attr_name:
                return attr.AttributeType
        return None

    def get_hash_key(self) -> Optional[KeySchemaElement]:
        """Get the hash (partition) key schema element.
        
        Returns:
            The hash key schema element or None
        """
        for elem in self.KeySchema:
            if elem.KeyType == KeyType.HASH:
                return elem
        return None

    def get_range_key(self) -> Optional[KeySchemaElement]:
        """Get the range (sort) key schema element.
        
        Returns:
            The range key schema element or None
        """
        for elem in self.KeySchema:
            if elem.KeyType == KeyType.RANGE:
                return elem
        return None



