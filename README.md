# **ESP32 Sensor API & Data Stack**

A data ingestion, retrieval, and analysis backend for microcontroller sensor streams (ESP32) with initial support for RAG-style natural language querying.  
 This repository provides:

* a FastAPI server for ingesting and querying sensor data

* tools for semantic indexing and retrieval via LLM agent

* a planned UI component (Next.js frontend integration) for data visualization and interaction

This project is evolving toward a production-ready sensor data platform with LLM chat interaction and analytics.

---

## **Overview**

The `esp32_api` project is designed to collect, store, and query time-series sensor data from ESP32 microcontrollers. It also integrates an agentic AI framework that allows users to ask open-ended questions about trends and anomalies in the data, experimenting with both Retrieval Augmented Generation (RAG) and natural language-to-SQL (NLSQL) strategies.

Key aspects of the stack include:

* FastAPI backend with REST endpoints (`/ingest`, `/timeseries`)

* PostgreSQL database for sensor storage and snapshots

* Vector embedding and semantic retrieval endpoints (`/rag/query`, `/rag/index`, `/rag/ingest_docs`)

* Planned integration with a React/Next.js frontend for visualization and agent interaction

*(See also the documentation structure below.)*

---

## **Documentation Structure**

This repository follows a structured documentation layout inspired by best practices. The primary documentation is housed under the `docs/` folder. Key sections include:

**Notes & Tutorials**

* `docs/notes/2026-01-rag-endpoints-and-vector-stores.md` — Developer notes on RAG, vector stores, and query endpoints.

* *(Future)* additional notes covering architectural decisions and integrations.

**Architecture & Design**

* `docs/architecture/overview.md` — High-level system architecture and data flow.

* `docs/architecture/state-management.md` — Notes on backend & frontend state strategies.

**Endpoint References**

* `docs/endpoints/ingest.md` — Ingestion API details.

* `docs/endpoints/query.md` — Query and analytics API details.

**Developer Guides**

* `docs/dev/cli.md` — CLI references & scripts.

* `docs/dev/testing.md` — Testing and workflow recommendations.

*(Each of these may be created as the project matures — see placeholders in the `/docs/` directory.)*

---

## **Architecture**

The system is composed of the following high-level components:

`ESP32 Devices`  
      `↓ (HTTP Ingestion)`  
`FastAPI Backend ── PostgreSQL ── Snapshots & Raw Data`  
      `├─ /ingest, /timeseries`  
      `└─ /rag/index, /rag/query, /rag/ingest_docs`  
           `├─ SQL + Time-Series Logic`  
           `└─ RAG / Embeddings`  
`Front-end (Next.js / React / TypeScript) — visualization & agent interaction`

The planned frontend will most likely integrate the Vercel/Next AI SDK, which would move the RAG endpoints to frontend API routes in TypeScript.

---

## **Installation**

### **Prerequisites**

* **Python 3.11+**

* **PostgreSQL** instance with credentials available (e.g. Supabase)

* `pgvector` extension installed in PostgreSQL for vector embeddings (e.g. in Supabase, install `vector` under Database > Extensions)

### **Local Setup**

Clone the repository and install dependencies:

`git clone https://github.com/postoccupancy/esp32_api.git`  
`cd esp32_api`  
`pip install -r server/requirements.txt`

Set up environment variables (see **Configuration** below), then start the API:

`uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload`

---

## **API Endpoints**

### **Ingestion**

`POST /ingest`  
 Ingests sensor payloads from ESP32 devices. Payload structure and parameters TBD.

### **Time-Series Queries**

`GET /timeseries`  
Returns filtered time-series data based on query parameters (`sensor`, `from`, `to`, `avg`, `min`, `max`, etc.).

### **RAG & Semantic Endpoints**

* `POST /rag/query` — Natural language question answering combining SQL data and/or semantic retrieval

* `POST /rag/index` — Batch indexing of time-series snapshots into vector store to allow non-SQL data queries

* `POST /rag/ingest_docs` — Ingest reference PDFs and web pages into the vector store

*(Detailed request/response schemas to be documented in `/docs/endpoints/*.md`.)*

---

## **Configuration**

Environment variables are used to control database connections. Copy `.env.example` to `.env` and fill in the required values.


---

## **Project Structure**

`esp32_api/`  
`├── server/                  # Backend service (FastAPI)`  
`│   ├── app/                # Core application modules`  
`│   ├── rag/                # RAG & indexing logic`  
`│   └── main.py             # FastAPI entry point`  
`├── device/                  # Device-side scripts & examples`  
`├── ui/                      # Placeholder for future frontend`  
`├── docs/                    # Project documentation`  
`│   ├── notes/`  
`│   ├── architecture/`  
`│   └── endpoints/`  
`├── .env.example             # Example environment vars`  
`└── README.md                # This file`


---

## **Contributing**

Contributions are welcome\! For structured guidelines, see the `CONTRIBUTING.md` once created. For now:

1. Fork the repo

2. Create a descriptive branch

3. Open a pull request with context and tests (when available)

---

## **License**

This project is open source and released under the BSD-3 Clause License.

---

## **What’s Next / Roadmap**

As the repository evolves, the following documentation is planned (placeholders exist under `/docs/`):

* **CLI Utility Guides** (`docs/dev/cli.md`)

* **Endpoint Schema References** (`docs/endpoints/*.md`)

* **Architecture & Data Flow Diagrams** (`docs/architecture/*.md`)

* **Testing and CI** (`docs/dev/testing.md`)

* **Frontend Integration Guide** (`docs/frontend/overview.md`)

