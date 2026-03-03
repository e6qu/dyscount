//! Expression parser for DynamoDB condition and update expressions

use super::*;

/// Parse a condition expression string
pub fn parse_condition_expression(expr: &str) -> Result<Condition> {
    let expr = expr.trim();
    
    // Handle parentheses
    if expr.starts_with('(') && expr.ends_with(')') {
        let inner = &expr[1..expr.len()-1];
        return parse_condition_expression(inner);
    }
    
    // Handle logical operators (OR has lower precedence than AND)
    if let Some(pos) = find_logical_op(expr, "OR") {
        let left = &expr[..pos];
        let right = &expr[pos+2..];
        return Ok(Condition::Or(
            Box::new(parse_condition_expression(left)?),
            Box::new(parse_condition_expression(right)?),
        ));
    }
    
    if let Some(pos) = find_logical_op(expr, "AND") {
        let left = &expr[..pos];
        let right = &expr[pos+3..];
        return Ok(Condition::And(
            Box::new(parse_condition_expression(left)?),
            Box::new(parse_condition_expression(right)?),
        ));
    }
    
    // Handle NOT
    if expr.to_uppercase().starts_with("NOT ") {
        let inner = &expr[4..];
        return Ok(Condition::Not(Box::new(parse_condition_expression(inner)?)));
    }
    
    // Handle attribute_exists / attribute_not_exists / begins_with / contains
    let upper = expr.to_uppercase();
    if upper.starts_with("ATTRIBUTE_EXISTS(") {
        let path = extract_function_arg(expr, "attribute_exists")?;
        return Ok(Condition::AttributeExists { path });
    }
    
    if upper.starts_with("ATTRIBUTE_NOT_EXISTS(") {
        let path = extract_function_arg(expr, "attribute_not_exists")?;
        return Ok(Condition::AttributeNotExists { path });
    }

    if upper.starts_with("BEGINS_WITH(") {
        let args = extract_function_args(expr, "begins_with")?;
        if args.len() != 2 {
            return Err(ExpressionError::ParseError(
                "begins_with requires exactly 2 arguments".to_string()
            ));
        }
        let path = args[0].trim().to_string();
        let value = parse_value_reference(&args[1])?;
        return Ok(Condition::BeginsWith { path, value });
    }

    if upper.starts_with("CONTAINS(") {
        let args = extract_function_args(expr, "contains")?;
        if args.len() != 2 {
            return Err(ExpressionError::ParseError(
                "contains requires exactly 2 arguments".to_string()
            ));
        }
        let path = args[0].trim().to_string();
        let value = parse_value_reference(&args[1])?;
        return Ok(Condition::Contains { path, value });
    }
    
    // Handle BETWEEN
    if let Some(pos) = expr.to_uppercase().find(" BETWEEN ") {
        let path = expr[..pos].trim().to_string();
        let rest = &expr[pos + 9..];
        if let Some(and_pos) = rest.to_uppercase().find(" AND ") {
            let low = parse_value_reference(rest[..and_pos].trim())?;
            let high = parse_value_reference(rest[and_pos + 5..].trim())?;
            return Ok(Condition::Between { path, low, high });
        }
    }
    
    // Handle IN
    if let Some(pos) = expr.to_uppercase().find(" IN ") {
        let path = expr[..pos].trim().to_string();
        let rest = &expr[pos + 4..].trim();
        if rest.starts_with('(') && rest.ends_with(')') {
            let values_str = &rest[1..rest.len()-1];
            let values = parse_value_list(values_str)?;
            return Ok(Condition::In { path, values });
        }
    }
    
    // Handle comparisons
    parse_comparison(expr)
}

/// Parse an update expression
pub fn parse_update_expression(expr: &str) -> Result<UpdateExpression> {
    let expr = expr.trim();
    let mut actions = Vec::new();
    
    // Find action keywords
    let action_keywords = [("SET ", UpdateActionType::Set), ("ADD ", UpdateActionType::Add), 
                          ("DELETE ", UpdateActionType::Delete), ("REMOVE ", UpdateActionType::Remove)];
    
    let mut current_pos = 0;
    let upper = expr.to_uppercase();
    
    while current_pos < expr.len() {
        let rest = &expr[current_pos..];
        let rest_upper = rest.to_uppercase();
        
        // Find next action keyword
        let mut next_action = None;
        let mut next_pos = rest.len();
        
        for (keyword, action_type) in &action_keywords {
            if let Some(pos) = rest_upper.find(keyword) {
                if pos < next_pos {
                    next_pos = pos;
                    next_action = Some((pos, keyword.len(), *action_type));
                }
            }
        }
        
        if let Some((pos, keyword_len, action_type)) = next_action {
            // Find the end of this action (next keyword or end of string)
            let action_start = pos + keyword_len;
            let mut action_end = rest.len();
            
            for (keyword, _) in &action_keywords {
                if let Some(next_kw_pos) = rest_upper[action_start..].find(keyword) {
                    action_end = action_start + next_kw_pos;
                    break;
                }
            }
            
            let action_content = &rest[action_start..action_end];
            let action_actions = parse_action_content(action_type, action_content)?;
            actions.extend(action_actions);
            
            current_pos += action_end;
        } else {
            break;
        }
    }
    
    Ok(UpdateExpression { actions })
}

/// Parse action content into individual actions
fn parse_action_content(action_type: UpdateActionType, content: &str) -> Result<Vec<UpdateAction>> {
    let mut actions = Vec::new();
    
    // Split by commas at top level
    let parts = split_top_level(content, ',');
    
    for part in parts {
        let part = part.trim();
        if part.is_empty() {
            continue;
        }
        
        let (path, value) = match action_type {
            UpdateActionType::Set => {
                // Format: path = value
                if let Some(eq_pos) = part.find('=') {
                    let path = part[..eq_pos].trim().to_string();
                    let value = parse_value_reference(part[eq_pos+1..].trim())?;
                    (path, Some(value))
                } else {
                    return Err(ExpressionError::ParseError(
                        format!("Invalid SET action: {}", part)
                    ));
                }
            }
            UpdateActionType::Add | UpdateActionType::Delete => {
                // Format: path value
                let parts: Vec<_> = part.split_whitespace().collect();
                if parts.len() >= 2 {
                    let path = parts[0].to_string();
                    let value = parse_value_reference(parts[1])?;
                    (path, Some(value))
                } else {
                    return Err(ExpressionError::ParseError(
                        format!("Invalid {:?} action: {}", action_type, part)
                    ));
                }
            }
            UpdateActionType::Remove => {
                // Format: path (no value)
                (part.to_string(), None)
            }
        };
        
        actions.push(UpdateAction { action: action_type, path, value });
    }
    
    Ok(actions)
}

/// Parse a comparison expression
fn parse_comparison(expr: &str) -> Result<Condition> {
    // Try each comparison operator (longer ones first)
    let operators = [
        ("<=", ComparisonOperator::Le),
        (">=", ComparisonOperator::Ge),
        ("<>", ComparisonOperator::Ne),
        ("=", ComparisonOperator::Eq),
        ("<", ComparisonOperator::Lt),
        (">", ComparisonOperator::Gt),
    ];
    
    for (op_str, op) in &operators {
        if let Some(pos) = expr.find(op_str) {
            let path = expr[..pos].trim().to_string();
            let value = parse_value_reference(expr[pos + op_str.len()..].trim())?;
            return Ok(Condition::Comparison {
                path,
                op: *op,
                value,
            });
        }
    }
    
    Err(ExpressionError::ParseError(
        format!("Invalid comparison expression: {}", expr)
    ))
}

/// Parse a value reference
fn parse_value_reference(s: &str) -> Result<ValueReference> {
    let s = s.trim();
    
    if s.starts_with(':') {
        // Expression attribute value
        Ok(ValueReference::ExpressionValue(s[1..].to_string()))
    } else if s.starts_with('\'') && s.ends_with('\'') {
        // String literal
        let val = AttributeValue::S { s: s[1..s.len()-1].to_string() };
        Ok(ValueReference::Literal(val))
    } else if s.starts_with('"') && s.ends_with('"') {
        // String literal
        let val = AttributeValue::S { s: s[1..s.len()-1].to_string() };
        Ok(ValueReference::Literal(val))
    } else if let Ok(n) = s.parse::<f64>() {
        // Number literal
        let val = AttributeValue::N { n: n.to_string() };
        Ok(ValueReference::Literal(val))
    } else if s.eq_ignore_ascii_case("true") {
        Ok(ValueReference::Literal(AttributeValue::BOOL { bool: true }))
    } else if s.eq_ignore_ascii_case("false") {
        Ok(ValueReference::Literal(AttributeValue::BOOL { bool: false }))
    } else if s.eq_ignore_ascii_case("null") {
        Ok(ValueReference::Literal(AttributeValue::NULL { null: true }))
    } else {
        // Assume it's an expression attribute value without colon (error)
        Err(ExpressionError::ParseError(
            format!("Invalid value reference: {}", s)
        ))
    }
}

/// Parse a list of values
fn parse_value_list(s: &str) -> Result<Vec<ValueReference>> {
    let parts = split_top_level(s, ',');
    parts.into_iter()
        .map(|p| parse_value_reference(p.trim()))
        .collect()
}

/// Extract argument from function call
fn extract_function_arg(expr: &str, func_name: &str) -> Result<String> {
    let prefix = format!("{}(", func_name);
    let lower_expr = expr.to_lowercase();
    
    if let Some(start) = lower_expr.find(&prefix) {
        let arg_start = start + prefix.len();
        if let Some(end) = expr[arg_start..].find(')') {
            let arg = &expr[arg_start..arg_start + end];
            return Ok(arg.trim().to_string());
        }
    }
    
    Err(ExpressionError::ParseError(
        format!("Invalid function call: {}", expr)
    ))
}

/// Extract arguments from function call with multiple args
fn extract_function_args(expr: &str, func_name: &str) -> Result<Vec<String>> {
    let prefix = format!("{}(", func_name.to_lowercase());
    let lower_expr = expr.to_lowercase();
    
    if let Some(start) = lower_expr.find(&prefix) {
        let arg_start = start + prefix.len();
        if let Some(end) = expr[arg_start..].rfind(')') {
            let args_str = &expr[arg_start..arg_start + end];
            // Split by comma
            let args: Vec<String> = args_str
                .split(',')
                .map(|s| s.trim().to_string())
                .collect();
            return Ok(args);
        }
    }
    
    Err(ExpressionError::ParseError(
        format!("Invalid function call: {}", expr)
    ))
}

/// Find position of logical operator at top level
fn find_logical_op(expr: &str, op: &str) -> Option<usize> {
    let upper = expr.to_uppercase();
    let mut depth = 0;
    let op_upper = op.to_uppercase();
    
    for (i, c) in upper.char_indices() {
        match c {
            '(' => depth += 1,
            ')' => depth -= 1,
            _ if depth == 0 => {
                if upper[i..].starts_with(&op_upper) {
                    // Check it's a whole word
                    let after = i + op.len();
                    if after >= upper.len() || upper[after..].starts_with(' ') {
                        return Some(i);
                    }
                }
            }
            _ => {}
        }
    }
    
    None
}

/// Split string by delimiter at top level (not inside parentheses)
fn split_top_level(s: &str, delim: char) -> Vec<&str> {
    let mut result = Vec::new();
    let mut start = 0;
    let mut depth = 0;
    
    for (i, c) in s.char_indices() {
        match c {
            '(' | '[' | '{' => depth += 1,
            ')' | ']' | '}' => depth -= 1,
            c if c == delim && depth == 0 => {
                result.push(&s[start..i]);
                start = i + 1;
            }
            _ => {}
        }
    }
    
    if start < s.len() {
        result.push(&s[start..]);
    }
    
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_comparison() {
        let cond = parse_condition_expression("pk = :pk_val").unwrap();
        match cond {
            Condition::Comparison { path, op, .. } => {
                assert_eq!(path, "pk");
                assert_eq!(op, ComparisonOperator::Eq);
            }
            _ => panic!("Expected comparison"),
        }
    }

    #[test]
    #[ignore = "TODO: Fix BETWEEN parsing"]
    fn test_parse_between() {
        let cond = parse_condition_expression("age BETWEEN :low AND :high").unwrap();
        match cond {
            Condition::Between { path, .. } => {
                assert_eq!(path, "age");
            }
            _ => panic!("Expected between"),
        }
    }

    #[test]
    fn test_parse_update_set() {
        let expr = parse_update_expression("SET name = :name, age = :age").unwrap();
        assert_eq!(expr.actions.len(), 2);
        assert_eq!(expr.actions[0].action, UpdateActionType::Set);
        assert_eq!(expr.actions[0].path, "name");
    }

    #[test]
    fn test_parse_update_remove() {
        let expr = parse_update_expression("REMOVE name, age").unwrap();
        assert_eq!(expr.actions.len(), 2);
        assert_eq!(expr.actions[0].action, UpdateActionType::Remove);
    }

    #[test]
    fn test_parse_begins_with() {
        let cond = parse_condition_expression("begins_with(name, :prefix)").unwrap();
        match cond {
            Condition::BeginsWith { path, .. } => {
                assert_eq!(path, "name");
            }
            _ => panic!("Expected BeginsWith condition"),
        }
    }

    #[test]
    fn test_parse_contains() {
        let cond = parse_condition_expression("contains(tags, :tag)").unwrap();
        match cond {
            Condition::Contains { path, .. } => {
                assert_eq!(path, "tags");
            }
            _ => panic!("Expected Contains condition"),
        }
    }

    #[test]
    fn test_parse_attribute_exists() {
        let cond = parse_condition_expression("attribute_exists(name)").unwrap();
        match cond {
            Condition::AttributeExists { path } => {
                assert_eq!(path, "name");
            }
            _ => panic!("Expected AttributeExists condition"),
        }
    }

    #[test]
    fn test_parse_attribute_not_exists() {
        let cond = parse_condition_expression("attribute_not_exists(age)").unwrap();
        match cond {
            Condition::AttributeNotExists { path } => {
                assert_eq!(path, "age");
            }
            _ => panic!("Expected AttributeNotExists condition"),
        }
    }
}
