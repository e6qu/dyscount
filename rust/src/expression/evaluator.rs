//! Expression evaluator for DynamoDB conditions and updates

use super::*;
use crate::models::{AttributeValue, Item};
use std::collections::HashMap;

/// Evaluates expressions against items
pub struct ExpressionEvaluator<'a> {
    expression_attribute_names: &'a HashMap<String, String>,
    expression_attribute_values: &'a HashMap<String, AttributeValue>,
}

impl<'a> ExpressionEvaluator<'a> {
    /// Create a new evaluator
    pub fn new(
        names: &'a HashMap<String, String>,
        values: &'a HashMap<String, AttributeValue>,
    ) -> Self {
        Self {
            expression_attribute_names: names,
            expression_attribute_values: values,
        }
    }

    /// Evaluate a condition against an item
    pub fn evaluate_condition(&self, condition: &Condition, item: &Item) -> Result<bool> {
        match condition {
            Condition::Comparison { path, op, value } => {
                let attr_name = self.resolve_path(path);
                let attr_value = item.get(&attr_name);
                let compare_value = self.resolve_value(value)?;
                
                Ok(self.compare(attr_value, &compare_value, *op))
            }
            Condition::Between { path, low, high } => {
                let attr_name = self.resolve_path(path);
                let attr_value = item.get(&attr_name);
                let low_value = self.resolve_value(low)?;
                let high_value = self.resolve_value(high)?;
                
                Ok(self.compare_between(attr_value, &low_value, &high_value))
            }
            Condition::In { path, values } => {
                let attr_name = self.resolve_path(path);
                let attr_value = item.get(&attr_name);
                
                for val_ref in values {
                    let val = self.resolve_value(val_ref)?;
                    if self.values_equal(attr_value, &val) {
                        return Ok(true);
                    }
                }
                Ok(false)
            }
            Condition::AttributeExists { path } => {
                let attr_name = self.resolve_path(path);
                Ok(item.contains_key(&attr_name))
            }
            Condition::AttributeNotExists { path } => {
                let attr_name = self.resolve_path(path);
                Ok(!item.contains_key(&attr_name))
            }
            Condition::And(left, right) => {
                Ok(self.evaluate_condition(left, item)? && self.evaluate_condition(right, item)?)
            }
            Condition::Or(left, right) => {
                Ok(self.evaluate_condition(left, item)? || self.evaluate_condition(right, item)?)
            }
            Condition::Not(inner) => {
                Ok(!self.evaluate_condition(inner, item)?)
            }
        }
    }

    /// Apply update expression to an item
    pub fn apply_update(
        &self,
        update_expr: &UpdateExpression,
        item: &mut Item,
    ) -> Result<()> {
        for action in &update_expr.actions {
            match action.action {
                UpdateActionType::Set => {
                    if let Some(ref value_ref) = action.value {
                        let value = self.resolve_value(value_ref)?;
                        let path = self.resolve_path(&action.path);
                        item.insert(path, value);
                    }
                }
                UpdateActionType::Add => {
                    if let Some(ref value_ref) = action.value {
                        let value = self.resolve_value(value_ref)?;
                        let path = self.resolve_path(&action.path);
                        
                        if let Some(existing) = item.get(&path) {
                            // Try to add numbers
                            if let (Some(existing_n), Some(new_n)) = 
                                (existing.as_n(), value.as_n()) {
                                let existing_f: f64 = existing_n.parse().unwrap_or(0.0);
                                let new_f: f64 = new_n.parse().unwrap_or(0.0);
                                let result = existing_f + new_f;
                                item.insert(path, AttributeValue::N { n: result.to_string() });
                            } else {
                                item.insert(path, value);
                            }
                        } else {
                            item.insert(path, value);
                        }
                    }
                }
                UpdateActionType::Delete => {
                    // DELETE is for sets - simplified implementation
                    if let Some(ref _value_ref) = action.value {
                        let path = self.resolve_path(&action.path);
                        // For sets, we would remove elements - simplified here
                        item.remove(&path);
                    }
                }
                UpdateActionType::Remove => {
                    let path = self.resolve_path(&action.path);
                    item.remove(&path);
                }
            }
        }
        
        Ok(())
    }

    /// Resolve a path (handle # prefix for expression attribute names)
    fn resolve_path(&self, path: &str) -> String {
        if path.starts_with('#') {
            self.expression_attribute_names
                .get(path)
                .cloned()
                .unwrap_or_else(|| path.to_string())
        } else {
            path.to_string()
        }
    }

    /// Resolve a value reference
    fn resolve_value(&self, value_ref: &ValueReference) -> Result<AttributeValue> {
        match value_ref {
            ValueReference::ExpressionValue(name) => {
                self.expression_attribute_values
                    .get(name)
                    .cloned()
                    .ok_or_else(|| ExpressionError::UndefinedValue(name.clone()))
            }
            ValueReference::Literal(val) => Ok(val.clone()),
        }
    }

    /// Compare two values
    fn compare(&self, left: Option<&AttributeValue>, right: &AttributeValue, op: ComparisonOperator) -> bool {
        match (left, right) {
            (Some(l), r) => match op {
                ComparisonOperator::Eq => self.values_equal(Some(l), r),
                ComparisonOperator::Ne => !self.values_equal(Some(l), r),
                ComparisonOperator::Lt => self.compare_values(l, r) == Some(std::cmp::Ordering::Less),
                ComparisonOperator::Le => {
                    let ord = self.compare_values(l, r);
                    ord == Some(std::cmp::Ordering::Less) || ord == Some(std::cmp::Ordering::Equal)
                }
                ComparisonOperator::Gt => self.compare_values(l, r) == Some(std::cmp::Ordering::Greater),
                ComparisonOperator::Ge => {
                    let ord = self.compare_values(l, r);
                    ord == Some(std::cmp::Ordering::Greater) || ord == Some(std::cmp::Ordering::Equal)
                }
            }
            (None, _) => false,
        }
    }

    /// Check if value is between low and high
    fn compare_between(&self, value: Option<&AttributeValue>, low: &AttributeValue, high: &AttributeValue) -> bool {
        match value {
            Some(v) => {
                let ge_low = self.compare_values(v, low).map(|o| o != std::cmp::Ordering::Less).unwrap_or(false);
                let le_high = self.compare_values(v, high).map(|o| o != std::cmp::Ordering::Greater).unwrap_or(false);
                ge_low && le_high
            }
            None => false,
        }
    }

    /// Check if two values are equal
    fn values_equal(&self, left: Option<&AttributeValue>, right: &AttributeValue) -> bool {
        match (left, right) {
            (Some(AttributeValue::S { s: l }), AttributeValue::S { s: r }) => l == r,
            (Some(AttributeValue::N { n: l }), AttributeValue::N { n: r }) => {
                let lf: f64 = l.parse().unwrap_or(0.0);
                let rf: f64 = r.parse().unwrap_or(0.0);
                (lf - rf).abs() < f64::EPSILON
            }
            (Some(AttributeValue::BOOL { bool: l }), AttributeValue::BOOL { bool: r }) => l == r,
            (Some(AttributeValue::NULL { .. }), AttributeValue::NULL { .. }) => true,
            _ => false,
        }
    }

    /// Compare two values for ordering
    fn compare_values(&self, left: &AttributeValue, right: &AttributeValue) -> Option<std::cmp::Ordering> {
        match (left, right) {
            (AttributeValue::S { s: l }, AttributeValue::S { s: r }) => l.partial_cmp(r),
            (AttributeValue::N { n: l }, AttributeValue::N { n: r }) => {
                let lf: f64 = l.parse().unwrap_or(0.0);
                let rf: f64 = r.parse().unwrap_or(0.0);
                lf.partial_cmp(&rf)
            }
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::AttributeValue;

    #[test]
    fn test_evaluate_comparison() {
        let mut item = Item::new();
        item.insert("age".to_string(), AttributeValue::N { n: "25".to_string() });

        let values: HashMap<String, AttributeValue> = [
            ("val".to_string(), AttributeValue::N { n: "20".to_string() })
        ].into_iter().collect();

        let empty_names = HashMap::new();
        let evaluator = ExpressionEvaluator::new(&empty_names, &values);
        
        let condition = Condition::Comparison {
            path: "age".to_string(),
            op: ComparisonOperator::Gt,
            value: ValueReference::ExpressionValue("val".to_string()),
        };

        assert!(evaluator.evaluate_condition(&condition, &item).unwrap());
    }

    #[test]
    fn test_apply_update_set() {
        let mut item = Item::new();
        
        let values: HashMap<String, AttributeValue> = [
            ("name".to_string(), AttributeValue::S { s: "John".to_string() })
        ].into_iter().collect();

        let empty_names = HashMap::new();
        let evaluator = ExpressionEvaluator::new(&empty_names, &values);
        
        let update = UpdateExpression {
            actions: vec![
                UpdateAction {
                    action: UpdateActionType::Set,
                    path: "name".to_string(),
                    value: Some(ValueReference::ExpressionValue("name".to_string())),
                }
            ],
        };

        evaluator.apply_update(&update, &mut item).unwrap();
        assert_eq!(item.get("name").unwrap().as_s(), Some("John"));
    }
}
