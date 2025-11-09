# PostgreSQL Database Schema

**Sprint 5-6 Deliverable**: Database schema design for workflow orchestration system

**Status**: Ready for implementation  
**Database**: PostgreSQL 14+  
**Migration Tool**: Alembic  
**ORM**: SQLAlchemy 2.0+

## Overview

This schema supports the visual workflow builder with multi-tenant architecture, RBAC, and comprehensive audit logging. The design prioritizes:

- **Performance**: Optimized indexes for common queries
- **Security**: Row-level access control via ownership
- **Scalability**: Partitioning strategy for large datasets
- **Audit**: Complete change history tracking
- **Multi-tenancy**: Organization-level isolation

## Core Tables

### 1. workflows

Stores workflow definitions with visual graph representation.

```sql
CREATE TABLE workflows (
    -- Primary key
    id VARCHAR(255) PRIMARY KEY,
    
    -- Workflow metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Ownership & tenancy
    owner VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    
    -- Visual graph definition (JSONB for flexibility)
    nodes JSONB NOT NULL,
    edges JSONB NOT NULL,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- State
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, archived
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255) NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE, -- Soft delete
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('draft', 'active', 'archived')),
    CONSTRAINT valid_nodes CHECK (jsonb_typeof(nodes) = 'array'),
    CONSTRAINT valid_edges CHECK (jsonb_typeof(edges) = 'array')
);

-- Indexes for performance
CREATE INDEX idx_workflows_owner ON workflows(owner) WHERE deleted_at IS NULL;
CREATE INDEX idx_workflows_org ON workflows(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_workflows_status ON workflows(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_workflows_created ON workflows(created_at DESC);
CREATE INDEX idx_workflows_tags ON workflows USING GIN(tags);
CREATE INDEX idx_workflows_metadata ON workflows USING GIN(metadata);

-- Full-text search on name and description
CREATE INDEX idx_workflows_search ON workflows USING GIN(
    to_tsvector('english', name || ' ' || COALESCE(description, ''))
) WHERE deleted_at IS NULL;

-- Trigger for updated_at
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2. executions

Tracks workflow execution instances with results.

```sql
CREATE TABLE executions (
    -- Primary key
    id VARCHAR(255) PRIMARY KEY,
    
    -- Foreign keys
    workflow_id VARCHAR(255) NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    
    -- Ownership
    owner VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    
    -- Execution details
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    -- queued, running, completed, failed, cancelled, timeout
    
    -- Input/output
    parameters JSONB DEFAULT '{}',
    result JSONB,
    error JSONB,
    
    -- Performance metrics
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10, 3),
    
    -- Step tracking
    current_step VARCHAR(255),
    steps_completed INTEGER DEFAULT 0,
    steps_total INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    trace_id VARCHAR(255), -- For distributed tracing
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_execution_status CHECK (
        status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'timeout')
    ),
    CONSTRAINT valid_parameters CHECK (jsonb_typeof(parameters) = 'object'),
    CONSTRAINT valid_duration CHECK (
        duration_seconds IS NULL OR duration_seconds >= 0
    )
);

-- Indexes
CREATE INDEX idx_executions_workflow ON executions(workflow_id);
CREATE INDEX idx_executions_owner ON executions(owner);
CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_created ON executions(created_at DESC);
CREATE INDEX idx_executions_trace ON executions(trace_id) WHERE trace_id IS NOT NULL;

-- Composite index for common queries
CREATE INDEX idx_executions_workflow_status ON executions(workflow_id, status, created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER update_executions_updated_at
    BEFORE UPDATE ON executions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to calculate duration
CREATE TRIGGER calculate_execution_duration
    BEFORE UPDATE ON executions
    FOR EACH ROW
    WHEN (NEW.completed_at IS NOT NULL AND OLD.completed_at IS NULL)
    EXECUTE FUNCTION calculate_duration();
```

### 3. users

User accounts with authentication and authorization.

```sql
CREATE TABLE users (
    -- Primary key
    id VARCHAR(255) PRIMARY KEY,
    
    -- Authentication
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    full_name VARCHAR(255),
    avatar_url TEXT,
    
    -- Organization
    organization_id VARCHAR(255),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Permissions (JSONB array of scope strings)
    scopes JSONB DEFAULT '["workflow:read", "workflow:execute"]',
    
    -- Security
    last_login TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_org ON users(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_active ON users(is_active) WHERE deleted_at IS NULL;

-- Trigger for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## Helper Functions

### update_updated_at_column

Automatically updates the `updated_at` timestamp.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### calculate_duration

Calculates execution duration when completed.

```sql
CREATE OR REPLACE FUNCTION calculate_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Migration Strategy

### Phase 1: Initial Schema (Sprint 5-6)
1. Create helper functions
2. Create core tables (workflows, executions, users)
3. Create indexes
4. Seed initial admin user

### Phase 2: Enhanced Features (Sprint 7-8)
1. Add organizations table
2. Implement audit_log
3. Add foreign key constraints

### Phase 3: Performance Optimization (Sprint 9+)
1. Implement partitioning for audit_log
2. Add materialized views for analytics
3. Implement read replicas

---

**Document Version**: 1.0  
**Last Updated**: November 9, 2025  
**Status**: Ready for Sprint 5-6 implementation
