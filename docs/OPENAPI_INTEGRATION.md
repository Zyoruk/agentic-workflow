# OpenAPI Integration Guide

**Current Status**: ✅ **Fully Integrated**  
**Version**: OpenAPI 3.0+  
**Last Updated**: November 11, 2025

---

## Overview

The Agentic Workflow System has **complete OpenAPI/Swagger integration** built-in through FastAPI. This provides automatic API documentation, validation, and client generation capabilities.

---

## Current OpenAPI Features

### ✅ Already Implemented

1. **Automatic OpenAPI Schema Generation**
   - FastAPI automatically generates OpenAPI 3.0+ compliant schema
   - All endpoints documented automatically
   - Request/response models defined with Pydantic
   - Type validation built-in

2. **Interactive Documentation**
   - **Swagger UI**: Available at `/docs`
   - **ReDoc**: Available at `/redoc`
   - **OpenAPI JSON**: Available at `/openapi.json`

3. **API Endpoint Coverage**
   - ✅ Health endpoints (`/api/v1/health`)
   - ✅ Workflow management (`/api/v1/workflows/*`)
   - ✅ Visual workflow builder (`/api/v1/workflows/visual/*`)
   - ✅ Workflow execution (`/api/v1/workflows/{id}/execute`)
   - ✅ Authentication (`/api/v1/auth/*`)
   - ✅ Agent management (`/api/v1/agents/*`)
   - ✅ Tool management (`/api/v1/tools/*`)
   - ✅ MCP integration (`/api/v1/mcp/*`)
   - ✅ Tenant management (`/api/v1/tenants/*`)
   - ✅ File management (`/api/v1/files/*`)
   - ✅ Billing (`/api/v1/billing/*`)
   - ✅ Business metrics (`/api/v1/business-metrics/*`)
   - ✅ WebSocket execution (`/api/v1/ws/executions/*`)

4. **Schema Features**
   - Request body validation
   - Response models with examples
   - Error response schemas
   - Security schemes (Bearer tokens, OAuth2)
   - Tags for endpoint organization
   - Operation IDs for code generation

---

## Accessing OpenAPI Documentation

### Swagger UI (Interactive)

```
https://your-instance.com/docs
```

**Features:**
- Try API calls directly in browser
- See request/response examples
- Test authentication
- Download OpenAPI spec

**Perfect for:**
- API exploration
- Manual testing
- Learning the API
- Quick prototyping

### ReDoc (Beautiful Documentation)

```
https://your-instance.com/redoc
```

**Features:**
- Clean, readable layout
- Detailed descriptions
- Code samples
- Search functionality

**Perfect for:**
- Reading documentation
- Understanding endpoints
- Sharing with team
- Reference documentation

### OpenAPI JSON (Machine-Readable)

```
https://your-instance.com/openapi.json
```

**Features:**
- Complete API specification
- Import into tools
- Generate clients
- CI/CD integration

**Perfect for:**
- Code generation
- Import into Postman/Insomnia
- Automated testing
- Integration with other tools

---

## Using OpenAPI Schema

### Import into Postman

1. Open Postman
2. Click "Import"
3. Enter URL: `https://your-instance.com/openapi.json`
4. Postman creates collection with all endpoints

### Import into Insomnia

1. Open Insomnia
2. Click "Import/Export"
3. Select "Import Data" → "From URL"
4. Enter: `https://your-instance.com/openapi.json`

### Generate Client Libraries

```bash
# Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate Python client
openapi-generator-cli generate \
  -i https://your-instance.com/openapi.json \
  -g python \
  -o ./agentic-client-python

# Generate JavaScript/TypeScript client
openapi-generator-cli generate \
  -i https://your-instance.com/openapi.json \
  -g typescript-axios \
  -o ./agentic-client-ts

# Generate Java client
openapi-generator-cli generate \
  -i https://your-instance.com/openapi.json \
  -g java \
  -o ./agentic-client-java

# Generate Go client
openapi-generator-cli generate \
  -i https://your-instance.com/openapi.json \
  -g go \
  -o ./agentic-client-go
```

### Use in CI/CD

```yaml
# Example: GitHub Actions
name: API Tests
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Download OpenAPI spec
        run: |
          curl https://your-instance.com/openapi.json > openapi.json
      
      - name: Validate OpenAPI spec
        uses: char0n/swagger-editor-validate@v1
        with:
          definition-file: openapi.json
      
      - name: Run contract tests
        run: npm test
```

---

## Current API Structure

### Endpoint Organization (Tags)

The API is organized into logical groups:

| Tag | Endpoints | Description |
|-----|-----------|-------------|
| **workflows** | `/api/v1/workflows/*` | Workflow management and execution |
| **agents** | `/api/v1/agents/*` | Agent information and capabilities |
| **tools** | `/api/v1/tools/*` | Tool registry and execution |
| **health** | `/api/v1/health` | System health monitoring |
| **authentication** | `/api/v1/auth/*` | Login, tokens, API keys |
| **tenants** | `/api/v1/tenants/*` | Multi-tenant management |
| **files** | `/api/v1/files/*` | File upload and management |
| **billing** | `/api/v1/billing/*` | Payment and subscription |
| **business-metrics** | `/api/v1/business-metrics/*` | Analytics and KPIs |
| **mcp** | `/api/v1/mcp/*` | Model Context Protocol |

### Security Schemes

The API supports multiple authentication methods:

1. **Bearer Token (JWT)**
   ```
   Authorization: Bearer eyJhbGc...
   ```

2. **API Key**
   ```
   Authorization: Bearer YOUR_API_KEY
   ```

3. **OAuth2** (Enterprise)
   ```
   OAuth2 with Authorization Code flow
   ```

---

## Enhancement Roadmap (Future)

### Phase 1: Documentation Enhancements (Q1 2026)

- [ ] Add more detailed descriptions to all endpoints
- [ ] Include more request/response examples
- [ ] Add workflow execution examples
- [ ] Document rate limiting details
- [ ] Add webhook callback examples

### Phase 2: Advanced Features (Q2 2026)

- [ ] OpenAPI 3.1 upgrade (JSON Schema 2020-12)
- [ ] Webhooks specification (OpenAPI 3.1 feature)
- [ ] GraphQL schema alongside REST
- [ ] AsyncAPI for WebSocket documentation
- [ ] API versioning in schema (v2 endpoints)

### Phase 3: Developer Experience (Q3 2026)

- [ ] Pre-generated client libraries in multiple languages
- [ ] Hosted SDK documentation
- [ ] Code samples in 10+ languages
- [ ] Interactive tutorials in docs
- [ ] Postman/Insomnia collections in repo

### Phase 4: Enterprise Features (Q4 2026)

- [ ] Private API gateway integration
- [ ] API key rotation automation
- [ ] Advanced rate limiting documentation
- [ ] Custom authentication schemes
- [ ] API governance and compliance docs

---

## Customizing OpenAPI Documentation

### Adding Endpoint Descriptions

```python
@router.post(
    "/workflows/execute",
    summary="Execute a workflow",
    description="""
    Execute a workflow with the provided parameters.
    
    This endpoint triggers the workflow execution and returns an execution ID
    that can be used to track progress and retrieve results.
    
    **Real-time updates** are available via WebSocket at the URL provided
    in the response.
    """,
    response_description="Execution details including ID and WebSocket URL",
    tags=["workflows"],
    responses={
        200: {
            "description": "Workflow execution started successfully",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "exec_20231111_142530",
                        "status": "running",
                        "websocket_url": "wss://..."
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        404: {"description": "Workflow not found"},
        422: {"description": "Validation error in parameters"}
    }
)
async def execute_workflow(...):
    ...
```

### Adding Response Examples

```python
class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    id: str = Field(..., example="wf_123")
    name: str = Field(..., example="Code Review Pipeline")
    status: str = Field(..., example="active")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "wf_20231111_142530",
                "name": "Automated Code Review",
                "status": "active",
                "created_at": "2023-11-11T14:25:30Z"
            }
        }
```

### Customizing API Metadata

In `src/agentic_workflow/api/main.py`:

```python
app = FastAPI(
    title="Agentic Workflow System",
    description="""
    AI-powered automation platform for software development.
    
    ## Features
    
    * 🤖 **Multi-Agent Intelligence**: Collaborate AI agents
    * 🎨 **Visual Workflow Builder**: Create workflows without code
    * ⚡ **Real-Time Updates**: WebSocket support
    * 🔐 **Enterprise Security**: OAuth2, JWT, API keys
    
    ## Getting Started
    
    1. Obtain an API key from your administrator
    2. Try the examples below
    3. Check out the [Getting Started Guide](https://docs.agentic-workflow.com)
    """,
    version=__version__,
    terms_of_service="https://agentic-workflow.com/terms",
    contact={
        "name": "Agentic Workflow Support",
        "url": "https://agentic-workflow.com/support",
        "email": "support@agentic-workflow.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
```

---

## Best Practices

### For API Consumers

1. **Always use the latest spec**: Download from `/openapi.json`
2. **Validate requests**: Use generated clients for type safety
3. **Handle all error codes**: Document error handling
4. **Test with Swagger UI**: Before writing code
5. **Monitor schema changes**: Subscribe to API changelog

### For API Developers

1. **Add detailed descriptions**: Every endpoint, parameter, response
2. **Provide examples**: Request and response examples
3. **Document errors**: All possible error responses
4. **Use tags effectively**: Group related endpoints
5. **Version breaking changes**: Use `/v2/` prefix for new versions

---

## Troubleshooting

### OpenAPI Spec Not Loading

```bash
# Check if API is running
curl https://your-instance.com/api/v1/health

# Verify OpenAPI endpoint
curl https://your-instance.com/openapi.json | jq
```

### Swagger UI Not Working

- Clear browser cache
- Check browser console for errors
- Verify CORS settings
- Try ReDoc at `/redoc` instead

### Generated Clients Not Working

```bash
# Validate the spec first
npx @apidevtools/swagger-cli validate openapi.json

# Check for spec version compatibility
jq '.openapi' openapi.json
```

---

## Additional Resources

### Official Documentation

- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- [FastAPI OpenAPI](https://fastapi.tiangolo.com/tutorial/metadata/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [ReDoc](https://github.com/Redocly/redoc)

### Code Generation Tools

- [OpenAPI Generator](https://openapi-generator.tech/)
- [Swagger Codegen](https://swagger.io/tools/swagger-codegen/)
- [openapi-typescript](https://github.com/drwpow/openapi-typescript)

### Validation Tools

- [Swagger Editor](https://editor.swagger.io/)
- [Spectral](https://stoplight.io/open-source/spectral)
- [OpenAPI Validator](https://github.com/APIDevTools/swagger-cli)

---

## Support

For OpenAPI-related questions:

- 📖 Read the [FastAPI OpenAPI docs](https://fastapi.tiangolo.com/tutorial/metadata/)
- 💬 Ask in [GitHub Discussions](https://github.com/yourusername/agentic-workflow/discussions)
- 📧 Email: api-support@agentic-workflow.com

---

*Last Updated: November 11, 2025*  
*Next Review: Q1 2026*
