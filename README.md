# 🏢 Agent Office

**Social Network Information Spread Simulation**

A comprehensive simulation system that models how information (including misinformation) spreads through a social network, complete with agent-based behaviors, ML pipeline for detection, and interactive visualizations.

## 📋 Overview

Agent Office simulates a telephone-game-like environment where:

- **13+ diverse agents** interact in a social network (Immediate Sharers, Cautious Sharers, Skeptics, Influencers, Lurkers)
- **Posts** with characteristics (truth value, emotional intensity, credibility) spread through the network
- **Behaviors** differ based on agent type: some share immediately, others verify, skeptics flag suspicious content
- **ML Pipeline** generates datasets and trains classifiers to detect misinformation

## ✨ Features

- 🧠 **Agent-Based Simulation** - Diverse user behaviors with realistic spreading patterns
- 📊 **Early Dissemination Tracking** - 38+ features captured for ML analysis
- 🤖 **ML Pipeline** - Logistic Regression + SVM with 20-epoch training
- 📈 **Model Comparison** - Visual comparison with ASCII charts
- 🖥️ **TUI Application** - Interactive terminal interface
- 📟 **Terminal Visualization** - Real-time ASCII network display
- 💾 **Data Export** - CSV, JSONL, JSON formats for further ML work

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+ required
python3 --version
```

### Installation

```bash
cd zed-base
# No external dependencies required (uses stdlib only)
```

### Running the Application

#### 1. TUI Application (Recommended)

```bash
python3 run_tui.py
```

Interactive menu with:
- **Run Simulation** - Watch posts spread through the network
- **Train & Compare Models** - Generate 500+ samples, train LR+SVM, view comparison
- **View Model Results** - ASCII charts of training history

#### 2. ML Pipeline (Headless)

```bash
python3 run_pipeline.py
```

Generates 500+ training samples, trains models for 20 epochs, outputs:
- `output/training_data.csv`
- `output/model_comparison_*.json`
- `output/training_history_*.json`

#### 3. Terminal Visualization

```bash
python3 run_terminal_viz.py
```

Real-time ASCII visualization (no curses needed).

#### 4. Simple Simulation

```bash
python3 run.py
```

Basic simulation with JSON logging to `output/`.

## 📁 Project Structure

```
zed-base/
├── agent_office/
│   ├── __init__.py          # Package exports
│   ├── agent.py             # Agent types & behaviors
│   ├── post.py              # Post characteristics
│   ├── network.py           # Social network graph
│   ├── simulation.py        # Simulation engine
│   ├── logger.py            # Terminal + JSON logging
│   ├── pipeline.py          # Data generation pipeline
│   ├── tui_app.py           # Full TUI application
│   ├── terminal_viz.py      # Simple terminal viz
│   ├── visualization.py     # GUI (tkinter, optional)
│   └── ml/
│       ├── data_collector.py    # Early dissemination tracking
│       ├── feature_extractor.py # 38 ML features
│       ├── dataset_builder.py   # CSV/JSONL/JSON export
│       └── ml_pipeline.py       # LR + SVM training
├── output/                  # Generated datasets & models
├── run_tui.py              # TUI runner
├── run_pipeline.py         # ML pipeline runner
├── run_terminal_viz.py     # Terminal viz runner
└── run.py                  # Basic simulation runner
```

## 📊 ML Features (38 total)

### Post Features (11)
- Category (one-hot: news, gossip, entertainment, politics, science, health)
- Emotional intensity, Credibility score, Source reliability
- Derived: emotional_credibility_gap, sensationalism_score

### Spread Features (27)
- Early reach, shares, flags, ignores, verifications
- Rates: share_rate, flag_rate, verification_rate
- Velocity, acceleration metrics
- Agent type involvement (immediate_shares, cautious_shares, etc.)
- Timing: first_share_tick, first_flag_tick, time_to_first_flag
- Trust metrics

## 📈 Sample Results

```
MODEL COMPARISON RESULTS
========================

Logistic Regression:
  Accuracy:  83.0%
  Precision: 84.1%
  Recall:    85.5%
  F1 Score:  84.8%
  AUC-ROC:   90.0%

SVM:
  Accuracy:  81.2%
  Precision: 100.0%
  Recall:    66.1%
  F1 Score:  79.6%
  AUC-ROC:   99.9%

Best Model: Logistic Regression
```

## 🎮 TUI Controls

| Key | Action |
|-----|--------|
| ↑↓ | Navigate menu |
| Enter | Select option |
| Space | Run simulation step |
| R | Reset simulation |
| T | Train models |
| Q | Return/Quit |

## 📝 Agent Types

| Type | Symbol | Behavior |
|------|--------|----------|
| Immediate Sharer | 🔴 | Shares without verification |
| Cautious Sharer | 🟢 | Verifies before sharing |
| Skeptic | 🔵 | High skepticism, rarely shares |
| Influencer | 🟡 | High network influence |
| Lurker | ⚪ | Reads but rarely shares |

## 🔮 Future Work (Not Implemented)

- ML Pipeline enhancements (more models)
- Advanced visualizations (matplotlib)
- NetworkX integration
- Web-based dashboard

## 📄 License

MIT License

## 👥 Authors

Okan Dogan
