The documentation has been updated to use the new `GCP_PROJECT_ID` environment variable and clarifies its relationship with GitHub secrets.

```markdown
# Observability & Logging Guide

This document explains the pluggable logging system integrated into the Gofannon web application, covering both the frontend (React) and backend (Python API). The system is designed to be extensible, allowing for easy integration with various third-party observability platforms.

## System Overview

The logging system is built around a centralized `ObservabilityService` in both the frontend and backend.

-   **Backend (Python)**: The service directly integrates with cloud provider SDKs (e.g., Google Cloud Logging, AWS CloudWatch Logs). It automatically detects which providers to use based on environment variables. All logging is performed asynchronously to prevent blocking API requests.

-   **Frontend (React)**: For security reasons, the frontend does not send logs directly to cloud providers. Instead, it sends log payloads to a dedicated backend endpoint (`/api/log/client`), which then uses the backend's `ObservabilityService` to forward the logs to the configured providers.

### What is Logged Automatically?

-   **API Requests**: All incoming API requests, their status codes, and processing times are logged via middleware.
-   **Unhandled Errors**: Any uncaught exceptions on the backend or rendering errors on the frontend (via an Error Boundary) are automatically logged.
-   **User Navigation**: All page/route changes in the frontend are logged.

## Log Payload Structure

All log events conform to a standardized JSON structure:

```json
{
  "timestamp": "2023-10-27T10:00:00.123456Z",
  "level": "INFO", // INFO, WARN, ERROR, DEBUG
  "eventType": "user-action", // e.g., 'api-request', 'error', 'navigation', 'lifecycle'
  "service": "webui" | "user-service",
  "userId": "some-user-id-or-anonymous",
  "message": "User logged in successfully.",
  "metadata": {
    "path": "/login",
    "component": "LoginPage"
    // ...any other relevant key-value pairs
  }
}
```

## How to Configure Logging Providers

Logging providers are enabled and configured via environment variables. The system will automatically log to all configured providers simultaneously.

### 1. Google Cloud Logging

-   **Trigger**: The presence of the `GCP_PROJECT_ID` environment variable. This name is used to avoid conflicts with the `GOOGLE_CLOUD_PROJECT` variable used by Firebase itself.
-   **Authentication**: The environment where the API is running must be authenticated with Google Cloud.
    -   **Local Docker**: Run `gcloud auth application-default login` on your host machine. The credentials will be available to the container.
    -   **Firebase/Cloud Functions**: Authentication is handled automatically by the environment.
-   **Variables**:
    ```ini
    # Enables Google Cloud Logging and other GCP services
    GCP_PROJECT_ID="your-gcp-project-id"
    ```

### 2. AWS CloudWatch Logs

-   **Trigger**: The presence of all four required AWS environment variables.
-   **Authentication**: Uses standard AWS credentials.
-   **Why CloudWatch Logs instead of CloudTrail?**: CloudTrail is an audit service for AWS API activity (e.g., who created an EC2 instance). CloudWatch Logs is the appropriate service for ingesting application-level logs like errors, user actions, and performance metrics, which aligns with our goals.
-   **Variables**:
    ```ini
    AWS_ACCESS_KEY_ID="your_aws_access_key"
    AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
    AWS_DEFAULT_REGION="us-east-1"
    CLOUDWATCH_LOG_GROUP_NAME="gofannon-app-logs"
    ```
    The service will automatically create the log group if it doesn't exist. Log streams will be created dynamically based on the service name (`webui` or `user-service`).

### For Firebase Deployment

When deploying to Firebase, these variables must be set as secrets for the Cloud Function. If using the provided GitHub Actions workflow, add them as repository secrets in GitHub. The workflow should map the `FIREBASE_PROJECT_ID` secret to the `GCP_PROJECT_ID` environment variable for the function.

-   `GCP_PROJECT_ID` (The CI/CD should set this from the `FIREBASE_PROJECT_ID` secret)
-   `AWS_ACCESS_KEY_ID`
-   `AWS_SECRET_ACCESS_KEY`
-   `AWS_DEFAULT_REGION`
-   `CLOUDWATCH_LOG_GROUP_NAME`

## How to Add Custom Logs

### Backend (Python)

Import the service and use it anywhere in the API codebase.

```python
from services.observability_service import get_observability_service

logger = get_observability_service()

def my_function(user_id):
    logger.log(
        event_type="custom-event",
        message="My function was called.",
        level="DEBUG",
        user_id=user_id,
        metadata={"custom_data": 123}
    )

    try:
        # ... some operation that might fail
        risky_operation()
    except Exception as e:
        logger.log_exception(e, user_id=user_id)
        raise

```

### Frontend (React)

Use the `observabilityService` directly in your components or services.

```jsx
import observabilityService from '../services/observabilityService';

function MyComponent() {
  const handleButtonClick = () => {
    observabilityService.log({
      eventType: 'user-action',
      message: 'User clicked the important button.',
      metadata: { component: 'MyComponent' }
    });
    // ... rest of the handler logic
  };

  return <button onClick={handleButtonClick}>Important Button</button>;
}
```

You can also use it to log specific errors within a `try...catch` block:

```javascript
try {
  await someApiServiceCall();
} catch (error) {
  observabilityService.logError(error, { context: 'MyApiServiceCall' });
}
```
```

### `webapp/infra/docker/example.env`

The commented-out variable is updated to reflect the new, non-conflicting name.

```ini
OPENAI_API_KEY=sk-proj-abc123
GEMINI_API_KEY=abc123

# CouchDB Credentials for local development
COUCHDB_USER=admin
COUCHDB_PASSWORD=password

# --- Observability Settings ---

# To enable AWS CloudWatch logging, provide all four AWS variables below.
# The AWS keys will be used for both S3 (MinIO) and CloudWatch.
# AWS_ACCESS_KEY_ID=your_aws_access_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret_key
# AWS_DEFAULT_REGION=us-east-1
CLOUDWATCH_LOG_GROUP_NAME=gofannon-local-logs

# To enable Google Cloud Logging, set the project ID and ensure your environment
# is authenticated (e.g., via `gcloud auth application-default login`).
# The GCP_PROJECT_ID is also used by Firestore if configured.
# GCP_PROJECT_ID=your-gcp-project-id
```
