# REST API Usage Examples

**Complete guide to using the Agentic Workflow REST API**

---

## Table of Contents

- [Authentication](#authentication)
- [Workflow Management](#workflow-management)
- [Workflow Execution](#workflow-execution)
- [Real-Time Monitoring](#real-time-monitoring)
- [Agent Management](#agent-management)
- [Error Handling](#error-handling)
- [Language-Specific Examples](#language-specific-examples)

---

## Authentication

### Get JWT Token

```bash
# Login with username and password
curl -X POST "https://api.agentic-workflow.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username" \
  -d "password=your_password"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Use API Key

```bash
# Most endpoints accept API keys
curl "https://api.agentic-workflow.com/api/v1/workflows" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Workflow Management

### List All Workflows

```bash
GET /api/v1/workflows

curl "https://api.agentic-workflow.com/api/v1/workflows" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "id": "wf_20231111_142530",
    "name": "Code Review Pipeline",
    "description": "Automated code review workflow",
    "node_count": 3,
    "created_at": "2023-11-11T14:25:30Z",
    "updated_at": "2023-11-11T14:25:30Z"
  }
]
```

### Create Visual Workflow

```bash
POST /api/v1/workflows/visual/create

curl -X POST "https://api.agentic-workflow.com/api/v1/workflows/visual/create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-workflow-1",
    "name": "Full Development Pipeline",
    "description": "Plan, code, test, and deploy",
    "nodes": [
      {
        "id": "node_1",
        "type": "agent",
        "position": {"x": 250, "y": 100},
        "data": {
          "agent_type": "planning",
          "label": "Plan Tasks",
          "config": {
            "reasoning_pattern": "chain_of_thought"
          }
        }
      },
      {
        "id": "node_2",
        "type": "agent",
        "position": {"x": 250, "y": 250},
        "data": {
          "agent_type": "code_generation",
          "label": "Generate Code",
          "config": {
            "language": "python",
            "framework": "fastapi"
          }
        }
      },
      {
        "id": "node_3",
        "type": "agent",
        "position": {"x": 250, "y": 400},
        "data": {
          "agent_type": "testing",
          "label": "Run Tests",
          "config": {
            "coverage_threshold": 80
          }
        }
      }
    ],
    "edges": [
      {
        "id": "edge_1",
        "source": "node_1",
        "target": "node_2"
      },
      {
        "id": "edge_2",
        "source": "node_2",
        "target": "node_3"
      }
    ],
    "metadata": {
      "created_by": "user123",
      "tags": ["development", "automation"]
    }
  }'
```

**Response:**
```json
{
  "workflow_id": "wf_20231111_143000",
  "name": "Full Development Pipeline",
  "created_at": "2023-11-11T14:30:00Z",
  "node_count": 3,
  "message": "Workflow created successfully"
}
```

### Get Workflow Details

```bash
GET /api/v1/workflows/{workflow_id}

curl "https://api.agentic-workflow.com/api/v1/workflows/wf_20231111_143000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "id": "wf_20231111_143000",
  "name": "Full Development Pipeline",
  "description": "Plan, code, test, and deploy",
  "nodes": [...],
  "edges": [...],
  "metadata": {...},
  "created_at": "2023-11-11T14:30:00Z",
  "updated_at": "2023-11-11T14:30:00Z"
}
```

### Update Workflow

```bash
PUT /api/v1/workflows/{workflow_id}

curl -X PUT "https://api.agentic-workflow.com/api/v1/workflows/wf_20231111_143000" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Pipeline",
    "description": "Updated description",
    "nodes": [...],
    "edges": [...]
  }'
```

### Delete Workflow

```bash
DELETE /api/v1/workflows/{workflow_id}

curl -X DELETE "https://api.agentic-workflow.com/api/v1/workflows/wf_20231111_143000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Workflow Execution

### Execute Workflow

```bash
POST /api/v1/workflows/{workflow_id}/execute

curl -X POST "https://api.agentic-workflow.com/api/v1/workflows/wf_20231111_143000/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "project_name": "my-api",
      "framework": "fastapi",
      "include_tests": true
    }
  }'
```

**Response:**
```json
{
  "execution_id": "exec_20231111_143500",
  "workflow_id": "wf_20231111_143000",
  "status": "running",
  "created_at": "2023-11-11T14:35:00Z",
  "message": "Workflow execution started"
}
```

### Check Execution Status

```bash
GET /api/v1/workflows/executions/{execution_id}

curl "https://api.agentic-workflow.com/api/v1/workflows/executions/exec_20231111_143500" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (Running):**
```json
{
  "execution_id": "exec_20231111_143500",
  "workflow_id": "wf_20231111_143000",
  "status": "running",
  "started_at": "2023-11-11T14:35:00Z",
  "completed_at": null,
  "result": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "execution_id": "exec_20231111_143500",
  "workflow_id": "wf_20231111_143000",
  "status": "completed",
  "started_at": "2023-11-11T14:35:00Z",
  "completed_at": "2023-11-11T14:37:30Z",
  "result": {
    "steps_completed": 3,
    "workflow_name": "Full Development Pipeline",
    "output": {
      "code_generated": true,
      "tests_passed": 42,
      "coverage": 85.5
    }
  },
  "error": null
}
```

### List Workflow Executions

```bash
GET /api/v1/workflows/{workflow_id}/executions

curl "https://api.agentic-workflow.com/api/v1/workflows/wf_20231111_143000/executions" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Real-Time Monitoring

### WebSocket Connection (JavaScript)

```javascript
// Connect to execution WebSocket
const ws = new WebSocket(
  'wss://api.agentic-workflow.com/api/v1/ws/executions/exec_20231111_143500',
  {
    headers: {
      'Authorization': 'Bearer YOUR_TOKEN'
    }
  }
);

ws.onopen = () => {
  console.log('Connected to workflow execution');
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Status:', update.status);
  console.log('Progress:', update.progress);
  console.log('Current Step:', update.current_step);
  console.log('Message:', update.message);
  
  if (update.status === 'completed') {
    console.log('Result:', update.result);
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed');
};
```

### WebSocket Messages

**Progress Update:**
```json
{
  "type": "progress",
  "execution_id": "exec_20231111_143500",
  "status": "running",
  "progress": 33,
  "current_step": "code_generation",
  "message": "Generating code based on requirements",
  "timestamp": "2023-11-11T14:36:00Z"
}
```

**Step Completed:**
```json
{
  "type": "step_completed",
  "execution_id": "exec_20231111_143500",
  "step_name": "code_generation",
  "step_result": {
    "files_created": 5,
    "lines_of_code": 342
  },
  "timestamp": "2023-11-11T14:36:30Z"
}
```

**Execution Completed:**
```json
{
  "type": "completed",
  "execution_id": "exec_20231111_143500",
  "status": "completed",
  "result": {
    "steps_completed": 3,
    "total_duration_seconds": 150,
    "output": {...}
  },
  "timestamp": "2023-11-11T14:37:30Z"
}
```

---

## Agent Management

### List Available Agents

```bash
GET /api/v1/agents

curl "https://api.agentic-workflow.com/api/v1/agents" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "id": "planning",
    "name": "Planning Agent",
    "description": "Strategic task planning and decomposition",
    "capabilities": [
      "task_decomposition",
      "estimation",
      "architecture_planning"
    ],
    "parameters": {
      "reasoning_pattern": {
        "type": "string",
        "enum": ["chain_of_thought", "react", "raise"],
        "default": "chain_of_thought"
      }
    }
  },
  {
    "id": "code_generation",
    "name": "Code Generation Agent",
    "description": "Generate code from requirements",
    "capabilities": [
      "code_generation",
      "refactoring",
      "documentation"
    ],
    "parameters": {
      "language": {
        "type": "string",
        "enum": ["python", "javascript", "java", "go"],
        "required": true
      },
      "framework": {
        "type": "string",
        "optional": true
      }
    }
  }
]
```

### Get Agent Capabilities

```bash
GET /api/v1/agents/{agent_id}/capabilities

curl "https://api.agentic-workflow.com/api/v1/agents/code_generation/capabilities" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Invalid authentication credentials"
}
```

**404 Not Found:**
```json
{
  "detail": "Workflow wf_invalid not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "nodes"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error",
  "error_id": "err_20231111_143500"
}
```

### Retry Logic Example

```bash
#!/bin/bash

# Function to execute workflow with retry
execute_workflow() {
  local workflow_id=$1
  local max_retries=3
  local retry_count=0
  
  while [ $retry_count -lt $max_retries ]; do
    response=$(curl -s -w "\n%{http_code}" \
      -X POST "https://api.agentic-workflow.com/api/v1/workflows/${workflow_id}/execute" \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"parameters": {}}')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" -eq 200 ]; then
      echo "Success: $body"
      return 0
    elif [ "$http_code" -eq 429 ]; then
      echo "Rate limited, retrying in 5 seconds..."
      sleep 5
      ((retry_count++))
    else
      echo "Error ($http_code): $body"
      return 1
    fi
  done
  
  echo "Max retries reached"
  return 1
}

execute_workflow "wf_20231111_143000"
```

---

## Language-Specific Examples

### Python

```python
import requests
import json

class AgenticWorkflowClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_workflow(self, workflow_definition):
        """Create a new workflow."""
        url = f'{self.base_url}/api/v1/workflows/visual/create'
        response = requests.post(url, headers=self.headers, json=workflow_definition)
        response.raise_for_status()
        return response.json()
    
    def execute_workflow(self, workflow_id, parameters=None):
        """Execute a workflow."""
        url = f'{self.base_url}/api/v1/workflows/{workflow_id}/execute'
        payload = {'parameters': parameters or {}}
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_execution_status(self, execution_id):
        """Get execution status."""
        url = f'{self.base_url}/api/v1/workflows/executions/{execution_id}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, execution_id, poll_interval=5):
        """Wait for execution to complete."""
        import time
        
        while True:
            status = self.get_execution_status(execution_id)
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            print(f"Status: {status['status']}, waiting...")
            time.sleep(poll_interval)

# Usage
client = AgenticWorkflowClient(
    base_url='https://api.agentic-workflow.com',
    api_key='your_api_key'
)

# Create workflow
workflow_def = {
    'name': 'My Workflow',
    'nodes': [...],
    'edges': [...]
}
workflow = client.create_workflow(workflow_def)
print(f"Created workflow: {workflow['workflow_id']}")

# Execute
execution = client.execute_workflow(workflow['workflow_id'], {'param': 'value'})
print(f"Execution started: {execution['execution_id']}")

# Wait for completion
result = client.wait_for_completion(execution['execution_id'])
print(f"Result: {result['result']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

class AgenticWorkflowClient {
  constructor(baseURL, apiKey) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });
  }
  
  async createWorkflow(workflowDefinition) {
    const response = await this.client.post(
      '/api/v1/workflows/visual/create',
      workflowDefinition
    );
    return response.data;
  }
  
  async executeWorkflow(workflowId, parameters = {}) {
    const response = await this.client.post(
      `/api/v1/workflows/${workflowId}/execute`,
      { parameters }
    );
    return response.data;
  }
  
  async getExecutionStatus(executionId) {
    const response = await this.client.get(
      `/api/v1/workflows/executions/${executionId}`
    );
    return response.data;
  }
  
  async waitForCompletion(executionId, pollInterval = 5000) {
    while (true) {
      const status = await this.getExecutionStatus(executionId);
      
      if (['completed', 'failed'].includes(status.status)) {
        return status;
      }
      
      console.log(`Status: ${status.status}, waiting...`);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }
}

// Usage
(async () => {
  const client = new AgenticWorkflowClient(
    'https://api.agentic-workflow.com',
    'your_api_key'
  );
  
  // Create workflow
  const workflowDef = {
    name: 'My Workflow',
    nodes: [...],
    edges: [...]
  };
  const workflow = await client.createWorkflow(workflowDef);
  console.log(`Created workflow: ${workflow.workflow_id}`);
  
  // Execute
  const execution = await client.executeWorkflow(
    workflow.workflow_id,
    { param: 'value' }
  );
  console.log(`Execution started: ${execution.execution_id}`);
  
  // Wait for completion
  const result = await client.waitForCompletion(execution.execution_id);
  console.log('Result:', result.result);
})();
```

### cURL Script

```bash
#!/bin/bash

# Configuration
API_URL="https://api.agentic-workflow.com"
API_KEY="your_api_key"

# Create workflow
WORKFLOW_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/workflows/visual/create" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Workflow",
    "nodes": [...],
    "edges": [...]
  }')

WORKFLOW_ID=$(echo "$WORKFLOW_RESPONSE" | jq -r '.workflow_id')
echo "Created workflow: $WORKFLOW_ID"

# Execute workflow
EXEC_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/workflows/${WORKFLOW_ID}/execute" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {}}')

EXEC_ID=$(echo "$EXEC_RESPONSE" | jq -r '.execution_id')
echo "Execution started: $EXEC_ID"

# Poll for completion
while true; do
  STATUS_RESPONSE=$(curl -s "${API_URL}/api/v1/workflows/executions/${EXEC_ID}" \
    -H "Authorization: Bearer ${API_KEY}")
  
  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
    echo "Result:"
    echo "$STATUS_RESPONSE" | jq '.result'
    break
  fi
  
  sleep 5
done
```

---

## Additional Resources

- [OpenAPI Documentation](https://api.agentic-workflow.com/docs)
- [Customer Getting Started Guide](CUSTOMER_GETTING_STARTED.md)
- [WebSocket Examples](WEBSOCKET_EXAMPLES.md)
- [Error Codes Reference](ERROR_CODES.md)

---

*Last Updated: November 11, 2025*
