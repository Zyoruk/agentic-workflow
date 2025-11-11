# Getting Started with Agentic Workflow System

**For Business Users, Product Managers, and API Consumers**

---

## What is Agentic Workflow?

Agentic Workflow is an **AI-powered automation platform** that handles complex software development tasks through intelligent agents. Think of it as having a team of AI developers working together on your tasks.

### What Can It Do?

- 🎯 **Automate Development Tasks**: Code generation, testing, review, CI/CD
- 🤖 **Multi-Agent Collaboration**: AI agents work together intelligently
- 🔄 **Visual Workflow Builder**: Create workflows without writing code
- ⚡ **Real-time Execution**: Watch your workflows execute live
- 📊 **Full History & Analytics**: Track all executions and results

---

## Quick Start: 3 Ways to Use Agentic Workflow

### Option 1: Visual Workflow Builder (Recommended for Beginners)

**Best for**: Non-technical users, quick prototyping

1. **Access the Visual Builder**
   ```
   https://your-agentic-instance.com/builder
   ```

2. **Create Your First Workflow**
   - Drag "Planning Agent" to canvas
   - Connect to "Code Generation Agent"
   - Connect to "Testing Agent"
   - Configure each agent's parameters
   - Click "Save Workflow"

3. **Execute**
   - Click "Execute" button
   - Watch real-time progress
   - Download results when complete

### Option 2: Single REST API Call (Recommended for Developers)

**Best for**: Developers, automated systems, integrations

Execute a simple workflow with one API call:

```bash
# Create and execute a workflow
curl -X POST "https://your-instance.com/api/v1/workflows/execute" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "Code Review Task",
      "steps": [
        {
          "agent": "planning",
          "parameters": {
            "objective": "Review pull request #123"
          }
        },
        {
          "agent": "code_review",
          "parameters": {
            "pr_number": 123,
            "repository": "myorg/myrepo"
          }
        }
      ]
    }
  }'
```

**Response:**
```json
{
  "execution_id": "exec_20231111_142530",
  "workflow_id": "wf_123",
  "status": "running",
  "created_at": "2023-11-11T14:25:30Z",
  "websocket_url": "wss://your-instance.com/api/v1/ws/executions/exec_20231111_142530"
}
```

### Option 3: Visual Builder API (For Advanced Users)

**Best for**: Creating reusable workflow templates via API

```bash
# Step 1: Create visual workflow
curl -X POST "https://your-instance.com/api/v1/workflows/visual/create" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-workflow-1",
    "name": "Code Review Pipeline",
    "description": "Automated code review workflow",
    "nodes": [
      {
        "id": "node_1",
        "type": "agent",
        "position": {"x": 250, "y": 100},
        "data": {
          "agent_type": "planning",
          "label": "Plan Review",
          "config": {}
        }
      },
      {
        "id": "node_2",
        "type": "agent",
        "position": {"x": 250, "y": 250},
        "data": {
          "agent_type": "code_review",
          "label": "Review Code",
          "config": {}
        }
      }
    ],
    "edges": [
      {
        "id": "edge_1",
        "source": "node_1",
        "target": "node_2"
      }
    ]
  }'

# Step 2: Execute the workflow
curl -X POST "https://your-instance.com/api/v1/workflows/{workflow_id}/execute" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "pr_number": 123,
      "repository": "myorg/myrepo"
    }
  }'
```

---

## Authentication

All API calls require authentication. You have two options:

### API Keys (Recommended)

```bash
# Include in header
Authorization: Bearer YOUR_API_KEY
```

### JWT Tokens (For User Sessions)

```bash
# Step 1: Login to get token
curl -X POST "https://your-instance.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# Response includes access_token
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}

# Step 2: Use token in requests
curl -X GET "https://your-instance.com/api/v1/workflows" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## Common Use Cases

### 1. Code Review Automation

**Scenario**: Automatically review pull requests

```bash
POST /api/v1/workflows/execute
{
  "workflow": {
    "steps": [
      {"agent": "code_review", "parameters": {"pr_id": 123}}
    ]
  }
}
```

### 2. Full Development Pipeline

**Scenario**: Generate code, write tests, run CI/CD

```bash
POST /api/v1/workflows/visual/create
# Create workflow with:
# - Planning Agent
# - Code Generation Agent
# - Testing Agent
# - CI/CD Agent
# Then execute it
```

### 3. Requirement Analysis

**Scenario**: Analyze and break down requirements

```bash
POST /api/v1/workflows/execute
{
  "workflow": {
    "steps": [
      {
        "agent": "requirement_engineering",
        "parameters": {
          "requirements_doc": "path/to/requirements.md"
        }
      }
    ]
  }
}
```

---

## Monitoring and Results

### Check Execution Status

```bash
GET /api/v1/workflows/executions/{execution_id}

# Response:
{
  "execution_id": "exec_123",
  "status": "completed",
  "result": {
    "steps_completed": 3,
    "output": {...}
  }
}
```

### Real-time Updates via WebSocket

```javascript
// JavaScript example
const ws = new WebSocket('wss://your-instance.com/api/v1/ws/executions/exec_123');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Progress:', update.progress);
  console.log('Current step:', update.current_step);
};
```

### List All Executions

```bash
GET /api/v1/workflows/{workflow_id}/executions

# Response: Array of all executions
[
  {
    "execution_id": "exec_123",
    "status": "completed",
    "created_at": "2023-11-11T14:25:30Z"
  },
  ...
]
```

---

## API Documentation

### Interactive Documentation

Access the interactive API documentation at:

- **Swagger UI**: `https://your-instance.com/docs`
  - Interactive API explorer
  - Try API calls directly in browser
  - See request/response schemas

- **ReDoc**: `https://your-instance.com/redoc`
  - Beautiful, readable documentation
  - Detailed endpoint descriptions
  - Example requests and responses

- **OpenAPI JSON**: `https://your-instance.com/openapi.json`
  - Machine-readable API specification
  - Use with code generators
  - Import into Postman/Insomnia

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows` | GET | List all workflows |
| `/api/v1/workflows/{id}` | GET | Get workflow details |
| `/api/v1/workflows/visual/create` | POST | Create visual workflow |
| `/api/v1/workflows/{id}/execute` | POST | Execute workflow |
| `/api/v1/workflows/executions/{id}` | GET | Get execution status |
| `/api/v1/auth/login` | POST | Login to get JWT token |
| `/api/v1/health` | GET | System health check |

---

## Best Practices

### 1. Use Webhooks for Long-Running Workflows

Instead of polling for status, configure a webhook:

```bash
POST /api/v1/workflows/{id}/execute
{
  "parameters": {...},
  "webhook_url": "https://your-app.com/webhook/workflow-complete"
}
```

### 2. Store Workflow Templates

Create reusable workflows once, execute many times:

```bash
# Create template
POST /api/v1/workflows/visual/create

# Execute with different parameters
POST /api/v1/workflows/{template_id}/execute
{"parameters": {"pr_number": 123}}

POST /api/v1/workflows/{template_id}/execute
{"parameters": {"pr_number": 456}}
```

### 3. Handle Errors Gracefully

```bash
# Check execution status
GET /api/v1/workflows/executions/{id}

# Response may include error
{
  "status": "failed",
  "error": "Agent timeout after 300 seconds",
  "error_step": "code_generation"
}
```

### 4. Use Pagination for Large Results

```bash
GET /api/v1/workflows?page=1&per_page=20
```

---

## Pricing Tiers

Different tiers offer different capabilities:

| Feature | Free | Professional | Enterprise |
|---------|------|--------------|------------|
| Workflows/month | 100 | 1,000 | Unlimited |
| API calls/day | 1,000 | 10,000 | Unlimited |
| Real-time monitoring | ✓ | ✓ | ✓ |
| Priority support | - | ✓ | ✓ |
| Custom agents | - | - | ✓ |
| On-premise deployment | - | - | ✓ |

---

## Support and Resources

### Documentation

- 📚 [Full API Reference](./API_REFERENCE.md)
- 🏗️ [Architecture Overview](./architecture/ARCHITECTURE_DIAGRAMS.md)
- 🔧 [Advanced Configuration](./ADVANCED_CONFIG.md)

### Community

- 💬 [Discussions](https://github.com/yourusername/agentic-workflow/discussions)
- 🐛 [Report Issues](https://github.com/yourusername/agentic-workflow/issues)
- 📖 [Example Workflows](https://github.com/yourusername/agentic-workflow/tree/main/examples)

### Need Help?

- Email: support@agentic-workflow.com
- Slack: [Join our community](https://slack.agentic-workflow.com)
- Office Hours: Tuesdays 10am-12pm PST

---

## Next Steps

1. ✅ **Get API Key**: Contact your administrator or sign up
2. ✅ **Try the Examples**: Use curl examples above
3. ✅ **Explore the Docs**: Visit `/docs` endpoint
4. ✅ **Build Your First Workflow**: Start with visual builder
5. ✅ **Join the Community**: Ask questions, share workflows

**Ready to automate?** Start with a simple workflow and scale from there!

---

*Last Updated: November 11, 2025*  
*Version: 2.0 - Customer-Focused Edition*
