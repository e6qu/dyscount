//! DynamoDB expression parsing and evaluation

use crate::models::{AttributeValue, Item};
use std::collections::HashMap;

mod parser;
mod evaluator;

pub use parser::{parse_condition_expression, parse_update_expression};
pub use evaluator::ExpressionEvaluator;

/// Represents a parsed condition
#[derive(Debug, Clone)]
pub enum Condition {
    /// Comparison: path op value
    Comparison {
        path: String,
        op: ComparisonOperator,
        value: ValueReference,
    },
    /// Between: path BETWEEN low AND high
    Between {
        path: String,
        low: ValueReference,
        high: ValueReference,
    },
    /// IN: path IN (values...)
    In {
        path: String,
        values: Vec<ValueReference>,
    },
    /// Attribute exists check
    AttributeExists {
        path: String,
    },
    /// Attribute not exists check
    AttributeNotExists {
        path: String,
    },
    /// Begins with check: begins_with(path, value)
    BeginsWith {
        path: String,
        value: ValueReference,
    },
    /// Contains check: contains(path, value)
    Contains {
        path: String,
        value: ValueReference,
    },
    /// Logical AND of conditions
    And(Box<Condition>, Box<Condition>),
    /// Logical OR of conditions
    Or(Box<Condition>, Box<Condition>),
    /// Logical NOT of condition
    Not(Box<Condition>),
}

/// Comparison operators
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ComparisonOperator {
    Eq,  // =
    Ne,  // <>
    Lt,  // <
    Le,  // <=
    Gt,  // >
    Ge,  // >=
}

/// Reference to a value in expression attribute values
#[derive(Debug, Clone)]
pub enum ValueReference {
    /// Expression attribute value (:name)
    ExpressionValue(String),
    /// Literal value
    Literal(AttributeValue),
}

/// Update action type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum UpdateActionType {
    Set,
    Add,
    Delete,
    Remove,
}

/// A single update action
#[derive(Debug, Clone)]
pub struct UpdateAction {
    pub action: UpdateActionType,
    pub path: String,
    pub value: Option<ValueReference>,
}

/// Parsed update expression
#[derive(Debug, Clone)]
pub struct UpdateExpression {
    pub actions: Vec<UpdateAction>,
}

/// Error type for expression operations
#[derive(Debug, thiserror::Error)]
pub enum ExpressionError {
    #[error("Parse error: {0}")]
    ParseError(String),
    #[error("Evaluation error: {0}")]
    EvaluationError(String),
    #[error("Undefined value: {0}")]
    UndefinedValue(String),
    #[error("Invalid operation: {0}")]
    InvalidOperation(String),
}

/// Result type for expression operations
pub type Result<T> = std::result::Result<T, ExpressionError>;
