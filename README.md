🌍 Global Event Intelligence Dashboard










A Big Data Analytics Platform for exploring global geopolitical events using the GDELT dataset, powered by ClickHouse, FastAPI, and React.

The system processes large-scale historical event data and visualizes geopolitical activity through an interactive geospatial dashboard.

📊 Project Overview

The Global Event Intelligence Dashboard analyzes worldwide political and social events using the GDELT (Global Database of Events, Language, and Tone) dataset.

The platform enables users to explore:

Global conflicts and cooperation trends

Event intensity using Goldstein Scale

Geographic distribution of political events

Historical event patterns over time

Country-level geopolitical activity

The system is designed as a big data analytics pipeline with a high-performance OLAP database and a modern web visualization dashboard.

🏗 System Architecture
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
Data Flow

1️⃣ Historical GDELT CSV files are ingested using a Python bulk loader
2️⃣ Data is stored in ClickHouse for high-performance analytics
3️⃣ FastAPI exposes REST APIs for querying event data
4️⃣ React dashboard visualizes global events on an interactive map

🧠 Architecture Diagram

(You can add a diagram here later)

Example placeholder:

CSV Data
   │
   ▼
Bulk Loader (Python)
   │
   ▼
ClickHouse Database
   │
   ▼
FastAPI API
   │
   ▼
React Dashboard
⚙️ Technology Stack
Backend

Python

FastAPI

ClickHouse Connect

Docker

Responsibilities:

Data ingestion

API services

Query execution

Database
ClickHouse

ClickHouse is used as the analytical database because it provides:

Columnar storage

High compression

Extremely fast aggregation queries

Efficient partitioning

Table configuration:

ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, global_event_id)
Frontend

The interactive dashboard is built using:

React

Material UI

Leaflet

React Leaflet

Heatmap visualization

🚀 Features
🌍 Global Event Map

Displays worldwide events using geographic coordinates.

Each event appears as a marker on the map.

🔥 Heatmap Visualization

Heatmap mode shows event intensity density across regions, highlighting geopolitical hotspots.

⏱ Timeline Explorer

Users can explore events using:

Year filter

Month filter

Day filter

Timeline autoplay

🔎 Country Search

Users can filter events by country name.

Example:

Search: India
📊 Event Summary

The dashboard shows:

Total events

Conflict events (Goldstein < 0)

Cooperation events (Goldstein > 0)

🖥 Dashboard Preview

(Add screenshots here)

Example:

/screenshots/dashboard_map.png
/screenshots/dashboard_heatmap.png
/screenshots/dashboard_summary.png
📥 Dataset

This project uses the GDELT Event Dataset, which contains structured information about global events extracted from international news sources.

Each record contains:

Column	Description
GlobalEventID	Unique event identifier
SQLDATE	Event date
Actor1CountryCode	Country involved
ActionGeo_Lat	Latitude
ActionGeo_Long	Longitude
GoldsteinScale	Event intensity
SOURCEURL	Source article
🚀 Running the Project
1️⃣ Start ClickHouse
docker compose up -d
2️⃣ Load CSV Data
python bulk_loader.py --input-dir ./data
3️⃣ Start Backend
uvicorn api:app --reload

API documentation:

http://localhost:8000/docs
4️⃣ Start Dashboard
npm start

Dashboard runs at:

http://localhost:3000
📡 API Example

Example query:

GET /events?year=2026&month=2&day=22

Example response:

[
 {
  "country": "IND",
  "lat": 20.5937,
  "lon": 78.9629,
  "goldstein": -4.0
 }
]
📂 Project Structure
gdelt-event-dashboard
│
├── backend
│   ├── api.py
│   ├── bulk_loader.py
│
├── dashboard
│   ├── src
│   │   └── App.js
│
├── docker
│   └── docker-compose.yml
│
├── data
│   └── gdelt_csv_files
│
└── README.md
⚡ Performance

Using ClickHouse provides extremely fast analytical queries.

Example metrics:

Query	Time
Event count by year	< 50 ms
Country aggregation	< 100 ms
Heatmap query	< 200 ms
📚 GDELT Event Classification
QuadClass	Meaning
1	Verbal Cooperation
2	Material Cooperation
3	Verbal Conflict
4	Material Conflict

Goldstein Scale:

-10 → strong conflict
+10 → strong cooperation
🎓 Academic Relevance

This project demonstrates concepts in:

Big Data Analytics

OLAP Databases

Data Engineering Pipelines

Geospatial Data Visualization

Full-Stack Analytics Systems

👨‍💻 Author

Manmohan Reddy
B.Tech – Data Analytics
