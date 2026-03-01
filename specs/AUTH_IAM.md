# AWS Authentication and IAM for DynamoDB API Compatibility

This document covers AWS authentication mechanisms required for DynamoDB API compatibility, including Signature Version 4, credential sources, DynamoDB Local auth behavior, and IAM policy formats.

---

## 1. AWS Signature Version 4

AWS Signature Version 4 (SigV4) is the protocol for authenticating AWS API requests. All AWS SDKs use SigV4 to sign requests to DynamoDB.

### 1.1 Authorization Header Format

```
Authorization: AWS4-HMAC-SHA256
Credential=<access-key-id>/<date>/<region>/<service>/aws4_request,
SignedHeaders=<semicolon-separated-headers>,
Signature=<hex-signature>
```

**Example:**
```
Authorization: AWS4-HMAC-SHA256 
Credential=AKIAIOSFODNN7EXAMPLE/20240101/us-east-1/dynamodb/aws4_request, 
SignedHeaders=host;x-amz-date;x-amz-target, 
Signature=fe5f80f77d5fa3beca038a248ff027d0445342fe2855ddc963176630326f1024
```

### 1.2 Required Headers

| Header | Description |
|--------|-------------|
| `Authorization` | The complete signature string |
| `X-Amz-Date` | UTC timestamp in ISO 8601 format (YYYYMMDD'T'HHMMSS'Z') |
| `Host` | The target host (e.g., `dynamodb.us-east-1.amazonaws.com`) |
| `X-Amz-Target` | DynamoDB API target (e.g., `DynamoDB_20120810.GetItem`) |
| `X-Amz-Security-Token` | Required when using temporary credentials (session token) |
| `X-Amz-Content-SHA256` | SHA256 hash of the request payload (or `UNSIGNED-PAYLOAD`) |

### 1.3 Signature Calculation Process

The signature is calculated in three stages:

#### Stage 1: Create a Canonical Request

```
CanonicalRequest =
  HTTPMethod + '\n' +
  CanonicalURI + '\n' +
  CanonicalQueryString + '\n' +
  CanonicalHeaders + '\n' +
  SignedHeaders + '\n' +
  HexEncode(Hash(RequestPayload))
```

**For DynamoDB:**
- `HTTPMethod`: Always `POST` for DynamoDB API
- `CanonicalURI`: `/` (root path)
- `CanonicalQueryString`: Empty string for DynamoDB
- `CanonicalHeaders`: Sorted, lowercase headers with trimmed values
- `SignedHeaders`: Semicolon-separated list of header names (lowercase)
- `RequestPayload`: The JSON request body

**Example Canonical Request:**
```
POST
/

host:dynamodb.us-east-1.amazonaws.com
x-amz-content-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
x-amz-date:20240101T000000Z
x-amz-target:DynamoDB_20120810.GetItem

host;x-amz-content-sha256;x-amz-date;x-amz-target
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

#### Stage 2: Create String to Sign

```
StringToSign =
  "AWS4-HMAC-SHA256" + '\n' +
  Timestamp + '\n' +
  Scope + '\n' +
  HexEncode(Hash(CanonicalRequest))
```

Where:
- `Timestamp`: Same as `X-Amz-Date` (YYYYMMDD'T'HHMMSS'Z')
- `Scope`: `<date>/<region>/<service>/aws4_request`
  - `date`: YYYYMMDD format
  - `region`: AWS region (e.g., `us-east-1`)
  - `service`: `dynamodb` for DynamoDB

**Example String to Sign:**
```
AWS4-HMAC-SHA256
20240101T000000Z
20240101/us-east-1/dynamodb/aws4_request
7344ae5b7ee6c3e7e6b0fe0640412a37625d1fbfff95c48bbb2dc43964946972
```

#### Stage 3: Calculate Signature

```
DateKey = HMAC-SHA256("AWS4" + SecretAccessKey, Date)
DateRegionKey = HMAC-SHA256(DateKey, Region)
DateRegionServiceKey = HMAC-SHA256(DateRegionKey, Service)
SigningKey = HMAC-SHA256(DateRegionServiceKey, "aws4_request")
Signature = HMAC-SHA256(SigningKey, StringToSign)
```

**Note:** The `SigningKey` is valid for the specific date, region, and service (up to 7 days).

### 1.4 Empty Payload Hash

For DynamoDB, the empty string hash is:
```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

This is the SHA256 hash of an empty string, used when there is no request body (rare for DynamoDB since most requests have JSON payloads).

### 1.5 AWS Signature Version 4A (SigV4A)

An extension that supports multi-region signatures:
- Uses `AWS4-ECDSA-P256-SHA256` algorithm
- Does not include region-specific information in the signature
- Required for some global AWS services

---

## 2. Credential Sources

AWS SDKs support multiple credential sources with the following precedence:

### 2.1 Environment Variables

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | The access key ID |
| `AWS_SECRET_ACCESS_KEY` | The secret access key |
| `AWS_SESSION_TOKEN` | Session token (for temporary credentials) |
| `AWS_DEFAULT_REGION` | Default AWS region |

**Example:**
```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_SESSION_TOKEN=IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3VERYLONGSTRINGEXAMPLE
export AWS_DEFAULT_REGION=us-east-1
```

### 2.2 AWS Credentials File

Location:
- Linux/macOS: `~/.aws/credentials`
- Windows: `%UserProfile%\.aws\credentials`

**Format:**
```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
aws_session_token = IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3VERYLONGSTRINGEXAMPLE

[profile production]
aws_access_key_id = AKIAI44QH8DHBEXAMPLE
aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
```

**Notes:**
- Do NOT use the word `profile` in the credentials file section names
- The `[default]` profile is used when no profile is specified
- `aws_session_token` is only needed for temporary credentials

### 2.3 AWS Config File

Location:
- Linux/macOS: `~/.aws/config`
- Windows: `%UserProfile%\.aws\config`

**Format:**
```ini
[default]
region = us-east-1
output = json

[profile production]
region = us-west-2
output = json
```

**Note:** In the config file, use `profile` prefix for named profiles: `[profile production]`

### 2.4 Profile Selection

Select a profile using:

**Environment Variable:**
```bash
export AWS_PROFILE=production
```

**AWS CLI:**
```bash
aws dynamodb list-tables --profile production
```

**SDK Code (examples):**
```python
# Python (boto3)
import boto3
session = boto3.Session(profile_name='production')
client = session.client('dynamodb')
```

```javascript
// JavaScript (AWS SDK v3)
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const client = new DynamoDBClient({ profile: 'production' });
```

```java
// Java
DynamoDbClient client = DynamoDbClient.builder()
    .credentialsProvider(ProfileCredentialsProvider.create("production"))
    .build();
```

### 2.5 IAM Instance Metadata Service (IMDS)

EC2 instances with IAM roles attached can retrieve temporary credentials from the instance metadata service.

#### IMDSv1 (Legacy)

```bash
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>
```

**Response:**
```json
{
  "Code": "Success",
  "LastUpdated": "2024-01-01T00:00:00Z",
  "Type": "AWS-HMAC",
  "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "Token": "IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3JpZ2luX2IQoJb3VERYLONGSTRINGEXAMPLE",
  "Expiration": "2024-01-01T06:00:00Z"
}
```

#### IMDSv2 (Recommended - Session-Based)

More secure, requires a session token:

```bash
# Step 1: Get session token (PUT request with custom header)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Step 2: Use token in metadata requests
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>
```

**Key Differences:**
| Feature | IMDSv1 | IMDSv2 |
|---------|--------|--------|
| Authentication | None | Session token required |
| Token acquisition | N/A | PUT request with custom header |
| SSRF resistance | Vulnerable | Resistant (requires PUT + header) |
| Hop limit | N/A | Default 1 (configurable) |

**IMDSv2 is becoming the default:**
- New EC2 instance types (mid-2024+) use IMDSv2 only by default
- AWS recommends migrating to IMDSv2
- IMDSv1 can be disabled at the instance or account level

### 2.6 STS Temporary Credentials

AWS Security Token Service (STS) provides temporary credentials:

#### AssumeRole
```python
import boto3

sts = boto3.client('sts')
response = sts.assume_role(
    RoleArn='arn:aws:iam::123456789012:role/MyRole',
    RoleSessionName='MySession',
    DurationSeconds=3600  # 1 hour, max 12 hours for normal roles
)

credentials = response['Credentials']
# credentials['AccessKeyId']
# credentials['SecretAccessKey']  
# credentials['SessionToken']
# credentials['Expiration']
```

#### AssumeRoleWithWebIdentity (OIDC)
For federated identities (e.g., GitHub Actions, EKS):
```python
response = sts.assume_role_with_web_identity(
    RoleArn='arn:aws:iam::123456789012:role/MyRole',
    RoleSessionName='GitHubActions',
    WebIdentityToken=token_from_idp
)
```

#### GetSessionToken
For MFA-protected access:
```python
response = sts.get_session_token(
    DurationSeconds=129600,  # Max 36 hours
    SerialNumber='arn:aws:iam::123456789012:mfa/user',
    TokenCode='123456'  # MFA code
)
```

### 2.7 Credential Precedence

AWS SDKs check credentials in this order:

1. Explicitly passed to client constructor
2. Environment variables (`AWS_ACCESS_KEY_ID`, etc.)
3. Web identity token (for EKS/ECS)
4. Shared credentials file (`~/.aws/credentials`)
5. AWS config file (`~/.aws/config`)
6. Container credentials (ECS task role)
7. EC2 instance metadata (IAM instance profile)
8. Default provider chain fails if none found

---

## 3. DynamoDB Local Authentication

[DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html) is a downloadable version of DynamoDB for local development and testing.

### 3.1 Does DynamoDB Local Validate Signatures?

**No.** DynamoDB Local does NOT validate AWS signatures. It accepts any credentials.

### 3.2 What Credentials Does DynamoDB Local Accept?

DynamoDB Local works with **any non-null credentials**:

```python
# Python - works with any credentials
import boto3

client = boto3.client(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1',
    aws_access_key_id='dummy',        # Any non-empty value
    aws_secret_access_key='dummy'     # Any non-empty value
)
```

```java
// Java - works with dummy credentials
DynamoDbClient client = DynamoDbClient.builder()
    .endpointOverride(URI.create("http://localhost:8000"))
    .region(Region.US_EAST_1)
    .credentialsProvider(StaticCredentialsProvider.create(
        AwsBasicCredentials.create("dummy", "dummy")
    ))
    .build();
```

### 3.3 DynamoDB Local Configuration

**Default port:** 8000

**Startup options:**
```bash
# Basic start
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar

# Custom port
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -port 8001

# In-memory mode (data lost on restart)
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -inMemory

# Shared database (persist data)
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb

# With data path
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -dbPath ./data
```

### 3.4 Docker Support

```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

### 3.5 Implications for SDK Compatibility

When implementing a DynamoDB-compatible API:

1. **For production:** Must implement full SigV4 validation
2. **For local development:** Can accept any credentials (like DynamoDB Local)
3. **Recommendation:** Support a "local mode" flag that bypasses signature validation

---

## 4. IAM Policy Format for DynamoDB

IAM policies control access to DynamoDB resources using JSON documents.

### 4.1 Policy Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "StatementIdentifier",
      "Effect": "Allow|Deny",
      "Action": [
        "dynamodb:ActionName"
      ],
      "Resource": [
        "arn:aws:dynamodb:<region>:<account-id>:table/<table-name>"
      ],
      "Condition": {
        "ConditionOperator": {
          "ConditionKey": "ConditionValue"
        }
      }
    }
  ]
}
```

### 4.2 Common DynamoDB Actions

#### Data Operations
| Action | Description | Access Level |
|--------|-------------|--------------|
| `dynamodb:GetItem` | Read a single item by primary key | Read |
| `dynamodb:BatchGetItem` | Read multiple items from one or more tables | Read |
| `dynamodb:PutItem` | Create or replace an item | Write |
| `dynamodb:UpdateItem` | Modify an existing item | Write |
| `dynamodb:DeleteItem` | Delete a single item | Write |
| `dynamodb:BatchWriteItem` | Write or delete multiple items | Write |
| `dynamodb:Query` | Query items using partition key and optional sort key | Read |
| `dynamodb:Scan` | Read all items in a table or index | Read |
| `dynamodb:ConditionCheckItem` | Check conditions without modifying data | Read |

#### PartiQL Operations
| Action | Description |
|--------|-------------|
| `dynamodb:PartiQLSelect` | Execute SELECT statements |
| `dynamodb:PartiQLInsert` | Execute INSERT statements |
| `dynamodb:PartiQLUpdate` | Execute UPDATE statements |
| `dynamodb:PartiQLDelete` | Execute DELETE statements |

#### Table Management
| Action | Description |
|--------|-------------|
| `dynamodb:CreateTable` | Create a new table |
| `dynamodb:DeleteTable` | Delete a table |
| `dynamodb:UpdateTable` | Modify table settings |
| `dynamodb:DescribeTable` | Get table information |
| `dynamodb:ListTables` | List all tables |

#### Stream Operations
| Action | Description |
|--------|-------------|
| `dynamodb:DescribeStream` | Get stream information |
| `dynamodb:GetRecords` | Read records from a stream |
| `dynamodb:GetShardIterator` | Get iterator for reading stream |
| `dynamodb:ListStreams` | List all streams |

#### Backup Operations
| Action | Description |
|--------|-------------|
| `dynamodb:CreateBackup` | Create a table backup |
| `dynamodb:RestoreTableFromBackup` | Restore from backup |
| `dynamodb:DescribeBackup` | Get backup information |
| `dynamodb:ListBackups` | List backups |
| `dynamodb:DeleteBackup` | Delete a backup |

### 4.3 Resource ARNs for DynamoDB

**Table:**
```
arn:aws:dynamodb:<region>:<account-id>:table/<table-name>
```
Example: `arn:aws:dynamodb:us-east-1:123456789012:table/Users`

**Index (GSI or LSI):**
```
arn:aws:dynamodb:<region>:<account-id>:table/<table-name>/index/<index-name>
```
Example: `arn:aws:dynamodb:us-east-1:123456789012:table/Users/index/EmailIndex`

**Stream:**
```
arn:aws:dynamodb:<region>:<account-id>:table/<table-name>/stream/<stream-label>
```
Example: `arn:aws:dynamodb:us-east-1:123456789012:table/Users/stream/2024-01-01T00:00:00.000`

**Backup:**
```
arn:aws:dynamodb:<region>:<account-id>:table/<table-name>/backup/<backup-name>
```
Example: `arn:aws:dynamodb:us-east-1:123456789012:table/Users/backup/backup-2024-01-01`

**Global Table:**
```
arn:aws:dynamodb::<account-id>:global-table/<global-table-name>
```

**All tables (wildcard):**
```
arn:aws:dynamodb:<region>:<account-id>:table/*
```

### 4.4 Condition Keys for DynamoDB

DynamoDB supports fine-grained access control using condition keys:

#### DynamoDB-Specific Condition Keys

| Condition Key | Description |
|---------------|-------------|
| `dynamodb:LeadingKeys` | The partition key value being accessed |
| `dynamodb:Attributes` | List of top-level attributes accessed |
| `dynamodb:Select` | The Select parameter value (ALL_ATTRIBUTES, SPECIFIC_ATTRIBUTES, etc.) |
| `dynamodb:ReturnValues` | The ReturnValues parameter (NONE, ALL_OLD, UPDATED_OLD, ALL_NEW, UPDATED_NEW) |
| `dynamodb:ReturnConsumedCapacity` | The ReturnConsumedCapacity parameter |
| `dynamodb:EnclosingOperation` | The enclosing operation (for TransactGetItems, TransactWriteItems) |
| `dynamodb:FullTableScan` | Whether a full table scan is being performed |

#### AWS Global Condition Keys

| Condition Key | Description |
|---------------|-------------|
| `aws:RequestTag/${TagKey}` | Tags in the request |
| `aws:ResourceTag/${TagKey}` | Tags on the resource |
| `aws:TagKeys` | List of tag keys in the request |
| `aws:SourceIp` | IP address of the requester |
| `aws:UserAgent` | User agent string |
| `aws:CurrentTime` | Current time |
| `aws:PrincipalType` | Type of principal (Account, User, FederatedUser, etc.) |
| `aws:userid` | User ID of the principal |
| `aws:username` | Username of the principal |

### 4.5 Policy Examples

#### Basic Read-Only Access
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/Users",
        "arn:aws:dynamodb:us-east-1:123456789012:table/Users/index/*"
      ]
    }
  ]
}
```

#### Read-Write Access
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadWriteAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/Orders",
        "arn:aws:dynamodb:us-east-1:123456789012:table/Orders/index/*"
      ]
    }
  ]
}
```

#### Item-Level Access Control (LeadingKeys)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AccessOwnItemsOnly",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/UserData",
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:LeadingKeys": ["${aws:userid}"]
        }
      }
    }
  ]
}
```

#### Attribute-Level Access Control
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RestrictAttributes",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/Employees",
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:Attributes": [
            "EmployeeId",
            "Name",
            "Department",
            "Title"
          ]
        },
        "StringEqualsIfExists": {
          "dynamodb:Select": "SPECIFIC_ATTRIBUTES"
        }
      }
    }
  ]
}
```

#### Multi-Table Access with Different Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadWriteOrders",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/Orders",
        "arn:aws:dynamodb:us-east-1:123456789012:table/Orders/index/*"
      ]
    },
    {
      "Sid": "ReadOnlyUsers",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/Users",
        "arn:aws:dynamodb:us-east-1:123456789012:table/Users/index/*"
      ]
    },
    {
      "Sid": "WriteOnlyAudit",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/AuditLog"
    }
  ]
}
```

#### DynamoDB Streams Access
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "StreamAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/Orders/stream/*"
    }
  ]
}
```

#### Prevent Table Deletion
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowItemOperations",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/*"
    },
    {
      "Sid": "DenyTableDeletion",
      "Effect": "Deny",
      "Action": ["dynamodb:DeleteTable"],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/*"
    }
  ]
}
```

### 4.6 Important Notes for Implementation

1. **Scan Restrictions:** When using `dynamodb:LeadingKeys`, do NOT include `Scan` in allowed actions because Scan returns all items regardless of partition key.

2. **Key Attributes:** When using `dynamodb:Attributes`, you MUST specify all primary key and index key attributes in the allowed list.

3. **Select Parameter:** Use `StringEqualsIfExists` with `dynamodb:Select` to prevent users from requesting all attributes when attribute restrictions are in place.

4. **ReturnValues:** Restrict `dynamodb:ReturnValues` to prevent write operations from returning all attributes.

5. **ForAllValues:** The `ForAllValues` modifier is required when using `dynamodb:LeadingKeys` because the key name is plural.

---

## 5. Implementation Recommendations

For a DynamoDB-compatible API implementation:

### 5.1 Authentication Modes

1. **Production Mode:**
   - Full AWS SigV4 validation
   - Credential source configuration (env, file, IMDS, STS)
   - IAM policy evaluation
   - Clock skew tolerance (±5 minutes typical)

2. **Development/Local Mode:**
   - Accept any credentials (like DynamoDB Local)
   - Optional signature validation
   - Fixed/mock identity

### 5.2 Required Components

| Component | Description |
|-----------|-------------|
| Signature Parser | Parse Authorization header |
| Credential Provider | Support multiple credential sources |
| Signing Key Calculator | Derive signing key from secret |
| Signature Verifier | Calculate and compare signatures |
| Timestamp Validator | Check X-Amz-Date for freshness |
| IAM Policy Engine | Evaluate policies for authorization |

### 5.3 Testing Considerations

- Use official AWS SDK test vectors for signature verification
- Test with various credential sources
- Verify clock skew handling
- Test with temporary credentials (session tokens)
- Validate against DynamoDB Local behavior

---

## 6. References

- [AWS Signature Version 4 Signing Process](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)
- [DynamoDB API Reference](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/)
- [DynamoDB Local Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html)
- [Actions, Resources, and Condition Keys for DynamoDB](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazondynamodb.html)
- [Using IAM Policy Conditions for Fine-Grained Access Control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)
- [AWS CLI Configuration and Credential Files](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- [EC2 Instance Metadata Service (IMDSv2)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-security-credentials.html)
