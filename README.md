# 📘 Catalogue Automation

This project automates the creation of a **product catalogue in PDF format** from Excel spreadsheets containing product data and image links.  
It downloads, optimizes, and crops product images, generates a well-structured catalogue with covers, and produces CSV reports summarizing which products were included or excluded.

---

## 🚀 Features

- Load product data from Excel spreadsheets.
- Download and optimize product images (resizing, cropping borders, removing subtitles).
- Cache and reuse previously optimized images.
- Build a professional PDF catalogue grouped by categories and families.
- Generate CSV reports:
  - **Full report**: all SKUs with a flag indicating whether they were included in the catalogue.
  - **Missing report** (optional): products without valid images.
- Logging system for debugging and auditing.

---

## 📂 Project Structure

```
CATALOGUE-AUTOMATION/
│
├── data/                  # Input Excel spreadsheets and other resources
├── logs/                  # Generated log files
├── src/                   # Source code
│   ├── main.py            # Main pipeline entrypoint
│   ├── run.py             # Script to run the project
│   ├── pdf_builder.py     # Catalogue PDF generator
│   │
│   └── utils/             # Utility modules
│       ├── excel.py       # Excel loading and preprocessing
│       ├── images.py      # Image download, optimization, and cropping
│       ├── logger.py      # Logging configuration
│       └── __init__.py
│
├── requirements.txt       # Python dependencies
├── run.spec               # PyInstaller spec (for packaging as executable)
└── README.md              # Project documentation
```

---

## ⚙️ Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/catalogue-automation.git
   cd catalogue-automation
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate   # (Linux/Mac)
   venv\Scripts\activate      # (Windows)

   pip install -r requirements.txt
   ```

---

## ▶️ Usage

1. Place your **product Excel file** and **image links Excel file** inside the `data/` folder.

2. Run the pipeline:
   ```bash
   python src/run.py
   ```

3. The script will:
   - Process the product list.
   - Download and optimize images.
   - Generate the catalogue PDF in the project folder.
   - Save CSV reports about included and missing products.

---

## 📝 Reports

- `*_relatorio.csv` → All SKUs with a `YES/NO` flag indicating if they were included in the catalogue.
- `*_sem_imagem.csv` → (Optional) Products excluded because of missing images.

---

## 🛠 Tech Stack

- **Python 3.12+**
- [Pandas](https://pandas.pydata.org/) – data manipulation  
- [Pillow (PIL)](https://python-pillow.org/) – image processing  
- [ReportLab](https://www.reportlab.com/) – PDF generation  
- [Requests](https://requests.readthedocs.io/) – HTTP image download  

---

## 📌 Notes

- All images are normalized to square format (default `600x600px`).
- Logs are stored under `/logs` with timestamps for debugging.
- You can package this project as an executable using the `run.spec` file with **PyInstaller**.

---

## 📄 License

MIT License – feel free to use and adapt.
