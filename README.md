# 🌍 Nutrition Paradox
## A Global View on Obesity and Malnutrition (WHO Data Analysis)
### 📖 About the Project

Nutrition Paradox is an end-to-end data analytics dashboard that explores the global coexistence of two major public health challenges:

* Rising Obesity

* Persistent Malnutrition

Using data from the World Health Organization (WHO) Global Health Observatory (GHO) API, this project performs automated data extraction, transformation, storage in MySQL, and interactive visualization through Streamlit.

The project highlights the paradox where countries simultaneously experience overnutrition and undernutrition.

### 🔨 Development Process

The project follows a complete ETL + Analytics Pipeline:

#### 1. Data Extraction

Data fetched from WHO GHO API endpoints:

* `NCD_BMI_30C (Adult Obesity)`

* `NCD_BMI_PLUS2C (Child Obesity)`

* `NCD_BMI_18C (Adult Malnutrition)`

* `NCD_BMI_MINUS2C (Child Malnutrition)`

#### 2. Data Transformation

* Year filtering (2012–2022)
* Country code conversion using pycountry
* Gender code cleaning
* Outlier removal using IQR
* Confidence Interval width calculation
* Obesity & malnutrition categorization

#### 3. Database Storage

* MySQL database creation
* Table creation
* Processed data insertion

#### 4. Visualization & Dashboard

* Multi-page Streamlit dashboard
* SQL-driven analytics
* Interactive Plotly visualizations

### ✨ Key Features

* 🌍 Global obesity & malnutrition comparison

* 📊 Year-wise trend analysis

* 👨‍👩‍👧 Gender-based disparity analysis

* 📈 Region-wise ranking

* 🧮 Confidence Interval reliability scoring

* 🔄 Combined obesity vs malnutrition analytics

* 📉 Outlier removal using statistical method (IQR)

* 🗄 SQL-based backend queries

* 📊 Interactive charts using Plotly

### ⚙️ Tech Stack

| Category        | Tools Used    |
| --------------- | ------------- |
| Language        | Python        |
| Framework       | Streamlit     |
| Database        | MySQL         |
| ORM             | SQLAlchemy    |
| Data Processing | Pandas, NumPy |
| Visualization   | Plotly        |
| API             | WHO GHO API   |
| Country Mapping | PyCountry     |

### 📋 Project Overview

The dashboard contains three main sections:

**1️⃣ Obesity Analysis**

* Top 5 Regions by Average Obesity
* Highest Obesity Countries
* Gender-based Obesity
* Country Reliability (CI Width)
* Age Group Comparison
* Global Obesity Trends

**2️⃣ Malnutrition Analysis**

* Age-wise Malnutrition
* Region Ranking
* Year-wise Change (India, Nigeria, Brazil)
* Countries with Increasing Malnutrition
* CI Width Monitoring Flags

**3️⃣ Combined Analysis**

* Obesity vs Malnutrition by Country
* Gender-based Disparity
* Regional Average Comparison
* Trend-based paradox analysis

### 🎯 Features:

* Automatic database creation
* Automatic API fetch (only if DB is empty)
* Multi-page navigation
* Sidebar filters
* SQL window functions (RANK)
* Advanced queries with CTE
* Confidence Interval reliability analysis
* Country name standardization
* Clean UI with interactive plots

### ⚙️ Setup & Installation

**1️⃣ Clone the Repository**
```
git clone https://github.com/your-username/nutrition-paradox.git
cd nutrition-paradox
```
**2️⃣ Install Required Packages**

`pip install -r requirements.txt`

Or manually:

`pip install streamlit pandas numpy plotly sqlalchemy mysql-connector-python pycountry requests`

**3️⃣ Configure MySQL**

Make sure MySQL is running.

Update your connection string in the script:

`create_engine("mysql+mysqlconnector://root:your_password@localhost")`

**4️⃣ Run the Application**

`streamlit run app.py`

### 📊 Dataset Setup

This project uses live data from the WHO Global Health Observatory API.

Endpoints Used:

* Obesity (Adults)
* Obesity (Children)
* Malnutrition (Adults)
* Malnutrition (Children)

Data is automatically:

* Pulled from API
* Cleaned
* Transformed
* Stored in MySQL

No manual dataset download required.

### 🔄 How It Works

1. Application starts.
2. Checks if MySQL tables contain data.
3. If empty → Fetches data from WHO API.
4. Applies:

    * Cleaning
    * Outlier removal
    * Feature engineering

5. Inserts into MySQL.
6. User selects analysis topic.
7. SQL queries run dynamically.
8. Plotly visualizes the results interactively.

### 🎯 Use Case

* This project can be used for:
* Public Health Research
* Policy Analysis
* Academic Study
* Data Science Portfolio
* WHO health trend exploration
* Understanding global nutrition paradox
It demonstrates how countries can simultaneously face:
* High obesity rates
* High malnutrition rates

### 🚀 Future Enhancements

* Add user-based filtering (country/year/gender)
* Add machine learning prediction models
* Deploy on Streamlit Cloud / AWS
* Add real-time API refresh button
* Add correlation heatmaps
* 8Add export to CSV / PDF feature
* Add authentication system
* Add Docker support
* Improve UI theme customization
* Add KPI summary cards

## 📌 Author
```
Saran K
Data Analytics & Visualization Enthusiast
Capstone Project – Global Health Data Analysis
```
## ⭐ If You Like This Project

```
Give it a ⭐ on GitHub and feel free to fork it!
```
