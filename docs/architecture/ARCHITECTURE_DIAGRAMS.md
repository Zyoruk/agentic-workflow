# Architecture Diagrams - Agentic Workflow System
## Comprehensive System Architecture Visualization

**Document Version:** 2.0  
**Date:** November 11, 2025  
**Status:** Current

---

## 0. Customer-Facing Views (New)

### 0.1 Customer Workflow Journey (40,000 Feet View)

**For Business Users and Product Managers**

```mermaid
graph TD
    START([You Have a Task]) --> API{Access Agentic<br/>Workflow API}
    
    API --> METHOD1[Option 1:<br/>Visual Workflow Builder]
    API --> METHOD2[Option 2:<br/>Single API Call]
    
    METHOD1 --> VISUAL[Create Workflow Visually<br/>- Drag and drop agents<br/>- Connect steps<br/>- Configure parameters]
    
    METHOD2 --> SIMPLE[Simple REST API Call<br/>POST /api/v1/workflows/execute]
    
    VISUAL --> EXECUTE[Execute Workflow]
    SIMPLE --> EXECUTE
    
    EXECUTE --> REALTIME[Real-time Progress<br/>via WebSocket]
    
    REALTIME --> AI[AI Agents Working<br/>- Planning<br/>- Code Generation<br/>- Testing<br/>- Review]
    
    AI --> RESULT{Results Ready}
    
    RESULT --> SUCCESS[✅ Success<br/>Get Results via API]
    RESULT --> PROGRESS[🔄 In Progress<br/>Check Status]
    RESULT --> ERROR[❌ Error<br/>Get Error Details]
    
    SUCCESS --> DASHBOARD[View in Dashboard<br/>or Access via API]
    PROGRESS --> REALTIME
    ERROR --> RETRY[Retry or Adjust]
    RETRY --> EXECUTE
    
    DASHBOARD --> DONE([Task Complete!])
    
    style START fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style API fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    style EXECUTE fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style AI fill:#f3e5f5,stroke:#6a1b9a,stroke-width:3px
    style SUCCESS fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style DONE fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
```

**What This Means for You:**
- 🎯 **Simple Integration**: Just one REST API endpoint to start automation
- 🎨 **Visual or Code**: Choose visual builder or direct API calls
- ⚡ **Real-time Updates**: Watch your workflow execute in real-time
- 🤖 **AI-Powered**: Multiple AI agents work together on your tasks
- 📊 **Full Visibility**: Track progress, get results, handle errors

### 0.2 System Components (Customer View)

**What's Under the Hood**

```mermaid
graph TB
    subgraph "🌐 Your Integration"
        YOU[Your Application]
        DASH[Web Dashboard<br/>Optional UI]
    end
    
    subgraph "🔌 API Gateway - Your Entry Point"
        REST[REST API<br/>35+ Endpoints]
        AUTH[Secure Authentication<br/>API Keys/JWT]
        DOCS[📚 OpenAPI Docs<br/>/docs /redoc]
    end
    
    subgraph "🤖 AI Agent Team - The Workers"
        COORD[Coordinator<br/>Manages workflow]
        PLAN[Planning<br/>Breaks down tasks]
        CODE[Code Generator<br/>Creates solutions]
        TEST[Tester<br/>Validates quality]
        REVIEW[Reviewer<br/>Final checks]
    end
    
    subgraph "💡 Intelligence Layer"
        GPT[GPT-4/5<br/>AI Brain]
        REASON[Smart Reasoning<br/>Decision Making]
    end
    
    subgraph "💾 Memory & Storage"
        CACHE[Fast Cache<br/>Session Data]
        VECTOR[Knowledge Base<br/>Learning & Memory]
        GRAPH[Relationships<br/>Context]
    end
    
    YOU --> REST
    DASH --> REST
    REST --> AUTH
    AUTH --> REST
    
    REST --> COORD
    COORD --> PLAN
    PLAN --> CODE
    CODE --> TEST
    TEST --> REVIEW
    
    COORD --> GPT
    PLAN --> GPT
    CODE --> GPT
    TEST --> GPT
    REVIEW --> GPT
    
    GPT --> REASON
    
    COORD --> CACHE
    PLAN --> VECTOR
    CODE --> VECTOR
    
    REST -.-> DOCS
    
    style YOU fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style REST fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    style COORD fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style GPT fill:#f3e5f5,stroke:#6a1b9a,stroke-width:3px
    style DOCS fill:#ffebee,stroke:#c62828,stroke-width:2px
```

**Key Features for You:**
- 🔐 **Enterprise Security**: OAuth2, JWT tokens, API keys
- 📖 **Self-Documenting**: Interactive OpenAPI/Swagger docs
- 🚀 **Production Ready**: Built on FastAPI, battle-tested
- 🧠 **Latest AI**: GPT-4/GPT-5 powered intelligence
- 📈 **Scalable**: Designed for high-volume production use

### 0.3 Visual Workflow Builder Flow

**Create Workflows Without Code**

```mermaid
graph LR
    subgraph "🎨 Visual Builder"
        START[1. Open Builder] --> DRAG[2. Drag Agents<br/>onto Canvas]
        DRAG --> CONNECT[3. Connect Steps<br/>with Arrows]
        CONNECT --> CONFIG[4. Configure<br/>Each Agent]
        CONFIG --> SAVE[5. Save Workflow]
    end
    
    subgraph "🚀 Execution"
        SAVE --> EXEC[6. Click Execute]
        EXEC --> WATCH[7. Watch Real-time<br/>Progress]
        WATCH --> RESULTS[8. Get Results]
    end
    
    subgraph "📊 Management"
        RESULTS --> VIEW[View History]
        VIEW --> REUSE[Reuse & Share]
        REUSE --> SCHEDULE[Schedule Runs]
    end
    
    style START fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style EXEC fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style RESULTS fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
```

**Visual Builder Benefits:**
- 🎯 **No Coding Required**: Point, click, configure
- 🔄 **Reusable Templates**: Save and share workflows
- 👥 **Team Collaboration**: Share workflows across teams
- 📅 **Scheduling**: Run workflows on a schedule
- 📈 **Version Control**: Track workflow changes

---

## 1. 20,000 Feet Architecture Diagram

### High-Level System Overview

```mermaid
graph TB
    subgraph "External Interfaces"
        UI[Web Dashboard<br/>React UI]
        CLI[CLI Tool<br/>Command Line]
        API_EXT[External Systems<br/>GitLab, Jira, etc.]
    end
    
    subgraph "API Layer"
        API[REST API Gateway<br/>FastAPI<br/>35+ Endpoints]
        WS[WebSocket Server<br/>Real-time Updates]
        AUTH[Authentication<br/>JWT/OAuth2]
    end
    
    subgraph "Agent Orchestration Layer"
        PM[Program Manager<br/>Coordination & Routing]
        PLANNER[Planning Agent<br/>Strategy & Decomposition]
        
        subgraph "Specialized Agents"
            RE[Requirement<br/>Engineering]
            CG[Code<br/>Generation]
            TEST[Testing<br/>Agent]
            CICD[CI/CD<br/>Agent]
            REVIEW[Code<br/>Review]
        end
    end
    
    subgraph "AI & Reasoning Layer"
        LLM[LLM Integration<br/>OpenAI GPT-4/5]
        REASON[Reasoning Engine<br/>CoT, ReAct, RAISE]
        COMM[Communication<br/>Manager]
    end
    
    subgraph "Tool Integration Layer"
        TOOL_REG[Tool Registry<br/>Dynamic Discovery]
        TOOL_EXEC[Tool Executor<br/>Performance Tracking]
        
        subgraph "Built-in Tools"
            FILE[File<br/>Operations]
            TEXT[Text<br/>Processing]
            CMD[Command<br/>Execution]
            DATA[Data<br/>Analysis]
        end
    end
    
    subgraph "Memory & State Management"
        CACHE[Redis Cache<br/>Session Management]
        VECTOR[Weaviate<br/>Vector Embeddings]
        GRAPH[Neo4j<br/>Knowledge Graph]
        
        subgraph "Memory Types"
            SHORT[Short-term<br/>Memory]
            LONG[Long-term<br/>Memory]
            CONTEXT[Context<br/>Windows]
        end
    end
    
    subgraph "Cross-Cutting Concerns"
        GUARD[Guardrails<br/>Safety & Validation]
        MONITOR[Monitoring<br/>Prometheus/Grafana]
        AUDIT[Audit Logging<br/>Compliance]
        EVENTS[Event Bus<br/>MQTT]
    end
    
    %% External to API Layer
    UI --> API
    CLI --> API
    API_EXT --> API
    
    %% API to Auth
    API --> AUTH
    AUTH --> API
    
    %% API to WebSocket
    API --> WS
    
    %% API to Agents
    API --> PM
    API --> PLANNER
    
    %% Orchestration
    PM --> PLANNER
    PLANNER --> RE
    PLANNER --> CG
    PLANNER --> TEST
    PLANNER --> CICD
    PLANNER --> REVIEW
    
    %% Agents to AI Layer
    RE --> LLM
    CG --> LLM
    TEST --> LLM
    CICD --> LLM
    REVIEW --> LLM
    
    %% AI Layer connections
    LLM --> REASON
    REASON --> COMM
    
    %% Agents to Tools
    RE --> TOOL_REG
    CG --> TOOL_REG
    TEST --> TOOL_REG
    CICD --> TOOL_REG
    REVIEW --> TOOL_REG
    
    TOOL_REG --> TOOL_EXEC
    TOOL_EXEC --> FILE
    TOOL_EXEC --> TEXT
    TOOL_EXEC --> CMD
    TOOL_EXEC --> DATA
    
    %% Memory connections
    PM --> CACHE
    PLANNER --> CACHE
    RE --> SHORT
    CG --> SHORT
    TEST --> SHORT
    
    SHORT --> CACHE
    LONG --> VECTOR
    CONTEXT --> CACHE
    
    VECTOR --> GRAPH
    
    %% Cross-cutting to all layers
    GUARD -.-> API
    GUARD -.-> PM
    GUARD -.-> RE
    GUARD -.-> CG
    GUARD -.-> TEST
    
    MONITOR -.-> API
    MONITOR -.-> PM
    MONITOR -.-> LLM
    
    AUDIT -.-> API
    AUDIT -.-> PM
    AUDIT -.-> CACHE
    
    EVENTS -.-> PM
    EVENTS -.-> COMM
    
    classDef apiLayer fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef agentLayer fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef aiLayer fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef toolLayer fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef memoryLayer fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef crossLayer fill:#f5f5f5,stroke:#424242,stroke-width:2px
    
    class API,WS,AUTH apiLayer
    class PM,PLANNER,RE,CG,TEST,CICD,REVIEW agentLayer
    class LLM,REASON,COMM aiLayer
    class TOOL_REG,TOOL_EXEC,FILE,TEXT,CMD,DATA toolLayer
    class CACHE,VECTOR,GRAPH,SHORT,LONG,CONTEXT memoryLayer
    class GUARD,MONITOR,AUDIT,EVENTS crossLayer
```

**Key Components:**
- **Blue (API Layer)**: External interfaces and API gateway
- **Purple (Agent Layer)**: Intelligent agents and orchestration
- **Orange (AI Layer)**: LLM integration and reasoning
- **Green (Tool Layer)**: Tool integration and execution
- **Pink (Memory Layer)**: Multi-store memory management
- **Gray (Cross-cutting)**: Monitoring, security, events

---

## 2. Module/Component Diagrams

### 2.1 Core Module Structure

```mermaid
graph LR
    subgraph "src/agentic_workflow/"
        CORE[core/<br/>Engine, Config, Logging]
        AGENTS[agents/<br/>7 Specialized Agents]
        API[api/<br/>REST Endpoints]
        TOOLS[tools/<br/>Tool System]
        MEMORY[memory/<br/>Multi-store Management]
        GRAPH[graph/<br/>Neo4j Integration]
        MCP[mcp/<br/>Model Context Protocol]
        GUARDRAILS[guardrails/<br/>Safety Systems]
        MONITOR[monitoring/<br/>Metrics & Health]
        EVENTS[events/<br/>Event System]
        UTILS[utils/<br/>Helpers & Utilities]
    end
    
    CORE --> AGENTS
    CORE --> API
    CORE --> MEMORY
    
    AGENTS --> TOOLS
    AGENTS --> MEMORY
    AGENTS --> MCP
    AGENTS --> GUARDRAILS
    
    API --> AGENTS
    API --> TOOLS
    API --> MONITOR
    
    TOOLS --> MEMORY
    
    MEMORY --> GRAPH
    
    GUARDRAILS --> MEMORY
    
    MONITOR --> EVENTS
    
    MCP --> TOOLS
    
    classDef coreModule fill:#e3f2fd,stroke:#0d47a1,stroke-width:3px
    classDef agentModule fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef infraModule fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    
    class CORE coreModule
    class AGENTS agentModule
    class API,TOOLS,MEMORY,GRAPH,MCP,GUARDRAILS,MONITOR,EVENTS,UTILS infraModule
```

### 2.2 Agent Architecture

```mermaid
graph TB
    subgraph "Base Agent Framework"
        BASE[Agent Base Class<br/>src/agents/base.py]
        TASK[AgentTask Model<br/>Input Specification]
        RESULT[AgentResult Model<br/>Output Specification]
    end
    
    subgraph "Specialized Agents (7 Total)"
        PLAN[Planning Agent<br/>837 lines<br/>Strategic Planning]
        PM[Program Manager<br/>1,949 lines<br/>Coordination]
        REQ[Requirement Engineering<br/>665 lines<br/>Requirements Analysis]
        CODE[Code Generation<br/>737 lines<br/>AI-Powered Coding]
        TEST[Testing Agent<br/>1,096 lines<br/>Test Generation]
        CICD[CI/CD Agent<br/>891 lines<br/>Pipeline Management]
        REVIEW[Review Agent<br/>1,022 lines<br/>Code Review]
    end
    
    subgraph "Agent Capabilities"
        EXEC[Execute Method<br/>Core Logic]
        INIT[Initialize Method<br/>Setup Resources]
        HEALTH[Health Check<br/>Status Monitoring]
        PLAN_METHOD[Plan Method<br/>Task Decomposition]
        CAPS[Get Capabilities<br/>Feature Discovery]
    end
    
    subgraph "Agent Support Systems"
        MEMORY_INT[Memory Integration<br/>State Management]
        LLM_INT[LLM Integration<br/>AI Capabilities]
        TOOL_INT[Tool Integration<br/>External Actions]
        GUARD_INT[Guardrails Integration<br/>Safety Checks]
    end
    
    BASE --> PLAN
    BASE --> PM
    BASE --> REQ
    BASE --> CODE
    BASE --> TEST
    BASE --> CICD
    BASE --> REVIEW
    
    BASE --> EXEC
    BASE --> INIT
    BASE --> HEALTH
    BASE --> PLAN_METHOD
    BASE --> CAPS
    
    PLAN --> MEMORY_INT
    PM --> MEMORY_INT
    REQ --> MEMORY_INT
    CODE --> LLM_INT
    TEST --> LLM_INT
    CICD --> TOOL_INT
    REVIEW --> LLM_INT
    
    EXEC --> GUARD_INT
    
    classDef baseClass fill:#fff3e0,stroke:#e65100,stroke-width:3px
    classDef agentClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef methodClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef supportClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    
    class BASE,TASK,RESULT baseClass
    class PLAN,PM,REQ,CODE,TEST,CICD,REVIEW agentClass
    class EXEC,INIT,HEALTH,PLAN_METHOD,CAPS methodClass
    class MEMORY_INT,LLM_INT,TOOL_INT,GUARD_INT supportClass
```

### 2.3 Memory Architecture

```mermaid
graph TB
    subgraph "Memory Manager"
        MANAGER[Memory Manager<br/>Central Coordinator]
        FACTORY[Memory Factory<br/>Store Creation]
    end
    
    subgraph "Short-term Memory"
        REDIS[Redis Store<br/>Fast Access<br/>Session Data]
        CACHE[Cache Layer<br/>TTL Management<br/>Stats Tracking]
        CONTEXT[Context Windows<br/>Recent History<br/>< 10 items]
    end
    
    subgraph "Long-term Memory"
        WEAVIATE[Weaviate Store<br/>Vector Embeddings<br/>Semantic Search]
        EMBEDDINGS[Embedding Service<br/>OpenAI Ada-002<br/>Text → Vectors]
    end
    
    subgraph "Graph Memory"
        NEO4J[Neo4j Database<br/>Relationship Graph<br/>Knowledge Graph]
        
        subgraph "Graph Layers"
            DOMAIN[Domain Layer<br/>Business Models]
            APP[Application Layer<br/>Use Cases]
            INFRA[Infrastructure Layer<br/>Repositories]
        end
    end
    
    subgraph "Connection Management"
        REDIS_CONN[Redis Connection<br/>Pool Management]
        WEAV_CONN[Weaviate Connection<br/>HTTP Client]
        NEO_CONN[Neo4j Connection<br/>Bolt Protocol]
    end
    
    MANAGER --> FACTORY
    
    FACTORY --> REDIS
    FACTORY --> WEAVIATE
    FACTORY --> NEO4J
    
    REDIS --> CACHE
    REDIS --> CONTEXT
    
    WEAVIATE --> EMBEDDINGS
    
    NEO4J --> DOMAIN
    NEO4J --> APP
    NEO4J --> INFRA
    
    REDIS --> REDIS_CONN
    WEAVIATE --> WEAV_CONN
    NEO4J --> NEO_CONN
    
    classDef managerClass fill:#fff3e0,stroke:#e65100,stroke-width:3px
    classDef shortClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef longClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef graphClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef connClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class MANAGER,FACTORY managerClass
    class REDIS,CACHE,CONTEXT shortClass
    class WEAVIATE,EMBEDDINGS longClass
    class NEO4J,DOMAIN,APP,INFRA graphClass
    class REDIS_CONN,WEAV_CONN,NEO_CONN connClass
```

### 2.4 Tool Integration Architecture

```mermaid
graph TB
    subgraph "Tool Manager"
        MANAGER[Tool Manager<br/>Central Coordinator]
        REGISTRY[Tool Registry<br/>Discovery & Metadata]
    end
    
    subgraph "Tool Discovery"
        DISCOVER[Dynamic Discovery<br/>Module Scanning]
        METADATA[Metadata Extraction<br/>Tool Capabilities]
        RECOMMEND[Recommendation Engine<br/>Task Matching]
    end
    
    subgraph "Built-in Tools (4 Categories)"
        subgraph "File Operations"
            FILE_READ[File Read]
            FILE_WRITE[File Write]
            FILE_LIST[Directory List]
        end
        
        subgraph "Text Processing"
            TEXT_ANALYZE[Text Analysis]
            TEXT_TRANSFORM[Text Transform]
            TEXT_VALIDATE[Text Validation]
        end
        
        subgraph "Command Execution"
            CMD_EXEC[Command Execute]
            CMD_VALIDATE[Command Validate]
        end
        
        subgraph "Data Analysis"
            DATA_STATS[Statistics]
            DATA_TRANSFORM[Transform]
            DATA_VALIDATE[Validate]
        end
    end
    
    subgraph "Tool Execution"
        EXECUTOR[Tool Executor<br/>Safe Execution]
        MONITOR[Performance Monitor<br/>Metrics Tracking]
        GUARD[Guardrails<br/>Safety Checks]
    end
    
    subgraph "Custom Tools"
        CUSTOM[Custom Tool Interface<br/>Extension Point]
        PLUGIN[Plugin System<br/>Dynamic Loading]
    end
    
    MANAGER --> REGISTRY
    MANAGER --> DISCOVER
    
    DISCOVER --> METADATA
    REGISTRY --> RECOMMEND
    
    REGISTRY --> FILE_READ
    REGISTRY --> FILE_WRITE
    REGISTRY --> FILE_LIST
    REGISTRY --> TEXT_ANALYZE
    REGISTRY --> TEXT_TRANSFORM
    REGISTRY --> TEXT_VALIDATE
    REGISTRY --> CMD_EXEC
    REGISTRY --> CMD_VALIDATE
    REGISTRY --> DATA_STATS
    REGISTRY --> DATA_TRANSFORM
    REGISTRY --> DATA_VALIDATE
    
    MANAGER --> EXECUTOR
    EXECUTOR --> MONITOR
    EXECUTOR --> GUARD
    
    REGISTRY --> CUSTOM
    CUSTOM --> PLUGIN
    
    classDef managerClass fill:#fff3e0,stroke:#e65100,stroke-width:3px
    classDef discoveryClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef toolClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef executionClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef customClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class MANAGER,REGISTRY managerClass
    class DISCOVER,METADATA,RECOMMEND discoveryClass
    class FILE_READ,FILE_WRITE,FILE_LIST,TEXT_ANALYZE,TEXT_TRANSFORM,TEXT_VALIDATE,CMD_EXEC,CMD_VALIDATE,DATA_STATS,DATA_TRANSFORM,DATA_VALIDATE toolClass
    class EXECUTOR,MONITOR,GUARD executionClass
    class CUSTOM,PLUGIN customClass
```

---

## 3. Sequence Diagrams

### 3.1 Workflow Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant PM as Program Manager
    participant Planner as Planning Agent
    participant Agent as Execution Agent
    participant Memory
    participant LLM
    participant Tools
    
    User->>API: POST /api/v1/workflows/execute
    activate API
    
    API->>API: Authenticate & Validate
    API->>PM: Create workflow execution
    activate PM
    
    PM->>Memory: Load context
    Memory-->>PM: Previous executions
    
    PM->>Planner: Request execution plan
    activate Planner
    
    Planner->>LLM: Analyze objective
    LLM-->>Planner: Analysis & decomposition
    
    Planner->>Memory: Store plan
    Planner-->>PM: Execution plan
    deactivate Planner
    
    loop For each step in plan
        PM->>Agent: Execute step
        activate Agent
        
        Agent->>Memory: Load step context
        Memory-->>Agent: Relevant data
        
        Agent->>LLM: Generate solution
        LLM-->>Agent: Generated output
        
        Agent->>Tools: Execute tool operations
        Tools-->>Agent: Tool results
        
        Agent->>Memory: Store results
        Agent-->>PM: Step result
        deactivate Agent
        
        PM->>API: Update progress (WebSocket)
        API-->>User: Real-time update
    end
    
    PM->>Memory: Store final results
    PM-->>API: Workflow complete
    deactivate PM
    
    API-->>User: 200 OK + results
    deactivate API
```

### 3.2 Agent Reasoning Flow (CoT, ReAct, RAISE)

```mermaid
sequenceDiagram
    participant Agent
    participant RE as Reasoning Engine
    participant LLM
    participant Memory
    participant Comm as Communication Manager
    
    Agent->>RE: reason(objective, pattern="raise")
    activate RE
    
    Note over RE: Phase 1: REASON
    RE->>LLM: Analyze problem
    LLM-->>RE: Initial reasoning
    RE->>Memory: Store reasoning steps
    
    Note over RE: Phase 2: ACT
    RE->>Agent: Execute action
    Agent->>LLM: Perform action
    LLM-->>Agent: Action result
    Agent-->>RE: Result
    RE->>Memory: Store action result
    
    Note over RE: Phase 3: IMPROVE
    RE->>LLM: Evaluate result
    LLM-->>RE: Improvement suggestions
    RE->>Memory: Store improvements
    
    Note over RE: Phase 4: SHARE
    RE->>Comm: Broadcast insight
    activate Comm
    Comm->>Comm: Filter recipients
    loop For each subscribed agent
        Comm->>Agent: Send insight
    end
    deactivate Comm
    
    Note over RE: Phase 5: EVALUATE
    RE->>LLM: Final evaluation
    LLM-->>RE: Confidence score
    RE->>Memory: Store evaluation
    
    RE-->>Agent: ReasoningResult
    deactivate RE
```

### 3.3 Tool Discovery and Execution

```mermaid
sequenceDiagram
    participant Agent
    participant TM as Tool Manager
    participant Registry
    participant Executor
    participant Tool
    participant Guard as Guardrails
    participant Monitor
    
    Agent->>TM: Request tool execution
    activate TM
    
    TM->>Registry: Search for tool
    Registry->>Registry: Query by name/category
    Registry-->>TM: Tool metadata
    
    TM->>Registry: Get recommendations
    Registry->>Registry: Match task to tools
    Registry-->>TM: Recommended tools
    
    TM->>Executor: Execute tool
    activate Executor
    
    Executor->>Guard: Validate inputs
    activate Guard
    Guard->>Guard: Check safety rules
    Guard-->>Executor: Validation result
    deactivate Guard
    
    alt Input valid
        Executor->>Monitor: Start tracking
        activate Monitor
        
        Executor->>Tool: Execute
        activate Tool
        Tool->>Tool: Perform operation
        Tool-->>Executor: Result
        deactivate Tool
        
        Monitor->>Monitor: Record metrics
        Monitor-->>Executor: Performance data
        deactivate Monitor
        
        Executor-->>TM: Success result
    else Input invalid
        Executor-->>TM: Error result
    end
    
    deactivate Executor
    
    TM->>Memory: Store execution record
    TM-->>Agent: Tool result
    deactivate TM
```

### 3.4 Memory Store Operation

```mermaid
sequenceDiagram
    participant Agent
    participant Manager as Memory Manager
    participant Cache as Redis Cache
    participant Vector as Weaviate
    participant Graph as Neo4j
    
    Agent->>Manager: store(data, type="context")
    activate Manager
    
    Manager->>Manager: Determine storage strategy
    
    par Parallel Storage
        Manager->>Cache: Store in cache (TTL=1h)
        activate Cache
        Cache->>Cache: Set with expiry
        Cache-->>Manager: Stored
        deactivate Cache
    and
        Manager->>Vector: Store embedding
        activate Vector
        Vector->>Vector: Generate embedding
        Vector->>Vector: Index vector
        Vector-->>Manager: Stored
        deactivate Vector
    and
        Manager->>Graph: Store relationships
        activate Graph
        Graph->>Graph: Create nodes
        Graph->>Graph: Create edges
        Graph-->>Manager: Stored
        deactivate Graph
    end
    
    Manager-->>Agent: Storage complete
    deactivate Manager
    
    Note over Agent,Graph: Later retrieval
    
    Agent->>Manager: retrieve(query, type="semantic")
    activate Manager
    
    Manager->>Cache: Check cache first
    activate Cache
    Cache-->>Manager: Cache miss
    deactivate Cache
    
    Manager->>Vector: Semantic search
    activate Vector
    Vector->>Vector: Vector similarity
    Vector-->>Manager: Top 5 results
    deactivate Vector
    
    Manager->>Graph: Get relationships
    activate Graph
    Graph->>Graph: Traverse graph
    Graph-->>Manager: Related nodes
    deactivate Graph
    
    Manager->>Manager: Merge and rank results
    Manager->>Cache: Update cache
    Manager-->>Agent: Retrieved data
    deactivate Manager
```

### 3.5 API Request Handling

```mermaid
sequenceDiagram
    participant Client
    participant LB as Load Balancer
    participant API as API Gateway
    participant Auth
    participant Agent
    participant DB as Database
    participant Monitor
    
    Client->>LB: HTTPS Request
    activate LB
    
    LB->>LB: SSL Termination
    LB->>API: Forward request
    deactivate LB
    activate API
    
    API->>Monitor: Record request
    
    API->>Auth: Validate JWT token
    activate Auth
    Auth->>Auth: Verify signature
    Auth->>DB: Check revocation
    Auth-->>API: User authenticated
    deactivate Auth
    
    API->>API: Rate limit check
    
    alt Rate limit OK
        API->>Agent: Execute business logic
        activate Agent
        Agent->>Agent: Process request
        Agent->>DB: Data operation
        DB-->>Agent: Data result
        Agent-->>API: Success response
        deactivate Agent
        
        API->>Monitor: Record success
        API-->>Client: 200 OK + data
    else Rate limit exceeded
        API->>Monitor: Record rejection
        API-->>Client: 429 Too Many Requests
    end
    
    deactivate API
```

---

## 4. Data Flow Diagrams

### 4.1 Agent Execution Data Flow

```mermaid
flowchart TD
    START([User Request]) --> VALIDATE{Valid<br/>Request?}
    
    VALIDATE -->|No| ERROR[Return Error<br/>400 Bad Request]
    VALIDATE -->|Yes| AUTH{Authenticated?}
    
    AUTH -->|No| UNAUTH[Return Error<br/>401 Unauthorized]
    AUTH -->|Yes| LOAD_CTX[Load Context<br/>from Memory]
    
    LOAD_CTX --> PLAN[Generate<br/>Execution Plan]
    PLAN --> DECOMPOSE[Decompose<br/>into Steps]
    
    DECOMPOSE --> LOOP{More<br/>Steps?}
    
    LOOP -->|Yes| EXEC_STEP[Execute Step]
    EXEC_STEP --> LLM_CALL[Call LLM<br/>if needed]
    LLM_CALL --> TOOL_EXEC[Execute Tools<br/>if needed]
    TOOL_EXEC --> GUARD{Pass<br/>Guardrails?}
    
    GUARD -->|No| FAIL[Step Failed]
    FAIL --> RETRY{Retry?}
    RETRY -->|Yes| EXEC_STEP
    RETRY -->|No| ABORT[Abort Workflow]
    
    GUARD -->|Yes| STORE[Store Result]
    STORE --> UPDATE[Update Progress]
    UPDATE --> LOOP
    
    LOOP -->|No| AGGREGATE[Aggregate Results]
    AGGREGATE --> FINAL_STORE[Store Final Result]
    FINAL_STORE --> METRICS[Update Metrics]
    METRICS --> SUCCESS[Return Success<br/>200 OK]
    
    ERROR --> END([End])
    UNAUTH --> END
    ABORT --> END
    SUCCESS --> END
    
    style START fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style SUCCESS fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style ERROR fill:#ffebee,stroke:#c62828,stroke-width:3px
    style UNAUTH fill:#ffebee,stroke:#c62828,stroke-width:3px
    style ABORT fill:#ffebee,stroke:#c62828,stroke-width:3px
    style END fill:#f5f5f5,stroke:#616161,stroke-width:3px
```

### 4.2 Memory Storage Data Flow

```mermaid
flowchart LR
    INPUT[Input Data] --> CLASSIFY[Classify Data Type]
    
    CLASSIFY --> SHORT{Short-term<br/>Memory?}
    CLASSIFY --> LONG{Long-term<br/>Memory?}
    CLASSIFY --> GRAPH{Graph<br/>Data?}
    
    SHORT -->|Yes| REDIS[(Redis<br/>Cache)]
    REDIS --> TTL[Set TTL<br/>1 hour]
    
    LONG -->|Yes| EMBED[Generate<br/>Embeddings]
    EMBED --> WEAVIATE[(Weaviate<br/>Vector Store)]
    
    GRAPH -->|Yes| EXTRACT[Extract<br/>Relationships]
    EXTRACT --> NEO4J[(Neo4j<br/>Graph DB)]
    
    TTL --> STORED[Data Stored]
    WEAVIATE --> STORED
    NEO4J --> STORED
    
    STORED --> INDEX[Update Indexes]
    INDEX --> COMPLETE([Storage Complete])
    
    style INPUT fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style REDIS fill:#ffebee,stroke:#c62828,stroke-width:2px
    style WEAVIATE fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style NEO4J fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style COMPLETE fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
```

---

## 5. Deployment Architecture

### 5.1 Production Deployment

```mermaid
graph TB
    subgraph "Load Balancing Layer"
        LB[Load Balancer<br/>NGINX/HAProxy]
        WAF[Web Application Firewall<br/>ModSecurity]
    end
    
    subgraph "Application Layer - Auto-scaled"
        APP1[API Instance 1<br/>FastAPI]
        APP2[API Instance 2<br/>FastAPI]
        APP3[API Instance N<br/>FastAPI]
    end
    
    subgraph "Caching Layer"
        REDIS1[(Redis Primary)]
        REDIS2[(Redis Replica)]
    end
    
    subgraph "Database Layer"
        NEO4J1[(Neo4j Primary)]
        NEO4J2[(Neo4j Replica)]
        
        WEAV1[(Weaviate Primary)]
        WEAV2[(Weaviate Replica)]
    end
    
    subgraph "Monitoring Stack"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[AlertManager]
    end
    
    subgraph "Logging Stack"
        LOGS[Log Aggregator<br/>Fluentd]
        ES[Elasticsearch]
        KIBANA[Kibana]
    end
    
    INTERNET[Internet] --> LB
    LB --> WAF
    WAF --> APP1
    WAF --> APP2
    WAF --> APP3
    
    APP1 --> REDIS1
    APP2 --> REDIS1
    APP3 --> REDIS1
    
    REDIS1 --> REDIS2
    
    APP1 --> NEO4J1
    APP2 --> NEO4J1
    APP3 --> NEO4J1
    
    NEO4J1 --> NEO4J2
    
    APP1 --> WEAV1
    APP2 --> WEAV1
    APP3 --> WEAV1
    
    WEAV1 --> WEAV2
    
    APP1 --> PROM
    APP2 --> PROM
    APP3 --> PROM
    
    PROM --> GRAF
    PROM --> ALERT
    
    APP1 --> LOGS
    APP2 --> LOGS
    APP3 --> LOGS
    
    LOGS --> ES
    ES --> KIBANA
    
    classDef lbClass fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef appClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef cacheClass fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef dbClass fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef monClass fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    
    class LB,WAF lbClass
    class APP1,APP2,APP3 appClass
    class REDIS1,REDIS2 cacheClass
    class NEO4J1,NEO4J2,WEAV1,WEAV2 dbClass
    class PROM,GRAF,ALERT,LOGS,ES,KIBANA monClass
```

---

## 6. Technology Stack Diagram

```mermaid
graph TB
    subgraph "Frontend Layer"
        REACT[React 18<br/>TypeScript]
        TAILWIND[Tailwind CSS]
    end
    
    subgraph "API Layer"
        FASTAPI[FastAPI 0.109+<br/>Python 3.11+]
        PYDANTIC[Pydantic 2.6+<br/>Data Validation]
        UVICORN[Uvicorn<br/>ASGI Server]
    end
    
    subgraph "AI/ML Layer"
        LANGCHAIN[LangChain 0.1+<br/>AI Framework]
        OPENAI[OpenAI API<br/>GPT-4/GPT-5]
        EMBEDDINGS[OpenAI Embeddings<br/>Ada-002]
    end
    
    subgraph "Storage Layer"
        REDIS[Redis 7+<br/>Cache & Sessions]
        NEO4J[Neo4j 5+<br/>Graph Database]
        WEAVIATE[Weaviate 4+<br/>Vector Store]
    end
    
    subgraph "Infrastructure"
        DOCKER[Docker<br/>Containerization]
        K8S[Kubernetes<br/>Orchestration]
        PROMETHEUS[Prometheus<br/>Metrics]
        GRAFANA[Grafana<br/>Visualization]
    end
    
    REACT --> FASTAPI
    TAILWIND --> REACT
    
    FASTAPI --> PYDANTIC
    FASTAPI --> UVICORN
    FASTAPI --> LANGCHAIN
    
    LANGCHAIN --> OPENAI
    LANGCHAIN --> EMBEDDINGS
    
    FASTAPI --> REDIS
    FASTAPI --> NEO4J
    FASTAPI --> WEAVIATE
    
    UVICORN --> DOCKER
    DOCKER --> K8S
    
    FASTAPI --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    
    classDef frontendClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef apiClass fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef aiClass fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef storageClass fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef infraClass fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class REACT,TAILWIND frontendClass
    class FASTAPI,PYDANTIC,UVICORN apiClass
    class LANGCHAIN,OPENAI,EMBEDDINGS aiClass
    class REDIS,NEO4J,WEAVIATE storageClass
    class DOCKER,K8S,PROMETHEUS,GRAFANA infraClass
```

---

## Summary

This document provides comprehensive architectural visualizations of the Agentic Workflow System at multiple levels of abstraction:

1. **20,000 Feet View**: Complete system overview with all major components
2. **Module Diagrams**: Internal structure of key modules (Agents, Memory, Tools)
3. **Sequence Diagrams**: Detailed interaction flows for core operations
4. **Data Flow Diagrams**: Data movement through the system
5. **Deployment Architecture**: Production infrastructure layout
6. **Technology Stack**: Technologies and versions used

**Usage:**
- Architecture reviews: Use 20,000 feet diagram
- Development planning: Use module and component diagrams
- Debugging: Use sequence and data flow diagrams
- DevOps planning: Use deployment architecture
- Technology decisions: Use technology stack diagram

**Maintenance:**
- Review and update diagrams with each major release
- Update when significant architectural changes occur
- Keep synchronized with implementation

---

**Document Owner:** Solutions Architect  
**Contributors:** Engineering Team  
**Last Updated:** November 9, 2025  
**Next Review:** December 9, 2025
