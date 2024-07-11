# INCORE-Gallery

This repository contains a Python script that uses the Zenodo API to search for Jupyter Notebooks or ZIP files, download them, and create a Jupyter Book.

## Prerequisites

- Python 3.x
- `virtualenv` package

## Setup

### 1. Clone the Repository and Set Up the Virtual Environment

#### On Windows

```commandline
git clone https://github.com/IN-CORE/incore-gallery/incore-gallery.git
cd incore-gallery
python -m venv \path\to\incore-gallery\venv
\path\to\incore-garrery\venv\Scripts\activate
pip install -r requirements.txt
```

#### On macOS and Linux
```bash
git clone https://github.com/IN-CORE/incore-gallery/incore-gallery.git
cd incore-gallery
python -m venv /path/to/incore-gallery/venv
source /path/to/incore-gallery/venv/activate
pip install -r requirements.txt
```