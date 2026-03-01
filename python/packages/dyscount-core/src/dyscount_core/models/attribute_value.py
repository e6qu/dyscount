"""DynamoDB AttributeValue model with serialization support."""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional, Self

from pydantic import BaseModel, model_validator


class AttributeValue(BaseModel):
    """DynamoDB AttributeValue supporting all DynamoDB data types.
    
    DynamoDB uses a JSON wire format where each value is typed with a descriptor:
    - S: String
    - N: Number (as string to preserve precision)
    - B: Binary (base64-encoded in JSON)
    - BOOL: Boolean
    - NULL: Null (value is always true)
    - M: Map (dictionary of AttributeValue)
    - L: List (array of AttributeValue)
    - SS: String Set (array of unique strings)
    - NS: Number Set (array of unique number strings)
    - BS: Binary Set (array of base64-encoded strings)
    """

    S: Optional[str] = None
    N: Optional[str] = None  # Numbers are strings in DynamoDB JSON
    B: Optional[bytes] = None
    BOOL: Optional[bool] = None
    NULL: Optional[bool] = None
    M: Optional[Dict[str, "AttributeValue"]] = None
    L: Optional[List["AttributeValue"]] = None
    SS: Optional[List[str]] = None
    NS: Optional[List[str]] = None  # Number sets store strings
    BS: Optional[List[bytes]] = None

    @model_validator(mode="after")
    def validate_single_type(self) -> Self:
        """Ensure exactly one type is set."""
        fields = ["S", "N", "B", "BOOL", "NULL", "M", "L", "SS", "NS", "BS"]
        set_fields = [f for f in fields if getattr(self, f) is not None]
        if len(set_fields) != 1:
            raise ValueError(f"Exactly one type must be set, got: {set_fields}")
        return self

    def get_type(self) -> str:
        """Return the type descriptor for this attribute value."""
        if self.S is not None:
            return "S"
        if self.N is not None:
            return "N"
        if self.B is not None:
            return "B"
        if self.BOOL is not None:
            return "BOOL"
        if self.NULL is not None:
            return "NULL"
        if self.M is not None:
            return "M"
        if self.L is not None:
            return "L"
        if self.SS is not None:
            return "SS"
        if self.NS is not None:
            return "NS"
        if self.BS is not None:
            return "BS"
        raise ValueError("No type is set")

    def get_value(self) -> Any:
        """Return the underlying value regardless of type."""
        if self.S is not None:
            return self.S
        if self.N is not None:
            return self.N
        if self.B is not None:
            return self.B
        if self.BOOL is not None:
            return self.BOOL
        if self.NULL is not None:
            return None
        if self.M is not None:
            return self.M
        if self.L is not None:
            return self.L
        if self.SS is not None:
            return self.SS
        if self.NS is not None:
            return self.NS
        if self.BS is not None:
            return self.BS
        raise ValueError("No value is set")

    def to_dynamodb_json(self) -> Dict[str, Any]:
        """Convert to DynamoDB JSON format.
        
        Binary values are base64-encoded for JSON serialization.
        """
        if self.S is not None:
            return {"S": self.S}
        if self.N is not None:
            return {"N": self.N}
        if self.B is not None:
            return {"B": base64.b64encode(self.B).decode("ascii")}
        if self.BOOL is not None:
            return {"BOOL": self.BOOL}
        if self.NULL is not None:
            return {"NULL": self.NULL}
        if self.M is not None:
            return {"M": {k: v.to_dynamodb_json() for k, v in self.M.items()}}
        if self.L is not None:
            return {"L": [item.to_dynamodb_json() for item in self.L]}
        if self.SS is not None:
            return {"SS": list(self.SS)}
        if self.NS is not None:
            return {"NS": list(self.NS)}
        if self.BS is not None:
            return {"BS": [base64.b64encode(b).decode("ascii") for b in self.BS]}
        raise ValueError("No value is set")

    @classmethod
    def from_dynamodb_json(cls, data: Dict[str, Any]) -> "AttributeValue":
        """Create an AttributeValue from DynamoDB JSON format.
        
        Args:
            data: DynamoDB JSON format dictionary with type descriptor
            
        Returns:
            AttributeValue instance
            
        Raises:
            ValueError: If the data format is invalid
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        if len(data) != 1:
            raise ValueError(f"Expected exactly one type descriptor, got: {list(data.keys())}")
        
        type_key = list(data.keys())[0]
        value = data[type_key]
        
        if type_key == "S":
            return cls(S=value)
        elif type_key == "N":
            return cls(N=value)
        elif type_key == "B":
            return cls(B=base64.b64decode(value))
        elif type_key == "BOOL":
            return cls(BOOL=value)
        elif type_key == "NULL":
            return cls(NULL=value)
        elif type_key == "M":
            return cls(M={k: cls.from_dynamodb_json(v) for k, v in value.items()})
        elif type_key == "L":
            return cls(L=[cls.from_dynamodb_json(item) for item in value])
        elif type_key == "SS":
            return cls(SS=list(value))
        elif type_key == "NS":
            return cls(NS=list(value))
        elif type_key == "BS":
            return cls(BS=[base64.b64decode(b) for b in value])
        else:
            raise ValueError(f"Unknown type descriptor: {type_key}")

    @classmethod
    def from_python_value(cls, value: Any) -> "AttributeValue":
        """Create an AttributeValue from a Python value (best effort conversion).
        
        Args:
            value: Python value to convert
            
        Returns:
            AttributeValue instance
        """
        if value is None:
            return cls(NULL=True)
        if isinstance(value, bool):
            return cls(BOOL=value)
        if isinstance(value, str):
            return cls(S=value)
        if isinstance(value, int) or isinstance(value, float):
            return cls(N=str(value))
        if isinstance(value, bytes):
            return cls(B=value)
        if isinstance(value, dict):
            return cls(M={k: cls.from_python_value(v) for k, v in value.items()})
        if isinstance(value, list):
            return cls(L=[cls.from_python_value(item) for item in value])
        raise ValueError(f"Cannot convert type {type(value)} to AttributeValue")

    def to_python_value(self) -> Any:
        """Convert to Python native types.
        
        Returns:
            Python native representation of the value
        """
        if self.S is not None:
            return self.S
        if self.N is not None:
            # Try to convert to int or float
            try:
                if "." in self.N or "e" in self.N.lower():
                    return float(self.N)
                return int(self.N)
            except ValueError:
                return self.N
        if self.B is not None:
            return self.B
        if self.BOOL is not None:
            return self.BOOL
        if self.NULL is not None:
            return None
        if self.M is not None:
            return {k: v.to_python_value() for k, v in self.M.items()}
        if self.L is not None:
            return [item.to_python_value() for item in self.L]
        if self.SS is not None:
            return set(self.SS)
        if self.NS is not None:
            return {float(n) if "." in n else int(n) for n in self.NS}
        if self.BS is not None:
            return set(self.BS)
        raise ValueError("No value is set")


def serialize_to_dynamodb_json(item: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Serialize a Python dict to DynamoDB JSON format.
    
    Args:
        item: Dictionary mapping attribute names to AttributeValue or native Python values
        
    Returns:
        DynamoDB JSON format dictionary
    """
    result = {}
    for key, value in item.items():
        if isinstance(value, AttributeValue):
            result[key] = value.to_dynamodb_json()
        else:
            result[key] = AttributeValue.from_python_value(value).to_dynamodb_json()
    return result


def deserialize_dynamodb_json(data: Dict[str, Dict[str, Any]]) -> Dict[str, AttributeValue]:
    """Deserialize DynamoDB JSON format to AttributeValue objects.
    
    Args:
        data: DynamoDB JSON format dictionary
        
    Returns:
        Dictionary mapping attribute names to AttributeValue instances
    """
    return {key: AttributeValue.from_dynamodb_json(value) for key, value in data.items()}
