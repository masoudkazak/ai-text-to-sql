# Natural Language Database Gateway

This project is a secure gateway between natural language and a database: users submit requests, an LLM converts them into SQL, and a governance engine evaluates role permissions, risk level, and security policies to decide whether each query should be executed, sent for human approval, or denied.

project with FastAPI + PostgreSQL + Redis + Svelte for text-to-SQL with governance and approval workflow.

```mermaid
flowchart TD
    A["Svelte UI<br>(Frontend / User Interface)"]

    subgraph backend["FastAPI Backend"]
        B1["Authentication & Authorization"]
        B2["Query API Endpoints"]
        B3["Approval Workflow"]
        B4["Audit Logging"]

        subgraph services["Services Layer"]
            S1["LLMService<br>(Text-to-SQL)"]
            S2["SQLAnalyzer<br>(Risk Analysis)"]
            S3["GovernanceEngine<br>(Decision Engine)"]
            S4["QueryExecutor<br>(Execution Layer)"]
            S5["AuditService<br>(Logging & Traceability)"]
        end
    end

    C[("PostgreSQL<br>Persistent Storage")]
    D[("Redis<br>Caching Layer")]

    A --> B2
    B2 --> C
    B2 --> D
```

## Run

```bash
docker compose up --build -d
```

Services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

## Seeded users
- `admin@example.com / admin123`
- `analyst@example.com / analyst123`
- `developer@example.com / developer123`
- `viewer@example.com / viewer123`
- `restricted@example.com / restricted123`
