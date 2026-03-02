"""DynamoDB exception classes"""


class DynamoDBException(Exception):
    """Base DynamoDB exception"""
    def __init__(self, message: str, error_type: str):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


class TableAlreadyExistsException(DynamoDBException):
    def __init__(self, message: str):
        super().__init__(message, "com.amazonaws.dynamodb.v20120810#TableAlreadyExistsException")


class ValidationException(DynamoDBException):
    def __init__(self, message: str):
        super().__init__(message, "com.amazonaws.dynamodb.v20120810#ValidationException")


class ResourceNotFoundException(DynamoDBException):
    def __init__(self, message: str):
        super().__init__(message, "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException")


class ConditionalCheckFailedException(DynamoDBException):
    def __init__(self, message: str):
        super().__init__(message, "com.amazonaws.dynamodb.v20120810#ConditionalCheckFailedException")
