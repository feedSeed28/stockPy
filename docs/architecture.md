# System Architecture

## Overview

Stock Quant System is a full-stack quantitative stock analysis platform.

```
┌──────────────────────────────────────────────────────────────┐
│                       Frontend (Port 8001)                    │
│                React 18 + Ant Design Pro + ECharts            │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP (REST API)
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       Backend (Port 8000)                     │
│                     FastAPI + SQLAlchemy Async                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    API Layer (routers)                   │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │                  Service Layer (business)                │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │ │
│  │  │ Data Fetch   │  │  Stock Query  │  │  Scheduler    │  │ │
│  │  │ (AKShare)    │  │  Service      │  │  (APScheduler)│  │ │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │                   Model Layer (ORM)                      │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────┘
                               │ SQLAlchemy Async
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    MySQL 8 (stock_data)                       │
└──────────────────────────────────────────────────────────────┘
```

## Technology Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Async ORM | SQLAlchemy 2.0 async | Mature ecosystem, FastAPI native |
| MySQL Driver | asyncmy | Best async MySQL driver for Python |
| Frontend Framework | Ant Design Pro (Umi Max) | Production-ready admin UI |
| Charts | ECharts | Best candlestick/K-line support |
| Data Source | AKShare | Free, comprehensive Chinese stock data |
| Task Scheduler | APScheduler | Python-native, FastAPI compatible |
