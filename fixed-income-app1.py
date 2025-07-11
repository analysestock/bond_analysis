#!/usr/bin/env python3
"""
Fixed Income Market Analysis Web Application
A comprehensive bond trading dashboard with modular architecture
"""

import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3
from contextlib import contextmanager

from flask import Flask, render_template_string, jsonify, request, session
from flask_cors import CORS
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import plotly.graph_objs as go
import plotly.utils

# =======================
# Configuration Module
# =======================

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bonds.db')
    BLOOMBERG_API_KEY = os.environ.get('BLOOMBERG_API_KEY', 'mock-api-key')
    CACHE_TTL = 300  # 5 minutes
    
# =======================
# Data Models
# =======================

@dataclass
class Bond:
    """Bond data model"""
    isin: str
    ticker: str
    coupon: float
    maturity: str
    yield_value: float
    spread: int
    duration: float
    rating: str
    sector: str
    currency: str
    price: float = 100.0
    issue_size: float = 1000000000  # Default 1B
    
@dataclass
class ClientPreferences:
    """Client preferences model"""
    user_id: str
    watchlist: List[str]
    sectors: List[str]
    duration_range: List[float]
    min_rating: str
    alert_thresholds: Dict[str, float]
    
# =======================
# Database Layer
# =======================

class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self, db_path='bonds.db'):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database schema"""
        with self.get_db() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS bonds (
                    isin TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    coupon REAL,
                    maturity TEXT,
                    yield_value REAL,
                    spread INTEGER,
                    duration REAL,
                    rating TEXT,
                    sector TEXT,
                    currency TEXT,
                    price REAL,
                    issue_size REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isin TEXT,
                    date TEXT,
                    yield_value REAL,
                    spread INTEGER,
                    price REAL,
                    FOREIGN KEY (isin) REFERENCES bonds(isin)
                );
                
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    alert_type TEXT,
                    threshold REAL,
                    triggered_at TIMESTAMP
                );
            ''')
            conn.commit()

# =======================
# Mock Data Generator
# =======================

class MockDataGenerator:
    """Generate realistic mock bond data"""
    
    SECTORS = ['Government', 'Corporate IG', 'Corporate HY', 'Municipal', 'Agency', 'Sovereign']
    RATINGS = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-']
    CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF']
    
    @staticmethod
    def generate_bonds(count: int = 50) -> List[Bond]:
        """Generate mock bond data"""
        bonds = []
        base_date = datetime.now()
        
        for i in range(count):
            maturity_years = random.randint(1, 30)
            maturity_date = base_date + timedelta(days=365 * maturity_years)
            
            sector = random.choice(MockDataGenerator.SECTORS)
            rating = random.choice(MockDataGenerator.RATINGS)
            
            # Base yield depends on rating and maturity
            base_yield = 2.0 + (maturity_years * 0.1)
            if 'BBB' in rating:
                base_yield += 1.5
            elif 'A' in rating:
                base_yield += 0.5
            
            yield_value = round(base_yield + random.uniform(-0.5, 0.5), 2)
            
            bond = Bond(
                isin=f"XS{str(i).zfill(10)}",
                ticker=f"{sector[:3].upper()} {round(random.uniform(1, 6), 2)}% {maturity_date.year}",
                coupon=round(random.uniform(1, 6), 2),
                maturity=maturity_date.strftime("%Y-%m-%d"),
                yield_value=yield_value,
                spread=random.randint(10, 300),
                duration=round(maturity_years * 0.85 + random.uniform(-1, 1), 1),
                rating=rating,
                sector=sector,
                currency=random.choice(MockDataGenerator.CURRENCIES),
                price=100 - (yield_value - 3) * 5 + random.uniform(-2, 2),
                issue_size=random.choice([500000000, 1000000000, 2000000000, 5000000000])
            )
            bonds.append(bond)
        
        return bonds
    
    @staticmethod
    def generate_historical_data(isin: str, days: int = 30) -> pd.DataFrame:
        """Generate historical price data"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        base_yield = 3.5
        base_spread = 50
        
        data = []
        for date in dates:
            # Add some random walk
            yield_change = random.uniform(-0.05, 0.05)
            spread_change = random.randint(-2, 2)
            
            base_yield += yield_change
            base_spread += spread_change
            
            data.append({
                'date': date,
                'yield_value': round(base_yield, 3),
                'spread': base_spread,
                'price': round(100 - (base_yield - 3) * 5, 2)
            })
        
        return pd.DataFrame(data)

# =======================
# Bloomberg API Placeholders
# =======================

async def fetch_bond_data(isin: str) -> dict:
    """Placeholder for Bloomberg BDP (Reference Data)"""
    # In production, this would call Bloomberg API
    # For now, return mock data
    mock_gen = MockDataGenerator()
    bonds = mock_gen.generate_bonds(1)
    return asdict(bonds[0]) if bonds else None

async def fetch_historical_data(isin: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Placeholder for Bloomberg BDH (Historical Data)"""
    # In production, this would call Bloomberg API
    # For now, return mock historical data
    days = (datetime.strptime(end_date, "%Y-%m-%d") - 
            datetime.strptime(start_date, "%Y-%m-%d")).days
    return MockDataGenerator.generate_historical_data(isin, days)

async def subscribe_real_time(securities: list) -> None:
    """Placeholder for Bloomberg real-time subscription"""
    # In production, this would set up Bloomberg real-time feed
    # For now, we'll simulate with periodic updates
    pass

# =======================
# Analytics Engine
# =======================

class AnalyticsEngine:
    """Bond analytics calculations"""
    
    @staticmethod
    def calculate_total_return(bond: Bond, holding_period_days: int = 30) -> float:
        """Calculate total return including price change and coupon"""
        coupon_income = (bond.coupon / 100) * (holding_period_days / 365)
        price_return = random.uniform(-2, 2) / 100  # Mock price change
        return round((coupon_income + price_return) * 100, 2)
    
    @staticmethod
    def calculate_spread_change(current_spread: int, historical_spread: int) -> int:
        """Calculate spread change in basis points"""
        return current_spread - historical_spread
    
    @staticmethod
    def generate_yield_curve(currency: str = 'USD') -> Dict[str, List]:
        """Generate yield curve data"""
        tenors = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
        
        # Base curve with some realistic shape
        if currency == 'USD':
            base_rates = [3.5, 3.7, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7]
        else:
            base_rates = [2.5, 2.7, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7]
        
        yields = [rate + random.uniform(-0.1, 0.1) for rate in base_rates]
        
        return {
            'tenors': tenors,
            'yields': [round(y, 3) for y in yields]
        }

# =======================
# Flask Application
# =======================

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db_manager = DatabaseManager()
analytics = AnalyticsEngine()

# =======================
# HTML Templates
# =======================

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fixed Income Analytics Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        body { background-color: #f8f9fa; }
        .card { margin-bottom: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .navbar { background-color: #1a1a2e !important; }
        .table-hover tbody tr:hover { background-color: #e9ecef; }
        .metric-card { text-align: center; padding: 20px; }
        .metric-value { font-size: 2em; font-weight: bold; }
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .chart-container { height: 400px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">Fixed Income Analytics</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/analytics">Analytics</a>
                <a class="nav-link" href="/preferences">Preferences</a>
            </div>
        </div>
    </nav>
    
    <div class="container-fluid mt-4">
        {% block content %}{% endblock %}
    </div>
    
    <script>
        // Auto-refresh data every 30 seconds
        setInterval(function() {
            if (window.refreshData) {
                window.refreshData();
            }
        }, 30000);
    </script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
{% extends "base.html" %}
{% block content %}
<div class="row">
    <!-- Market Overview -->
    <div class="col-md-12">
        <h2>Market Overview</h2>
    </div>
    
    <!-- Key Metrics -->
    <div class="col-md-3">
        <div class="card metric-card">
            <h5>10Y US Treasury</h5>
            <div class="metric-value">4.25%</div>
            <small class="positive">+5 bps</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card metric-card">
            <h5>IG Spread</h5>
            <div class="metric-value">125 bps</div>
            <small class="negative">-3 bps</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card metric-card">
            <h5>HY Spread</h5>
            <div class="metric-value">425 bps</div>
            <small class="positive">+8 bps</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card metric-card">
            <h5>EUR/USD</h5>
            <div class="metric-value">1.0875</div>
            <small class="negative">-0.25%</small>
        </div>
    </div>
</div>

<div class="row mt-4">
    <!-- Yield Curve Chart -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Yield Curves</h5>
            </div>
            <div class="card-body">
                <div id="yieldCurveChart" class="chart-container"></div>
            </div>
        </div>
    </div>
    
    <!-- Spread Analysis -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Spread Analysis</h5>
            </div>
            <div class="card-body">
                <div id="spreadChart" class="chart-container"></div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <!-- Bond Watchlist -->
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5>Bond Watchlist</h5>
                <button class="btn btn-sm btn-primary float-end" onclick="exportData()">Export</button>
            </div>
            <div class="card-body">
                <table class="table table-hover" id="bondTable">
                    <thead>
                        <tr>
                            <th>ISIN</th>
                            <th>Ticker</th>
                            <th>Sector</th>
                            <th>Rating</th>
                            <th>Maturity</th>
                            <th>Yield</th>
                            <th>Spread</th>
                            <th>Duration</th>
                            <th>Price</th>
                            <th>Change</th>
                        </tr>
                    </thead>
                    <tbody id="bondTableBody">
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <!-- Market News -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Market News</h5>
            </div>
            <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                <div class="mb-3">
                    <h6>Fed Signals Potential Rate Pause</h6>
                    <small class="text-muted">2 hours ago</small>
                    <p>Federal Reserve officials indicated they may pause rate hikes...</p>
                </div>
                <div class="mb-3">
                    <h6>European IG Spreads Tighten</h6>
                    <small class="text-muted">4 hours ago</small>
                    <p>Investment grade credit spreads in Europe compressed by 5bps...</p>
                </div>
                <div class="mb-3">
                    <h6>New Corporate Bond Issuance Surge</h6>
                    <small class="text-muted">6 hours ago</small>
                    <p>Corporate bond issuance reached $45bn this week...</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Top Movers -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Top Movers</h5>
            </div>
            <div class="card-body">
                <div id="moversChart" class="chart-container"></div>
            </div>
        </div>
    </div>
</div>

<script>
// Initialize dashboard
$(document).ready(function() {
    loadBondData();
    loadYieldCurve();
    loadSpreadAnalysis();
    loadTopMovers();
});

function loadBondData() {
    $.get('/api/bonds', function(data) {
        const tbody = $('#bondTableBody');
        tbody.empty();
        
        data.bonds.forEach(bond => {
            const change = (Math.random() * 4 - 2).toFixed(2);
            const changeClass = change >= 0 ? 'positive' : 'negative';
            
            tbody.append(`
                <tr>
                    <td>${bond.isin}</td>
                    <td>${bond.ticker}</td>
                    <td>${bond.sector}</td>
                    <td>${bond.rating}</td>
                    <td>${bond.maturity}</td>
                    <td>${bond.yield_value.toFixed(2)}%</td>
                    <td>${bond.spread} bps</td>
                    <td>${bond.duration.toFixed(1)}</td>
                    <td>${bond.price.toFixed(2)}</td>
                    <td class="${changeClass}">${change >= 0 ? '+' : ''}${change}%</td>
                </tr>
            `);
        });
    });
}

function loadYieldCurve() {
    $.get('/api/yield-curve', function(data) {
        const traces = [];
        
        ['USD', 'EUR'].forEach(currency => {
            const curveData = data[currency];
            traces.push({
                x: curveData.tenors,
                y: curveData.yields,
                mode: 'lines+markers',
                name: currency,
                line: { width: 3 }
            });
        });
        
        const layout = {
            title: 'Yield Curves',
            xaxis: { title: 'Tenor (Years)' },
            yaxis: { title: 'Yield (%)' },
            hovermode: 'x unified'
        };
        
        Plotly.newPlot('yieldCurveChart', traces, layout);
    });
}

function loadSpreadAnalysis() {
    // Mock spread data by rating
    const ratings = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B'];
    const spreads = [25, 45, 85, 125, 425, 625];
    
    const trace = {
        x: ratings,
        y: spreads,
        type: 'bar',
        marker: {
            color: spreads,
            colorscale: 'Viridis'
        }
    };
    
    const layout = {
        title: 'Credit Spreads by Rating',
        xaxis: { title: 'Rating' },
        yaxis: { title: 'Spread (bps)' }
    };
    
    Plotly.newPlot('spreadChart', [trace], layout);
}

function loadTopMovers() {
    // Mock top movers data
    const movers = [
        { name: 'XS1234567890', change: 15 },
        { name: 'XS2345678901', change: 12 },
        { name: 'XS3456789012', change: -10 },
        { name: 'XS4567890123', change: -8 },
        { name: 'XS5678901234', change: 7 }
    ];
    
    const trace = {
        x: movers.map(m => m.change),
        y: movers.map(m => m.name),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: movers.map(m => m.change > 0 ? 'green' : 'red')
        }
    };
    
    const layout = {
        title: 'Top Yield Movers (bps)',
        xaxis: { title: 'Change (bps)' },
        margin: { l: 100 }
    };
    
    Plotly.newPlot('moversChart', [trace], layout);
}

function exportData() {
    window.location.href = '/api/export/bonds';
}

window.refreshData = function() {
    loadBondData();
    loadYieldCurve();
    loadSpreadAnalysis();
    loadTopMovers();
};
</script>
{% endblock %}
'''

ANALYTICS_TEMPLATE = '''
{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>Advanced Analytics</h2>
    </div>
</div>

<div class="row mt-4">
    <!-- Duration vs Yield Scatter -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Duration vs Yield Analysis</h5>
            </div>
            <div class="card-body">
                <div id="durationYieldChart" class="chart-container"></div>
            </div>
        </div>
    </div>
    
    <!-- Sector Performance Heatmap -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Sector Performance Heatmap</h5>
            </div>
            <div class="card-body">
                <div id="sectorHeatmap" class="chart-container"></div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <!-- Historical Performance -->
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5>Historical Performance Analysis</h5>
                <select id="bondSelect" class="form-select form-select-sm" style="width: 200px; display: inline-block; margin-left: 20px;">
                    <option value="XS0000000001">GOV 2.5% 2030</option>
                    <option value="XS0000000002">CORP 3.2% 2028</option>
                </select>
            </div>
            <div class="card-body">
                <div id="historicalChart" class="chart-container"></div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <!-- Portfolio Analytics -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Portfolio Metrics</h5>
            </div>
            <div class="card-body">
                <table class="table">
                    <tr>
                        <td>Average Yield</td>
                        <td class="text-end"><strong>4.35%</strong></td>
                    </tr>
                    <tr>
                        <td>Average Duration</td>
                        <td class="text-end"><strong>7.2 years</strong></td>
                    </tr>
                    <tr>
                        <td>Average Credit Rating</td>
                        <td class="text-end"><strong>A+</strong></td>
                    </tr>
                    <tr>
                        <td>Total Return (YTD)</td>
                        <td class="text-end positive"><strong>+3.45%</strong></td>
                    </tr>
                    <tr>
                        <td>Sharpe Ratio</td>
                        <td class="text-end"><strong>1.23</strong></td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
    
    <!-- Risk Metrics -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Risk Analysis</h5>
            </div>
            <div class="card-body">
                <div id="riskChart" class="chart-container"></div>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    loadDurationYieldAnalysis();
    loadSectorHeatmap();
    loadHistoricalPerformance();
    loadRiskAnalysis();
});

function loadDurationYieldAnalysis() {
    $.get('/api/bonds', function(data) {
        const trace = {
            x: data.bonds.map(b => b.duration),
            y: data.bonds.map(b => b.yield_value),
            mode: 'markers',
            type: 'scatter',
            text: data.bonds.map(b => b.ticker),
            marker: {
                size: data.bonds.map(b => Math.log(b.issue_size) * 2),
                color: data.bonds.map(b => b.spread),
                colorscale: 'Viridis',
                showscale: true,
                colorbar: { title: 'Spread (bps)' }
            }
        };
        
        const layout = {
            title: 'Duration vs Yield (Size = Issue Size)',
            xaxis: { title: 'Duration (Years)' },
            yaxis: { title: 'Yield (%)' },
            hovermode: 'closest'
        };
        
        Plotly.newPlot('durationYieldChart', [trace], layout);
    });
}

function loadSectorHeatmap() {
    const sectors = ['Gov', 'Corp IG', 'Corp HY', 'Muni', 'Agency'];
    const periods = ['1D', '1W', '1M', '3M', 'YTD'];
    
    // Generate random performance data
    const z = sectors.map(() => 
        periods.map(() => (Math.random() * 4 - 2).toFixed(2))
    );
    
    const trace = {
        x: periods,
        y: sectors,
        z: z,
        type: 'heatmap',
        colorscale: 'RdYlGn',
        showscale: true,
        colorbar: { title: 'Return (%)' }
    };
    
    const layout = {
        title: 'Sector Performance',
        xaxis: { title: 'Period' },
        yaxis: { title: 'Sector' }
    };
    
    Plotly.newPlot('sectorHeatmap', [trace], layout);
}

function loadHistoricalPerformance() {
    $.get('/api/historical/XS0000000001', function(data) {
        const trace1 = {
            x: data.dates,
            y: data.yields,
            mode: 'lines',
            name: 'Yield',
            yaxis: 'y'
        };
        
        const trace2 = {
            x: data.dates,
            y: data.spreads,
            mode: 'lines',
            name: 'Spread',
            yaxis: 'y2',
            line: { color: 'orange' }
        };
        
        const layout = {
            title: 'Historical Yield and Spread',
            xaxis: { title: 'Date' },
            yaxis: { title: 'Yield (%)', side: 'left' },
            yaxis2: {
                title: 'Spread (bps)',
                overlaying: 'y',
                side: 'right'
            },
            hovermode: 'x unified'
        };
        
        Plotly.newPlot('historicalChart', [trace1, trace2], layout);
    });
}

function loadRiskAnalysis() {
    const risks = ['Duration Risk', 'Credit Risk', 'Liquidity Risk', 'FX Risk', 'Curve Risk'];
    const values = [65, 45, 30, 55, 40];
    
    const trace = {
        type: 'scatterpolar',
        r: values,
        theta: risks,
        fill: 'toself',
        name: 'Current Portfolio'
    };
    
    const layout = {
        title: 'Risk Profile',
        polar: {
            radialaxis: {
                visible: true,
                range: [0, 100]
            }
        }
    };
    
    Plotly.newPlot('riskChart', [trace], layout);
}

$('#bondSelect').change(function() {
    loadHistoricalPerformance();
});
</script>
{% endblock %}
'''

PREFERENCES_TEMPLATE = '''
{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>Client Preferences</h2>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Bond Preferences</h5>
            </div>
            <div class="card-body">
                <form id="preferencesForm">
                    <div class="mb-3">
                        <label class="form-label">Preferred Sectors</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="Government" id="sectorGov" checked>
                            <label class="form-check-label" for="sectorGov">Government</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="Corporate IG" id="sectorCorpIG" checked>
                            <label class="form-check-label" for="sectorCorpIG">Corporate IG</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="Corporate HY" id="sectorCorpHY">
                            <label class="form-check-label" for="sectorCorpHY">Corporate HY</label>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Duration Range</label>
                        <div class="row">
                            <div class="col">
                                <input type="number" class="form-control" id="durationMin" value="5" min="0" max="30">
                            </div>
                            <div class="col-auto">to</div>
                            <div class="col">
                                <input type="number" class="form-control" id="durationMax" value="10" min="0" max="30">
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Minimum Rating</label>
                        <select class="form-select" id="minRating">
                            <option value="AAA">AAA</option>
                            <option value="AA">AA</option>
                            <option value="A" selected>A</option>
                            <option value="BBB">BBB</option>
                            <option value="BB">BB</option>
                        </select>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Preferred Currencies</label>
                        <select class="form-select" multiple id="currencies">
                            <option value="USD" selected>USD</option>
                            <option value="EUR" selected>EUR</option>
                            <option value="GBP">GBP</option>
                            <option value="JPY">JPY</option>
                            <option value="CHF">CHF</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Save Preferences</button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Alert Settings</h5>
            </div>
            <div class="card-body">
                <form id="alertForm">
                    <div class="mb-3">
                        <label class="form-label">Yield Change Alert (basis points)</label>
                        <input type="number" class="form-control" id="yieldAlert" value="10" min="1" max="100">
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Spread Change Alert (basis points)</label>
                        <input type="number" class="form-control" id="spreadAlert" value="5" min="1" max="50">
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Price Change Alert (%)</label>
                        <input type="number" class="form-control" id="priceAlert" value="2" min="0.1" max="10" step="0.1">
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Alert Channels</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="emailAlert" checked>
                            <label class="form-check-label" for="emailAlert">Email</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="smsAlert">
                            <label class="form-check-label" for="smsAlert">SMS</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="dashboardAlert" checked>
                            <label class="form-check-label" for="dashboardAlert">Dashboard</label>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Save Alert Settings</button>
                </form>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5>Watchlist Management</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-8">
                        <input type="text" class="form-control" id="bondSearch" placeholder="Search bonds by ISIN or ticker...">
                    </div>
                    <div class="col-md-4">
                        <button class="btn btn-primary" onclick="searchBonds()">Search</button>
                    </div>
                </div>
                
                <div class="mt-3">
                    <h6>Current Watchlist</h6>
                    <div id="watchlistItems" class="list-group">
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            XS0000000001 - GOV 2.5% 2030
                            <button class="btn btn-sm btn-danger" onclick="removeFromWatchlist('XS0000000001')">Remove</button>
                        </div>
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            XS0000000002 - CORP 3.2% 2028
                            <button class="btn btn-sm btn-danger" onclick="removeFromWatchlist('XS0000000002')">Remove</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
$('#preferencesForm').submit(function(e) {
    e.preventDefault();
    
    const preferences = {
        sectors: $('input[type="checkbox"]:checked').map(function() {
            return $(this).val();
        }).get(),
        duration_range: [
            parseFloat($('#durationMin').val()),
            parseFloat($('#durationMax').val())
        ],
        min_rating: $('#minRating').val(),
        currencies: $('#currencies').val()
    };
    
    $.post('/api/preferences', preferences, function(response) {
        alert('Preferences saved successfully!');
    });
});

$('#alertForm').submit(function(e) {
    e.preventDefault();
    
    const alerts = {
        yield_change: parseInt($('#yieldAlert').val()),
        spread_change: parseInt($('#spreadAlert').val()),
        price_change: parseFloat($('#priceAlert').val()),
        channels: {
            email: $('#emailAlert').is(':checked'),
            sms: $('#smsAlert').is(':checked'),
            dashboard: $('#dashboardAlert').is(':checked')
        }
    };
    
    $.post('/api/alerts', alerts, function(response) {
        alert('Alert settings saved successfully!');
    });
});

function searchBonds() {
    const query = $('#bondSearch').val();
    // Implement bond search
    console.log('Searching for:', query);
}

function removeFromWatchlist(isin) {
    if (confirm('Remove this bond from watchlist?')) {
        $.ajax({
            url: '/api/watchlist/' + isin,
            type: 'DELETE',
            success: function() {
                location.reload();
            }
        });
    }
}
</script>
{% endblock %}
'''

# =======================
# API Routes
# =======================

@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE.replace('{% extends "base.html" %}', BASE_TEMPLATE.replace('{% block content %}{% endblock %}', DASHBOARD_TEMPLATE[30:])))

@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE.replace('{% extends "base.html" %}', BASE_TEMPLATE.replace('{% block content %}{% endblock %}', DASHBOARD_TEMPLATE[30:])))

@app.route('/analytics')
def analytics_page():
    return render_template_string(ANALYTICS_TEMPLATE.replace('{% extends "base.html" %}', BASE_TEMPLATE.replace('{% block content %}{% endblock %}', ANALYTICS_TEMPLATE[30:])))

@app.route('/preferences')
def preferences_page():
    return render_template_string(PREFERENCES_TEMPLATE.replace('{% extends "base.html" %}', BASE_TEMPLATE.replace('{% block content %}{% endblock %}', PREFERENCES_TEMPLATE[30:])))

@app.route('/api/bonds')
def get_bonds():
    """Get bond data"""
    # Generate mock bonds
    bonds = MockDataGenerator.generate_bonds(20)
    
    # Store in database
    with db_manager.get_db() as conn:
        for bond in bonds:
            conn.execute('''
                INSERT OR REPLACE INTO bonds 
                (isin, ticker, coupon, maturity, yield_value, spread, duration, rating, sector, currency, price, issue_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bond.isin, bond.ticker, bond.coupon, bond.maturity, bond.yield_value, 
                  bond.spread, bond.duration, bond.rating, bond.sector, bond.currency, 
                  bond.price, bond.issue_size))
        conn.commit()
    
    return jsonify({'bonds': [asdict(bond) for bond in bonds]})

@app.route('/api/yield-curve')
def get_yield_curve():
    """Get yield curve data"""
    curves = {}
    for currency in ['USD', 'EUR']:
        curves[currency] = analytics.generate_yield_curve(currency)
    return jsonify(curves)

@app.route('/api/historical/<isin>')
def get_historical_data(isin):
    """Get historical data for a bond"""
    df = MockDataGenerator.generate_historical_data(isin, 30)
    
    return jsonify({
        'dates': df['date'].dt.strftime('%Y-%m-%d').tolist(),
        'yields': df['yield_value'].tolist(),
        'spreads': df['spread'].tolist(),
        'prices': df['price'].tolist()
    })

@app.route('/api/preferences', methods=['POST'])
def save_preferences():
    """Save user preferences"""
    prefs = request.json
    user_id = session.get('user_id', 'default_user')
    
    with db_manager.get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO user_preferences (user_id, preferences)
            VALUES (?, ?)
        ''', (user_id, json.dumps(prefs)))
        conn.commit()
    
    return jsonify({'status': 'success'})

@app.route('/api/alerts', methods=['POST'])
def save_alerts():
    """Save alert settings"""
    alerts = request.json
    # In production, save to database
    return jsonify({'status': 'success'})

@app.route('/api/watchlist/<isin>', methods=['DELETE'])
def remove_from_watchlist(isin):
    """Remove bond from watchlist"""
    # In production, update user's watchlist in database
    return jsonify({'status': 'success'})

@app.route('/api/export/bonds')
def export_bonds():
    """Export bond data to CSV"""
    import csv
    import io
    from flask import make_response
    
    # Get bonds from database
    bonds = MockDataGenerator.generate_bonds(20)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['isin', 'ticker', 'sector', 'rating', 
                                                'maturity', 'yield_value', 'spread', 
                                                'duration', 'price'])
    writer.writeheader()
    for bond in bonds:
        writer.writerow(asdict(bond))
    
    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=bonds_export.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

# =======================
# WebSocket Support (Mock)
# =======================

@app.route('/api/stream')
def stream_updates():
    """Mock real-time updates endpoint"""
    import time
    from flask import Response
    
    def generate():
        while True:
            # Generate random update
            update = {
                'type': 'price_update',
                'isin': f'XS{random.randint(0, 49):010d}',
                'yield': round(random.uniform(2, 6), 3),
                'spread': random.randint(10, 300),
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(update)}\n\n"
            time.sleep(5)  # Update every 5 seconds
    
    return Response(generate(), mimetype="text/event-stream")

# =======================
# Main Entry Point
# =======================

if __name__ == '__main__':
    # Initialize database with sample data
    print("Initializing Fixed Income Analytics Dashboard...")
    print("Access the application at: http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  - Dashboard: http://localhost:5000/dashboard")
    print("  - Analytics: http://localhost:5000/analytics")
    print("  - Preferences: http://localhost:5000/preferences")
    print("\nAPI Endpoints:")
    print("  - GET  /api/bonds - Get bond data")
    print("  - GET  /api/yield-curve - Get yield curve data")
    print("  - GET  /api/historical/<isin> - Get historical data")
    print("  - POST /api/preferences - Save preferences")
    print("  - GET  /api/export/bonds - Export to CSV")
    
    app.run(debug=True, port=5000)