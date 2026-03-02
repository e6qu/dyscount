"""Tests for tagging operations (TagResource, UntagResource, ListTagsOfResource)."""

import tempfile

import pytest
from dyscount_core.models.operations import (
    CreateTableRequest,
    TagResourceRequest,
    UntagResourceRequest,
    ListTagsOfResourceRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    KeyType,
    ScalarAttributeType,
)
from dyscount_core.models.errors import ValidationException, ResourceNotFoundException
from dyscount_core.config import Config, LoggingSettings, ServerSettings, StorageSettings
from dyscount_core.services.table_service import TableService


@pytest.fixture
def temp_data_dir():
    """Provide a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config(temp_data_dir):
    """Provide a test configuration."""
    return Config(
        server=ServerSettings(host="127.0.0.1", port=8000),
        storage=StorageSettings(data_directory=temp_data_dir),
        logging=LoggingSettings(level="INFO"),
    )


@pytest.fixture
async def table_service(config):
    """Create a table service for testing."""
    service = TableService(config)
    yield service
    await service.close()


@pytest.fixture
async def test_table(table_service):
    """Create a test table."""
    request = CreateTableRequest(
        TableName="TestTableForTagging",
        KeySchema=[
            KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
        ],
        AttributeDefinitions=[
            AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
        ],
    )
    
    await table_service.create_table(request)
    yield "TestTableForTagging"


class TestTagResource:
    """Test TagResource operation."""
    
    @pytest.mark.asyncio
    async def test_tag_resource_single_tag(self, table_service, test_table):
        """Should add a single tag to a table."""
        request = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Test"}
            ],
        )
        
        response = await table_service.tag_resource(request)
        
        # Response should be empty on success
        assert response is not None
        
        # Verify tag was added
        list_request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        list_response = await table_service.list_tags_of_resource(list_request)
        
        assert len(list_response.tags) == 1
        assert list_response.tags[0]["Key"] == "Environment"
        assert list_response.tags[0]["Value"] == "Test"
    
    @pytest.mark.asyncio
    async def test_tag_resource_multiple_tags(self, table_service, test_table):
        """Should add multiple tags to a table."""
        request = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Test"},
                {"Key": "Owner", "Value": "TeamA"},
                {"Key": "Project", "Value": "Dyscount"},
            ],
        )
        
        await table_service.tag_resource(request)
        
        # Verify tags were added
        list_request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        list_response = await table_service.list_tags_of_resource(list_request)
        
        assert len(list_response.tags) == 3
        tags_dict = {t["Key"]: t["Value"] for t in list_response.tags}
        assert tags_dict["Environment"] == "Test"
        assert tags_dict["Owner"] == "TeamA"
        assert tags_dict["Project"] == "Dyscount"
    
    @pytest.mark.asyncio
    async def test_tag_resource_update_existing_tag(self, table_service, test_table):
        """Should update an existing tag value."""
        # Add initial tag
        request1 = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Test"}
            ],
        )
        await table_service.tag_resource(request1)
        
        # Update tag value
        request2 = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Production"}
            ],
        )
        await table_service.tag_resource(request2)
        
        # Verify tag was updated
        list_request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        list_response = await table_service.list_tags_of_resource(list_request)
        
        assert len(list_response.tags) == 1
        assert list_response.tags[0]["Value"] == "Production"
    
    @pytest.mark.asyncio
    async def test_tag_resource_invalid_arn(self, table_service, test_table):
        """Should reject invalid ARN format."""
        request = TagResourceRequest(
            ResourceArn="invalid-arn-format",
            Tags=[
                {"Key": "Environment", "Value": "Test"}
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.tag_resource(request)
        
        assert "Invalid" in str(exc_info.value) or "ARN" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_tag_resource_table_not_found(self, table_service):
        """Should reject tagging non-existent table."""
        request = TagResourceRequest(
            ResourceArn="arn:aws:dynamodb:local:default:table/NonExistentTable",
            Tags=[
                {"Key": "Environment", "Value": "Test"}
            ],
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await table_service.tag_resource(request)
        
        assert "not found" in str(exc_info.value).lower()


class TestUntagResource:
    """Test UntagResource operation."""
    
    @pytest.mark.asyncio
    async def test_untag_resource_single_tag(self, table_service, test_table):
        """Should remove a single tag from a table."""
        # Add tags first
        tag_request = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Test"},
                {"Key": "Owner", "Value": "TeamA"},
            ],
        )
        await table_service.tag_resource(tag_request)
        
        # Remove one tag
        untag_request = UntagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            TagKeys=["Environment"],
        )
        
        response = await table_service.untag_resource(untag_request)
        
        # Response should be empty on success
        assert response is not None
        
        # Verify tag was removed
        list_request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        list_response = await table_service.list_tags_of_resource(list_request)
        
        assert len(list_response.tags) == 1
        assert list_response.tags[0]["Key"] == "Owner"
    
    @pytest.mark.asyncio
    async def test_untag_resource_multiple_tags(self, table_service, test_table):
        """Should remove multiple tags from a table."""
        # Add tags first
        tag_request = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Test"},
                {"Key": "Owner", "Value": "TeamA"},
                {"Key": "Project", "Value": "Dyscount"},
            ],
        )
        await table_service.tag_resource(tag_request)
        
        # Remove multiple tags
        untag_request = UntagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            TagKeys=["Environment", "Project"],
        )
        
        await table_service.untag_resource(untag_request)
        
        # Verify tags were removed
        list_request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        list_response = await table_service.list_tags_of_resource(list_request)
        
        assert len(list_response.tags) == 1
        assert list_response.tags[0]["Key"] == "Owner"
    
    @pytest.mark.asyncio
    async def test_untag_resource_nonexistent_tag(self, table_service, test_table):
        """Should handle removing non-existent tag gracefully."""
        untag_request = UntagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            TagKeys=["NonExistentTag"],
        )
        
        # Should not raise
        response = await table_service.untag_resource(untag_request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_untag_resource_table_not_found(self, table_service):
        """Should reject untagging non-existent table."""
        request = UntagResourceRequest(
            ResourceArn="arn:aws:dynamodb:local:default:table/NonExistentTable",
            TagKeys=["Environment"],
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await table_service.untag_resource(request)
        
        assert "not found" in str(exc_info.value).lower()


class TestListTagsOfResource:
    """Test ListTagsOfResource operation."""
    
    @pytest.mark.asyncio
    async def test_list_tags_empty(self, table_service, test_table):
        """Should return empty list for table with no tags."""
        request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        
        response = await table_service.list_tags_of_resource(request)
        
        assert response.tags == []
        assert response.next_token is None
    
    @pytest.mark.asyncio
    async def test_list_tags_with_tags(self, table_service, test_table):
        """Should return all tags for a table."""
        # Add tags
        tag_request = TagResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}",
            Tags=[
                {"Key": "Environment", "Value": "Test"},
                {"Key": "Owner", "Value": "TeamA"},
            ],
        )
        await table_service.tag_resource(tag_request)
        
        # List tags
        request = ListTagsOfResourceRequest(
            ResourceArn=f"arn:aws:dynamodb:local:default:table/{test_table}"
        )
        
        response = await table_service.list_tags_of_resource(request)
        
        assert len(response.tags) == 2
        tags_dict = {t["Key"]: t["Value"] for t in response.tags}
        assert tags_dict["Environment"] == "Test"
        assert tags_dict["Owner"] == "TeamA"
    
    @pytest.mark.asyncio
    async def test_list_tags_table_not_found(self, table_service):
        """Should reject listing tags for non-existent table."""
        request = ListTagsOfResourceRequest(
            ResourceArn="arn:aws:dynamodb:local:default:table/NonExistentTable"
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await table_service.list_tags_of_resource(request)
        
        assert "not found" in str(exc_info.value).lower()


class TestExtractTableNameFromArn:
    """Test ARN parsing."""
    
    @pytest.mark.asyncio
    async def test_extract_table_name_from_arn_standard(self, table_service):
        """Should extract table name from standard ARN."""
        arn = "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
        table_name = table_service._extract_table_name_from_arn(arn)
        assert table_name == "MyTable"
    
    @pytest.mark.asyncio
    async def test_extract_table_name_from_arn_local(self, table_service):
        """Should extract table name from local ARN."""
        arn = "arn:aws:dynamodb:local:default:table/TestTable"
        table_name = table_service._extract_table_name_from_arn(arn)
        assert table_name == "TestTable"
    
    @pytest.mark.asyncio
    async def test_extract_table_name_from_arn_invalid(self, table_service):
        """Should raise error for invalid ARN."""
        with pytest.raises(ValidationException):
            table_service._extract_table_name_from_arn("invalid-arn")
        
        with pytest.raises(ValidationException):
            table_service._extract_table_name_from_arn("arn:aws:s3:::bucket")
