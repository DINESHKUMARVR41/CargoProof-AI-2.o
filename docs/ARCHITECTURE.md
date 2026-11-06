# CargoProof AI Architecture

## System Overview

```mermaid
flowchart TB
    Operator([Operator])

    subgraph Frontend["Frontend"]
        React["React 18 + Vite"]
        Firebase["Firebase Browser SDK"]
        Router["React Router"]
        Ui["Dashboard, Shipments, Quotes, Reports"]
    end

    subgraph Backend["FastAPI Backend"]
        Api["REST API Gateway"]
        Auth["Firebase Admin Token Verification"]
        Repo["Ownership-Scoped Repository"]
        Agent["Evidence Procurement Agent"]
        Rules["13-Rule Verification Engine"]
        Payments["Payment and Settlement Verification"]
        Integrity["SHA-256 Fingerprints and Audit Events"]
    end

    subgraph Storage["Persistence"]
        SQLite[(Persistent SQLite)]
        Supabase[(Supabase PostgreSQL)]
        Files[(Private Document Storage)]
    end

    subgraph External["External Services"]
        Providers["Configured Live Providers"]
        Sandbox["Synthetic x402 Sandbox"]
        Base["Base Sepolia USDC"]
        Algorand["Algorand TestNet USDC and Escrow"]
    end

    Operator --> React
    React --> Firebase
    Firebase --> Auth
    React --> Router --> Ui
    React -->|Bearer Firebase ID token| Api
    Api --> Auth
    Api --> Repo
    Api --> Agent
    Agent --> Providers
    Agent --> Sandbox
    Agent --> Rules
    Rules --> Integrity
    Api --> Payments
    Payments --> Base
    Payments --> Algorand
    Repo --> SQLite
    Repo --> Supabase
    Repo --> Files
    Integrity --> Repo
```

## Request and Evidence Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant FastAPI
    participant Repository
    participant Provider
    participant Engine
    participant PaymentRail

    User->>Frontend: Sign in and create shipment
    Frontend->>FastAPI: Submit shipment/document with Firebase token
    FastAPI->>FastAPI: Validate token and normalize user ID
    FastAPI->>Repository: Create owned shipment or document record
    Repository-->>FastAPI: Confirmed persistence

    User->>Frontend: Request verification
    Frontend->>FastAPI: POST /api/verify/{quote_id}
    FastAPI->>PaymentRail: Verify required customer payment
    PaymentRail-->>FastAPI: Confirmed or rejected transaction
    FastAPI->>Provider: Request evidence within budget

    alt Live provider configured
        Provider-->>FastAPI: Live provider response
    else Sandbox/provider unavailable
        Provider-->>FastAPI: Synthetic or unavailable evidence
    end

    FastAPI->>Engine: Evaluate normalized evidence
    Engine-->>FastAPI: 13 rule results, penalties, decision
    FastAPI->>Repository: Persist report and audit trail
    FastAPI-->>Frontend: Report, PDF, integrity, and source details
```

## Payment Settlement Boundaries

```mermaid
flowchart LR
    Customer[Customer]

    subgraph CustomerPayment["Customer Verification Payment"]
        Base[Base Sepolia USDC Receipt]
        Algo[Algorand TestNet USDC Transfer]
    end

    subgraph Procurement["Paid Evidence Procurement"]
        X402[x402 Algorand Requirement]
        Settlement[Provider Settlement Receipt]
    end

    subgraph EscrowRail["Separate Escrow Rail"]
        App[Algorand Escrow Application]
        Action[Hold / Release / Refund]
    end

    Customer --> Base
    Customer --> Algo
    Customer --> X402
    Base --> Verification[Backend Payment Record]
    Algo --> Verification
    X402 --> Settlement --> Verification
    Verification --> Report[Verification Report]
    App --> Action
    Action --> Report
```

Payment records, provider procurement receipts, escrow state, and verification reports remain separate. A confirmed payment unlocks its documented workflow; it does not prove physical custody, cargo condition, or successful verification.

## Storage Modes

| Mode | Data storage | Document storage | Authentication |
|---|---|---|---|
| Demo/SQLite | `backend/data/cargoproof.db` | Local private upload directory | Demo fallback or configured auth |
| Supabase | PostgreSQL through PostgREST | Private Supabase Storage | Firebase or configured backend validation |

Supabase service-role credentials are server-only. Repository queries must continue to scope data by authenticated user ID.

## 13-Rule Verification Engine

The engine evaluates submitted shipment fields and normalized provider evidence. Missing evidence never automatically passes a required check.

| Rule area | Examples |
|---|---|
| Container identity | ISO 6346 format and check digit |
| Vessel identity | Seven-digit IMO validity and checksum |
| AIS evidence | Position, speed, route, freshness |
| Ports and route | Loading/discharge, route sequence, plausibility |
| Weather | Arrival/departure marine conditions |
| Documents | SHA-256 integrity and extracted shipment fields |
| Cargo | Declared description and valuation consistency |
| Carrier coherence | Container, vessel, booking, and reference consistency |
| Customs/sanctions | Available screening and compliance evidence |

Severity is translated into rule penalties. A critical failure can reject a report, while non-critical failures may result in HOLD. Missing required evidence produces INSUFFICIENT_DATA; all required checks must pass for VERIFIED.

## API Trust Boundaries

- Firebase ID tokens are verified by the backend.
- Demo tokens are accepted only when demo authentication fallback is enabled.
- Shipment, quote, document, report, payment, and audit records are ownership-scoped.
- Private document records must not return storage paths or extracted text from public metadata listings.
- Report integrity is recomputed from persisted evidence fingerprints.
- Download endpoints require ownership validation.
- Administrative escrow actions require trusted authorization.

## Deployment Boundary

Current local operation uses React/Vite and FastAPI processes. Supabase and external provider configuration are optional integration boundaries.

Production deployment requires:

- Firebase and frontend domain configuration
- PostgreSQL or managed database hardening
- Private object-storage configuration
- Provider credentials and documented endpoints
- TestNet or mainnet network controls explicitly approved by operators
- Independent escrow contract review
- Shared rate limiting
- Secret management and centralized logging
- Backup, restore, and incident-response procedures
