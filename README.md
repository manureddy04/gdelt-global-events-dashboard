# 🌍 Global Event Intelligence Dashboard

> A Big Data Analytics Platform for exploring global geopolitical events using the GDELT dataset, powered by ClickHouse, FastAPI, and React.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)
![ClickHouse](https://img.shields.io/badge/ClickHouse-OLAP-yellow?logo=clickhouse&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📖 Overview

The **Global Event Intelligence Dashboard** analyzes worldwide political and social events using the [GDELT (Global Database of Events, Language, and Tone)](https://www.gdeltproject.org/) dataset. It processes large-scale historical event data and visualizes geopolitical activity through an interactive, geospatial dashboard.

### What you can explore:
- 🔴 Global conflicts and cooperation trends
- 📉 Event intensity using the **Goldstein Scale**
- 🗺️ Geographic distribution of political events
- 📅 Historical event patterns over time
- 🏳️ Country-level geopolitical activity

---

## 🏗️ System Architecture

```
GDELT CSV Files
      │
      ▼
Python Bulk Loader
      │
      ▼
ClickHouse OLAP Database
      │
      ▼
FastAPI Backend API
      │
      ▼
React + Leaflet Dashboard
```

### Data Flow

| Step | Component | Description |
|------|-----------|-------------|
| 1 | **Python Bulk Loader** | Ingests historical GDELT CSV files into the database |
| 2 | **ClickHouse** | Stores and indexes data for high-performance analytics |
| 3 | **FastAPI** | Exposes REST APIs for querying event data |
| 4 | **React + Leaflet** | Renders the interactive map-based dashboard |

---

## ⚙️ Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| Python | Bulk data loading & processing |
| FastAPI | REST API framework |
| ClickHouse | High-performance OLAP database |
| Docker | Containerized deployment |

### Frontend
| Technology | Purpose |
|------------|---------|
| React | UI framework |
| Material UI | Component library |
| Leaflet / React-Leaflet | Interactive map rendering |
| Leaflet Heatmap | Event density visualization |

### Data Source
- **[GDELT Project](https://www.gdeltproject.org/)** — A global database of events, language, and tone, monitoring the world's broadcast, print, and web news.

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| 🌍 **Global Event Map** | Visualize events across the world on an interactive map |
| 🔥 **Heatmap Visualization** | View event density hotspots geographically |
| ⏱️ **Timeline Filtering** | Filter events by Year / Month / Day |
| 🔎 **Country Search** | Search and drill down into specific countries |
| 📊 **Event Analytics** | View summary statistics and event breakdowns |
| ⚡ **OLAP Performance** | Powered by ClickHouse for sub-second query responses |

---

## 📂 Project Structure

```
gdelt-bigdata-analytics-platform/
│
├── backend/
│   ├── api.py               # FastAPI application & endpoints
│   ├── bulk_loader.py       # GDELT CSV ingestion pipeline
│   └── requirements.txt     # Python dependencies
│
├── dashboard/
│   ├── src/
│   │   └── App.js           # Main React application
│   └── package.json         # Node.js dependencies
│
├── docker/
│   └── docker-compose.yml   # ClickHouse + service orchestration
│
├── data/
│   └── gdelt_csv_files/     # Raw GDELT input data (place CSV files here)
│
└── README.md
```

---

## ▶️ Getting Started

### Prerequisites

Make sure you have the following installed:
- [Docker & Docker Compose](https://docs.docker.com/compose/install/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)

---

### 1️⃣ Start ClickHouse

```bash
cd docker
docker-compose up -d
```

ClickHouse will be available at `http://localhost:8123`.

---

### 2️⃣ Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

### 3️⃣ Load GDELT Data

Place your GDELT `.csv` files inside the `data/gdelt_csv_files/` directory, then run:

```bash
python bulk_loader.py --input-dir ./data
```

> ⏳ Depending on the volume of data, this step may take several minutes.

---

### 4️⃣ Start the Backend API

```bash
uvicorn api:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

---

### 5️⃣ Start the Dashboard

```bash
cd dashboard
npm install
npm start
```

The dashboard will be available at:

```
http://localhost:3000
```

---

## 🗃️ Database Schema (ClickHouse)

The core GDELT events table follows the structure below:

| Column | Type | Description |
|--------|------|-------------|
| `GlobalEventID` | UInt64 | Unique event identifier |
| `Day` | Date | Event date |
| `Actor1CountryCode` | String | Country code of Actor 1 |
| `Actor2CountryCode` | String | Country code of Actor 2 |
| `GoldsteinScale` | Float32 | Event impact score (-10 to +10) |
| `NumMentions` | UInt32 | Number of media mentions |
| `ActionGeo_Lat` | Float32 | Event latitude |
| `ActionGeo_Long` | Float32 | Event longitude |
| `ActionGeo_CountryCode` | String | Country where event occurred |

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/events` | Fetch paginated events |
| `GET` | `/events/heatmap` | Get heatmap data (lat, long, intensity) |
| `GET` | `/events/country/{code}` | Events filtered by country |
| `GET` | `/events/timeline` | Aggregated events by date |
| `GET` | `/events/summary` | High-level event statistics |

> Full interactive documentation available at `http://localhost:8000/docs` when the server is running.

---

## 🛠️ Troubleshooting

**ClickHouse not starting?**  
Check that port `8123` and `9000` are not already in use:
```bash
docker ps
docker-compose logs clickhouse
```

**No data appearing on the map?**  
Ensure your GDELT CSV files are placed in `data/gdelt_csv_files/` and the bulk loader completed without errors.

**Frontend not connecting to backend?**  
Verify the API is running at `http://localhost:8000` and CORS is enabled in `api.py`.

---

## 📚 References

- [GDELT Project](https://www.gdeltproject.org/) — Global event dataset
- [ClickHouse Documentation](https://clickhouse.com/docs) — OLAP database
- [FastAPI Documentation](https://fastapi.tiangolo.com/) — Python web framework
- [React Leaflet](https://react-leaflet.js.org/) — Map visualization library

---

## 👨‍💻 Author

**Manmohan Reddy**  
B.Tech – Data Analytics | Alliance University

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

> 💡 *Built as part of a Big Data Analytics capstone project exploring geopolitical trends using the GDELT dataset.*
