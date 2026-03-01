import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import requests
import pycountry
from sqlalchemy import create_engine, text
import plotly.graph_objects as go

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    layout="wide",
    page_title="Nutrition Paradox",
    page_icon="⚖️"
)

st.title("🌍 A Global View on Obesity and Malnutrition")

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "page" not in st.session_state:
    st.session_state.page = "home"

# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

engine = create_engine("mysql+mysqlconnector://root:0007@localhost")

with engine.connect() as conn:
    conn.execute(text("CREATE DATABASE IF NOT EXISTS Nutrition_Paradox"))
    conn.commit()

db_engine = create_engine(
    "mysql+mysqlconnector://root:0007@localhost/Nutrition_Paradox"
)

# --------------------------------------------------
# CREATE TABLES
# --------------------------------------------------

create_obesity_table = """
CREATE TABLE IF NOT EXISTS obesity (
    Country VARCHAR(255),
    Region VARCHAR(255),
    Gender VARCHAR(255),
    Year INT,
    Mean_Estimate FLOAT,
    LowerBound FLOAT,
    UpperBound FLOAT,
    Age_Group VARCHAR(255),
    CI_Width FLOAT,
    Obesity_level VARCHAR(255)
);
"""

create_malnutrition_table = """
CREATE TABLE IF NOT EXISTS malnutrition (
    Country VARCHAR(255),
    Region VARCHAR(255),
    Gender VARCHAR(255),
    Year INT,
    Mean_Estimate FLOAT,
    LowerBound FLOAT,
    UpperBound FLOAT,
    Age_Group VARCHAR(255),
    CI_Width FLOAT,
    Malnutrition_level VARCHAR(255)
);
"""

with db_engine.connect() as conn:
    conn.execute(text(create_obesity_table))
    conn.execute(text(create_malnutrition_table))
    conn.commit()

# --------------------------------------------------
# API FUNCTION
# --------------------------------------------------

@st.cache_data
def fetch_data():

    urls = {
        "Obesity_adults": "https://ghoapi.azureedge.net/api/NCD_BMI_30C",
        "Obesity_children": "https://ghoapi.azureedge.net/api/NCD_BMI_PLUS2C",
        "Malnutrition_adults": "https://ghoapi.azureedge.net/api/NCD_BMI_18C",
        "Malnutrition_children": "https://ghoapi.azureedge.net/api/NCD_BMI_MINUS2C"
    }

    dataframes = {}

    for key, url in urls.items():
        response = requests.get(url, timeout=30)
        data = response.json()
        df = pd.DataFrame(data.get("value", []))
        df["Age_Group"] = "Adults" if "adults" in key else "Children"
        dataframes[key] = df

    return dataframes
# --------------------------------------------------
# GLOBAL SIDEBAR (VISIBLE ON ALL PAGES)
# --------------------------------------------------

# st.sidebar.title("🔎 Global Filters")

# years_query = pd.read_sql(
#     "SELECT DISTINCT Year FROM obesity ORDER BY Year",
#     db_engine
# )

# years = years_query["Year"].tolist()

# if years:
#     st.session_state.selected_year = st.sidebar.selectbox(
#         "Select Year",
#         years,
#         index=len(years)-1
#     )
# else:
#     st.sidebar.warning("No data available yet")

# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------
if st.session_state.page == "home":
    # -------------------------------------------------
    # CHECK IF DATA EXISTS
    # --------------------------------------------------
    with db_engine.connect() as conn:
        obesity_count = conn.execute(text("SELECT COUNT(*) FROM obesity")).scalar()
        malnutrition_count = conn.execute(text("SELECT COUNT(*) FROM malnutrition")).scalar()
        
    # --------------------------------------------------
    # RUN ETL ONLY IF EMPTY
    # --------------------------------------------------
    if obesity_count == 0 and malnutrition_count == 0:
        
        st.info("Fetching data from WHO API...")
        dataframes = fetch_data()
        dataframes=''
        Obesity_df = pd.concat(
            [dataframes["Obesity_adults"], dataframes["Obesity_children"]],
            ignore_index=True)
        Malnutrition_df = pd.concat(
            [dataframes["Malnutrition_adults"], dataframes["Malnutrition_children"]],
            ignore_index=True)
        
        # ------------------ YEAR FILTER ------------------
        Obesity_df = Obesity_df[
            (Obesity_df["TimeDimensionValue"] >= "2012") &
            (Obesity_df["TimeDimensionValue"] <= "2022")]
        
        Malnutrition_df = Malnutrition_df[
            (Malnutrition_df["TimeDimensionValue"] >= "2012") &
            (Malnutrition_df["TimeDimensionValue"] <= "2022")]
        
        # ------------------ SELECT REQUIRED COLUMNS ------------------
         
        required_cols = [
            "ParentLocation","Dim1","TimeDim","Low","High",
            "NumericValue","SpatialDim","Age_Group"]
        
        Obesity_df = Obesity_df[required_cols]
        Malnutrition_df = Malnutrition_df[required_cols]
        
        # ------------------ RENAME ------------------
        
        rename_cols = {
            "SpatialDim":"Country",
            "ParentLocation":"Region",
            "TimeDim":"Year",
            "Dim1":"Gender",
            "NumericValue":"Mean_Estimate",
            "Low":"LowerBound",
            "High":"UpperBound"
            }
        
        Obesity_df.rename(columns=rename_cols, inplace=True)
        Malnutrition_df.rename(columns=rename_cols, inplace=True)
        
        # ------------------ GENDER CLEAN ------------------
        
        gender_map = {"SEX_BTSX":"Both","SEX_MLE":"Male","SEX_FMLE":"Female"}
        
        Obesity_df["Gender"] = Obesity_df["Gender"].replace(gender_map)
        Malnutrition_df["Gender"] = Malnutrition_df["Gender"].replace(gender_map)
        
        # ------------------ COUNTRY CONVERSION ------------------
         
        special_code = {"GLOBAL":"Global",
                        "WB_LMI":"Low & Middle Income",
                        "WB_HI":"High Income",
                        "WB_LI":"Low Income",
                        "EMR":"Eastern Mediterranean Region",
                        "EUR":"Europe",
                        "AFR":"Africa",
                        "SEAR":"South-East Asia Region",
                        "WPR":"Western Pacific Region",
                        "AMR":"Americas Region",
                        "WB_UMI":"Upper Middle Income"}
        def convert_country(code):
            country = pycountry.countries.get(alpha_3=str(code))
            if country:
                return country.name
            return special_code.get(code, code)
        Obesity_df["Country"] = Obesity_df["Country"].apply(convert_country)
        Malnutrition_df["Country"] = Malnutrition_df["Country"].apply(convert_country)
        
        # ------------------ OUTLIER REMOVAL (IQR) ------------------
         
        def remove_outliers_iqr(df, column):
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            return df[(df[column] >= lower) & (df[column] <= upper)]
        
        for col in ["Mean_Estimate","LowerBound","UpperBound"]:
            Obesity_df = remove_outliers_iqr(Obesity_df, col)
        for col in ["Mean_Estimate","LowerBound","UpperBound"]:
            Malnutrition_df = remove_outliers_iqr(Malnutrition_df, col)
            
        # ------------------ FEATURE ENGINEERING ------------------
          
        Obesity_df["CI_Width"] = Obesity_df["UpperBound"] - Obesity_df["LowerBound"]
        Malnutrition_df["CI_Width"] = Malnutrition_df["UpperBound"] - Malnutrition_df["LowerBound"]
        
        Obesity_df["Obesity_level"] = np.select([
            Obesity_df["Mean_Estimate"] <= 25,
            (Obesity_df["Mean_Estimate"] > 25) & (Obesity_df["Mean_Estimate"] < 30),
            Obesity_df["Mean_Estimate"] >= 30],
            ["Low","Moderate","High"],
            default="Unclassified")
        
        Malnutrition_df["Malnutrition_level"] = np.select([
            Malnutrition_df["Mean_Estimate"] <= 10,
            (Malnutrition_df["Mean_Estimate"] > 10) & (Malnutrition_df["Mean_Estimate"] < 20),
            Malnutrition_df["Mean_Estimate"] >= 20],
            ["Low","Moderate","High"],
            default="Unclassified")
        
        # ------------------ FINAL CLEAN ------------------
        
        Obesity_df.fillna("Unknown", inplace=True)
        Malnutrition_df.fillna("Unknown", inplace=True)
        
        Obesity_df.reset_index(drop=True, inplace=True)
        Malnutrition_df.reset_index(drop=True, inplace=True)
        
        # ------------------ INSERT ------------------
        
        Obesity_df.to_sql("obesity", db_engine, if_exists="append", index=False)
        Malnutrition_df.to_sql("malnutrition", db_engine, if_exists="append", index=False)
        
        st.success("Data inserted into MySQL successfully ✅")
        
    else:
        st.success("Database already contains data. API skipped ✅")

    st.subheader("📊 Analysis Dashboard")
    st.markdown("""
     <style>

/* Button size */
div.stButton > button {
    height: 150px;
    width: 260px;
    border-radius: 15px;
}

/* 🔥 Target inner text */
div.stButton > button p {
    font-size: 22px !important;
    font-weight: bold!important;
}

/* Normal background */
div.stButton > button {
    background: linear-gradient(135deg, #ffffff, #d1d9ff);
    padding: 9px 15px;
    transition: all 0.3s ease-in-out;
}

/* Hover effect */
div.stButton > button:hover {
    background: linear-gradient(
        135deg,
        rgba(230,230,250,0.6),
        rgba(173,216,230,0.45)
    );
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    color: Blue;
    border-color: blue;
    transform: scale(1.05);
    box-shadow: 0px 0px 8px #1e90ff;
}

</style>
""", unsafe_allow_html=True)

    col1, col2, col3,col4,col5 = st.columns([1,1.5,1.5,1.5,1])

    with col2:
        if st.button("Obesity Analysis"):
            st.session_state.page = "Obesity Analysis"
            st.rerun()
    with col4:
        if st.button("Obesity VS Malnutrition"):
            st.session_state.page = "Combined Analysis"
            st.rerun()
    with col3:
        if st.button("Malnutrition Analysis"):
            st.session_state.page = "Malnutrition Analysis"
            st.rerun() 
# --------------------------------------------------
# Obesity Analysis DASHBOARD
# --------------------------------------------------
elif st.session_state.page == "Obesity Analysis":

    st.header('Obesity Data')

    query="""SELECT * FROM obesity"""
    df = pd.read_sql(query, db_engine)
    st.dataframe(df, use_container_width=True)

    topic = st.sidebar.selectbox(
        "Choose Topic",
        [
            "— Select Topic —",
            "Top 5 Regions by Average Obesity",
            "Highest obesity estimates",
            "Obesity trend",
            "Obesity by gender",
            "Country count by obesity level",
            "Top 5 least and Most countries",
            "obesity by age group",
            "Top 10 Countries with low obesity",
            "obesity female vs male",
            "obesity percentage per year"
        ])

    if topic == "— Select Topic —":
        st.sidebar.info("👆 Please select a topic")
        if st.sidebar.button("⬅ Back to Home"):
            st.session_state.page = "home"
            st.rerun()    
        st.stop()

    if topic == "Top 5 Regions by Average Obesity":
        st.session_state.page = "top5"
        st.rerun()
    
    if topic == "Highest obesity estimates":
        st.session_state.page = "Highest obesity estimates"
        st.rerun()

    if topic == "Obesity trend":
        st.session_state.page = "Obesity trend"
        st.rerun()

    if topic == "Obesity by gender":
        st.session_state.page = "Obesity by gender"
        st.rerun()

    if topic == "Country count by obesity level":
        st.session_state.page = "Country count by obesity level"
        st.rerun()

    if topic == "Top 5 least and Most countries":
        st.session_state.page = "Top 5 least and Most countries"
        st.rerun()

    if topic == "obesity by age group":
        st.session_state.page = "obesity by age group"
        st.rerun()

    if topic == "Top 10 Countries with low obesity":
        st.session_state.page = "Top 10 Countries with low obesity"
        st.rerun()

    if topic == "obesity female vs male":
        st.session_state.page = "obesity female vs male"
        st.rerun()

    if topic == "obesity percentage per year":
        st.session_state.page = "obesity percentage per year"
        st.rerun()

# --------------------------------------------------
# Obesity Query 1
# --------------------------------------------------
elif st.session_state.page == "top5":

    st.subheader("1. Top 5 Regions by Average Obesity")

    st.sidebar.title("🔎 Top 5 Filters")

    years_query = pd.read_sql(
        "SELECT DISTINCT Year FROM obesity ORDER BY Year",
        db_engine
    )

    if years_query.empty:
        st.warning("No data available.")
        st.stop()

    years = years_query["Year"].tolist()

    selected_year = st.sidebar.selectbox(
        "Select Year",
        years,
        index=len(years)-1,
        key="top5_year"
    )

    st.session_state.selected_year = selected_year

    query = f"""
    SELECT Region,
           ROUND(AVG(Mean_Estimate),2) AS avg_obesity
    FROM obesity
    WHERE Year = {selected_year}
    GROUP BY Region
    ORDER BY avg_obesity DESC
    LIMIT 5;
    """

    df = pd.read_sql(query, db_engine)

    if df.empty:
        st.warning("No records found for selected year.")
        st.stop()


    st.dataframe(df, use_container_width=True)

    fig = px.histogram(data_frame=df,x="Region",y="avg_obesity",color="Region",
        title=f"Regions Vs Average Obesity ({selected_year})")
    fig.update_layout(title_x=0.3,title_font=dict(size=30),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig, use_container_width=True)

    if st.sidebar.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()

# --------------------------------------------------
# Obesity Query 2
# --------------------------------------------------

elif st.session_state.page == "Highest obesity estimates":

    st.subheader("2. Top 5 countries with highest obesity estimates")

    query = f"""
    SELECT Country,
    ROUND(AVG(Mean_Estimate),2) AS avg_obesity
    FROM obesity
    GROUP BY Country
    ORDER BY avg_obesity DESC
    LIMIT 5;
    """

    df = pd.read_sql(query, db_engine)
    st.dataframe(df, use_container_width=True)

    fig = px.histogram(data_frame=df,x="Country",y="avg_obesity",color="Country"
                 ,title=f"Country Vs Average Obesity")
    fig.update_layout(title_x=0.3,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig, use_container_width=True)

    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()

# --------------------------------------------------
# Obesity Query 3
# --------------------------------------------------
elif st.session_state.page == "Obesity trend":
    st.subheader("3. Obesity trend in India over the years(Mean_estimate)")
    query = f"""SELECT Year,
    ROUND(AVG(Mean_Estimate),2) AS India_obesity
    FROM obesity
    WHERE Country = 'India'
    GROUP BY Year
    ORDER BY Year;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.area(data_frame=df,x="Year",y="India_obesity",title="Year Vs India Obesity",markers=True)
    fig.update_traces(
    marker=dict(size=10, symbol="circle"))
    fig.update_layout(title_x=0.4,title_font=dict(size=40),
                          width=500,     # increase width
                          height=550  ,    # increase height
                              hoverlabel=dict(
                              bgcolor="#FA5E5E",
                              font_size=14,
                              font_color="White"))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 4
# --------------------------------------------------
elif st.session_state.page == "Obesity by gender":
    st.subheader("4. Average obesity by gender")

    query = f"""SELECT Gender,
       ROUND(AVG(Mean_Estimate),2) AS Avg_obesity
       FROM obesity
       GROUP BY Gender
       ORDER BY avg_obesity DESC;"""
    
    df= pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.pie(df, values='Avg_obesity', names='Gender',title="Gender Vs Avg Obesity")
    fig.update_layout(title_x=0.32,title_font=dict(size=45),
                      width=800,
                      height=650,
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))
    fig.update_traces(textposition='inside', textinfo='percent+label')

    st.plotly_chart(fig, use_container_width=True)
    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 5
# --------------------------------------------------
elif st.session_state.page == "Country count by obesity level":
    st.subheader("5. Country count by obesity level category and age group")

    query = f"""SELECT Age_Group,
       Obesity_Level,
       COUNT(DISTINCT Country) AS country_count
       FROM obesity
       GROUP BY Age_Group, Obesity_Level
       ORDER BY Age_Group, Obesity_Level;"""
    
    df= pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x="Obesity_Level",y="country_count",color="Age_Group",barmode="group",title="Country Vs Age Group")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig, use_container_width=True)

    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 6
# --------------------------------------------------
elif st.session_state.page == "Top 5 least and Most countries":
    st.subheader("6. Top 5 countries least reliable countries and Top 5 most consistent countries")

    query =f"""WITH ranked AS (
    SELECT Country,
           AVG(CI_Width) AS Avg_ci_Width,
           RANK() OVER (ORDER BY AVG(CI_Width) DESC) AS least_rank,
           RANK() OVER (ORDER BY AVG(CI_Width) ASC)  AS consistent_rank
    FROM obesity
    GROUP BY Country)
    SELECT Country, Avg_ci_Width, 'Least Reliable' AS Type
    FROM ranked
    WHERE least_rank <= 5
    UNION ALL
    SELECT Country, Avg_ci_Width, 'Most Consistent' AS Type
    FROM ranked
    WHERE consistent_rank <= 5;"""

    df= pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x="Country",y="Avg_ci_Width",color="Type",title="Country Vs Ci Width")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig, use_container_width=True)

    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 7
# --------------------------------------------------
elif st.session_state.page == "obesity by age group":
    st.subheader("7. Average obesity by age group")

    query = f"""SELECT Age_Group,
       ROUND(AVG(Mean_Estimate),2) AS Avg_obesity
       FROM obesity
       GROUP BY Age_Group;"""
    
    df= pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    # Top_10_df = df["Age_Group"]

    # fig = px.pie(data_frame=df,values="avg_obesity",names="Age_Group")
    # fig.update_traces(textposition='inside', textinfo='percent+label')
    colors = ['gold', 'mediumturquoise']
    fig = go.Figure(data=[go.Pie(labels=df["Age_Group"],
                             values=df["Avg_obesity"],hole=0.5)])
    fig.update_traces(hoverinfo='label+percent', textinfo='value', textfont_size=20,
                  marker=dict(colors=colors, line=dict(color='#000000', width=2)))
    fig.update_layout(title=dict(text="Age Group VS Avg Obesity",x=0.48, xanchor="center"),title_font=dict(size=40),
                          width=600,     # increase width
                          height=600  ,    # increase height
                          hoverlabel=dict(
                              bgcolor="#5EFABE",   # Background color
                              font_size=14,
                              font_color="black"))
 
    st.plotly_chart(fig, use_container_width=True)
    
    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 8
# --------------------------------------------------
elif st.session_state.page == "Top 10 Countries with low obesity":
    st.subheader("8. Top 10 Countries with consistent low obesity over the years")

    query = f"""SELECT 
    Country,
    ROUND(AVG(Mean_Estimate),2) AS Avg_obesity,
    ROUND(AVG(CI_Width),2) AS Avg_ci_width
    FROM obesity
    GROUP BY Country
    HAVING AVG(Mean_Estimate) < 25   
    ORDER BY avg_obesity ASC, Avg_ci_width ASC
    LIMIT 10;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.histogram(data_frame=df,x="Country",y="Avg_obesity",color="Avg_ci_width",title="Avg Obesity Vs Ci width")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))


    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 9
# --------------------------------------------------
elif st.session_state.page == "obesity female vs male":
    st.subheader("9. Countries where female obesity exceeds male by large margin")

    query = f"""SELECT 
    f.Country,
    f.Year,
    ROUND(f.Mean_Estimate,2) AS female_obesity,
    ROUND(m.Mean_Estimate,2) AS male_obesity,
    ROUND(f.Mean_Estimate - m.Mean_Estimate,2) AS Gender_gap
    FROM obesity f
    JOIN obesity m
    ON f.Country = m.Country
    AND f.Year = m.Year
    AND f.Age_Group = m.Age_Group   -- important if dataset has age groups
    WHERE f.Gender = 'Female'
    AND m.Gender = 'Male'
    AND (f.Mean_Estimate - m.Mean_Estimate) > 5
    ORDER BY Gender_gap DESC;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x="Country",y="Gender_gap",color="Gender_gap",title="Countries Vs Gender Gap",
                 color_continuous_scale="Reds")
    
    fig.update_layout(title_x=0.3,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig,use_container_width=True)

    
    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()
# --------------------------------------------------
# Obesity Query 10
# --------------------------------------------------
elif st.session_state.page == "obesity percentage per year":
    st.subheader("10. Global average obesity percentage per year")

    query =  f"""SELECT Year,
       ROUND(AVG(Mean_Estimate),2) AS Global_avg_obesity
       FROM obesity
       GROUP BY Year
       ORDER BY Year;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.line(data_frame=df,x="Year",y="Global_avg_obesity",markers=True,title="Year Vs Global Obesity")

    fig.update_traces(
    marker=dict(size=10, symbol="circle"))
    fig.update_layout(title_x=0.4,title_font=dict(size=40),
                          width=500,     # increase width
                          height=550  ,    # increase height
                              hoverlabel=dict(
                              bgcolor="#FA5E5E",
                              font_size=14,
                              font_color="White"))
    

    st.plotly_chart(fig,use_container_width=True)
    
    
    if st.button("⬅ Back to Obesity Analysis"):
        st.session_state.page = "Obesity Analysis"
        st.rerun()

#--------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------
# Malnutrition Analysis DASHBOARD
# --------------------------------------------------
elif st.session_state.page == "Malnutrition Analysis":

    st.header('Malnutrition Data')

    query="""SELECT * FROM malnutrition"""
    df = pd.read_sql(query, db_engine)
    st.dataframe(df, use_container_width=True)
    
    topic = st.sidebar.selectbox(
        "Choose Topic",
        [
            "— Select Topic —",
            "Malnutrition by age group",
            "Top 5 countries with highest malnutrition",
            "Malnutrition trend",
            "Gender-based  malnutrition",
            "Malnutrition level-wise",
            "Yearly malnutrition change in specific countries",
            "Regions with lowest malnutrition averages",
            "Countries with increasing malnutrition",
            "Min/Max malnutrition levels",
            "High CI_Width flags for monitoring"
        ])

    if topic == "— Select Topic —":
        st.sidebar.info("👆 Please select a topic")
        if st.sidebar.button("⬅ Back to Home"):
            st.session_state.page = "home"
            st.rerun()  
        st.stop()

    if topic == "Malnutrition by age group":
        st.session_state.page = "Malnutrition by age group"
        st.rerun()
    
    if topic == "Top 5 countries with highest malnutrition":
        st.session_state.page = "Top 5 countries with highest malnutrition"
        st.rerun()

    if topic == "Malnutrition trend":
        st.session_state.page = "Malnutrition trend"
        st.rerun()

    if topic == "Gender-based  malnutrition":
        st.session_state.page = "Gender-based  malnutrition"
        st.rerun()

    if topic == "Malnutrition level-wise":
        st.session_state.page = "Malnutrition level-wise"
        st.rerun()

    if topic == "Yearly malnutrition change in specific countries":
        st.session_state.page = "Yearly malnutrition change in specific countries"
        st.rerun()

    if topic == "Regions with lowest malnutrition averages":
        st.session_state.page = "Regions with lowest malnutrition averages"
        st.rerun()

    if topic == "Countries with increasing malnutrition":
        st.session_state.page = "Countries with increasing malnutrition"
        st.rerun()

    if topic == "Min/Max malnutrition levels":
        st.session_state.page = "Min/Max malnutrition levels"
        st.rerun()

    if topic == "High CI_Width flags for monitoring":
        st.session_state.page = "High CI_Width flags for monitoring"
        st.rerun()
    
# --------------------------------------------------
# Malnutrition Query 1
# --------------------------------------------------
elif st.session_state.page == "Malnutrition by age group":

    st.subheader("1. Malnutrition by age group")

    query = f"""SELECT Age_Group,
    ROUND(AVG(Mean_Estimate),2) AS Avg_malnutrition
    FROM malnutrition
    GROUP BY Age_Group;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.pie(data_frame=df,values="Avg_malnutrition",
                 names="Age_Group",title="Malnutrition Vs Age Group",hole=0.5)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(title_x=0.3,title_font=dict(size=40),
                          width=600,     # increase width
                          height=500  ,    # increase height
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))


    st.plotly_chart(fig,use_container_width=True)
    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()

# --------------------------------------------------
# Malnutrition Query 2
# --------------------------------------------------

elif st.session_state.page == "Top 5 countries with highest malnutrition":

    st.subheader("2. Top 5 countries with highest malnutrition")

    query = f"""SELECT Country,
       ROUND(AVG(Mean_Estimate),2) AS Avg_malnutrition
       FROM malnutrition
       GROUP BY Country
       ORDER BY Avg_malnutrition DESC
       LIMIT 5;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig= go.Figure(data=[go.Pie(labels=df["Country"], values=df["Avg_malnutrition"], pull=[0.1, 0, 0, 0])])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(title=dict(text="Country VS Malnutrition",x=0.5, xanchor="center"),title_font=dict(size=40),
                          width=600,     # increase width
                          height=500  ,    # increase height
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))


    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()

# --------------------------------------------------
# Malnutrition Query 3
# --------------------------------------------------
elif st.session_state.page == "Malnutrition trend":

    st.subheader("3. Malnutrition trend in African region over the years")
    
    query = f"""SELECT Year,
       ROUND(AVG(Mean_Estimate),2) AS Avg_malnutrition
       FROM malnutrition
       WHERE Region = 'Africa'
       GROUP BY Year
       ORDER BY Year ASC;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.line(data_frame=df,y="Avg_malnutrition",x="Year",title="Malnutrition Vs Year")
    fig.update_traces(
    marker=dict(size=10, symbol="circle"))
    fig.update_layout(title_x=0.4,title_font=dict(size=40),
                          width=500,     # increase width
                          height=550  ,    # increase height
                              hoverlabel=dict(
                              bgcolor="#FA5E5E",
                              font_size=14,
                              font_color="White"))
    
    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 4
# --------------------------------------------------
elif st.session_state.page == "Gender-based  malnutrition":

    st.subheader("4. Gender-based average malnutrition")

    query = f"""SELECT Gender,
       ROUND(AVG(Mean_Estimate),2) AS Avg_malnutrition
       FROM malnutrition
       GROUP BY Gender;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,y="Avg_malnutrition",x="Gender",title="Malnutrition Vs Gender",color="Gender")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))
    
    st.plotly_chart(fig,use_container_width=True)
    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 5
# --------------------------------------------------
elif st.session_state.page == "Malnutrition level-wise":

    st.subheader("5. Malnutrition level-wise (average CI_Width by age group)")

    query = f"""SELECT Malnutrition_level,
       Age_Group,
       ROUND(AVG(CI_Width),2) AS Avg_ci_width
       FROM malnutrition
       GROUP BY Malnutrition_level, Age_Group;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,y="Avg_ci_width",
                 x="Age_Group",color="Malnutrition_level",barmode="group",title="Age Group Vs Ci width")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))
    
    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 6
# --------------------------------------------------
elif st.session_state.page == "Yearly malnutrition change in specific countries":
   
    st.subheader("6. Yearly malnutrition change in specific countries(India, Nigeria, Brazil)")

    query = """SELECT Year,
       Country,
       ROUND(AVG(Mean_Estimate),2) AS Avg_malnutrition
       FROM malnutrition
       WHERE Country IN ("India","Nigeria","Brazil")
       GROUP BY Year, Country
       ORDER BY Year ASC;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.area(data_frame=df,x="Year",y="Avg_malnutrition",
                  color="Country",markers=True,title="Malnutrition Vs Year")
    fig.update_traces(
    marker=dict(size=10, symbol="circle"))
    fig.update_layout(title_x=0.4,title_font=dict(size=40),
                          width=500,     # increase width
                          height=550  ,    # increase height
                              hoverlabel=dict(
                              bgcolor="#FA5E5E",
                              font_size=14,
                              font_color="White"))

    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 7
# --------------------------------------------------
elif st.session_state.page == "Regions with lowest malnutrition averages":

    st.subheader("7. Regions with lowest malnutrition averages")

    query = """SELECT Region,
       ROUND(AVG(Mean_Estimate),2) AS Avg_malnutrition
       FROM malnutrition
       GROUP BY Region
       ORDER BY Avg_malnutrition ASC;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x="Region",y="Avg_malnutrition",title="Malnutrition Vs Region",color="Region")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 8
# --------------------------------------------------
elif st.session_state.page == "Countries with increasing malnutrition":

    st.subheader("8. Countries with increasing malnutrition")

    query = """SELECT Country,
       MIN(CASE WHEN Year = (SELECT MIN(Year) FROM malnutrition)
                THEN Mean_Estimate END) AS early_value,
       
       MAX(CASE WHEN Year = (SELECT MAX(Year) FROM malnutrition)
                THEN Mean_Estimate END) AS recent_value,
       
       MAX(CASE WHEN Year = (SELECT MAX(Year) FROM malnutrition)
                THEN Mean_Estimate END)
       -
       MIN(CASE WHEN Year = (SELECT MIN(Year) FROM malnutrition)
                THEN Mean_Estimate END) AS difference
        FROM malnutrition
        GROUP BY Country
        HAVING difference > 0
        ORDER BY difference DESC;"""
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.area(data_frame=df,x="Country",y=["early_value","recent_value"],title="Early value Vs Recent value by Country")
    fig.update_traces(
    marker=dict(size=10, symbol="circle"))
    fig.update_layout(title_x=0.25,title_font=dict(size=40),
                          width=500,     # increase width
                          height=550  ,    # increase height
                              hoverlabel=dict(
                              bgcolor="#FA5E5E",
                              font_size=14,
                              font_color="White"))

    st.plotly_chart(fig,use_container_width=True)



    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 9
# --------------------------------------------------
elif st.session_state.page == "Min/Max malnutrition levels":

    st.subheader("9. Min/Max malnutrition levels year-wise comparison")

    query = f"""SELECT Year,
       MIN(Mean_Estimate) AS min_malnutrition,
       MAX(Mean_Estimate) AS max_malnutrition
       FROM malnutrition
       GROUP BY Year
       ORDER BY Year;"""
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.area(data_frame=df,x="Year",y=["min_malnutrition","max_malnutrition"]
                  ,markers="circle",title="Min Malnutrition Vs Max Malnutrition by Year")
    fig.update_traces(
    marker=dict(size=10, symbol="circle"))
    fig.update_layout(title_x=0.2,title_font=dict(size=40),
                          width=500,     # increase width
                          height=550  ,    # increase height
                              hoverlabel=dict(
                              bgcolor="#FA5E5E",
                              font_size=14,
                              font_color="White"))

    st.plotly_chart(fig,use_container_width=True)

    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
# --------------------------------------------------
# Malnutrition Query 10
# --------------------------------------------------
elif st.session_state.page == "High CI_Width flags for monitoring":

    st.subheader("10. High CI_Width flags for monitoring (CI_width > 5)")
    
    query = """SELECT Country,
       Year,Region,Mean_Estimate,CI_Width
       FROM malnutrition
       WHERE CI_Width > 5
       ORDER BY CI_Width DESC;"""
    
    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x="Year",y="CI_Width",
                 color="Region",title="Year Vs CI Width")
    fig.update_layout(title_x=0.35,title_font=dict(size=40),
                          hoverlabel=dict(
                              bgcolor="#57F782",
                              font_color="black"))

    st.plotly_chart(fig,use_container_width=True)


    if st.button("⬅ Back to Malnutrition Analysis"):
        st.session_state.page = "Malnutrition Analysis"
        st.rerun()
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------
# Obesity VS Malnutrition Analysis
# --------------------------------------------------

elif st.session_state.page == "Combined Analysis":

    st.header('Obesity VS Malnutrition Analysis')
    
    topic = st.selectbox(
        "Choose Topic",
        [
            "— Select Topic —",
            "Obesity vs malnutrition by country",
            "Gender-based disparity",
            "Region-wise avg estimates",
            "obesity up & malnutrition down",
            "Age-wise trend analysis"
        ])

    if topic == "— Select Topic —":
        st.info("👆 Please select a topic")
        if st.button("⬅ Back to Home"):
            st.session_state.page = "home"
            st.rerun()  
        st.stop()

    if topic == "Obesity vs malnutrition by country":
        st.session_state.page = "Obesity vs malnutrition"
        st.rerun()
    
    if topic == "Gender-based disparity":
        st.session_state.page = "Gender-based disparity"
        st.rerun()

    if topic == "Region-wise avg estimates":
        st.session_state.page = "Region-wise avg estimates"
        st.rerun()

    if topic == "obesity up & malnutrition down":
        st.session_state.page = "obesity up & malnutrition down"
        st.rerun()

    if topic == "Age-wise trend analysis":
        st.session_state.page = "Age-wise trend analysis"
        st.rerun()

# --------------------------------------------------
# Combined Query 1
# --------------------------------------------------
elif st.session_state.page == "Obesity vs malnutrition":

    st.subheader("1. Obesity vs malnutrition comparison by country(any 5 countries)")

    query = f"""SELECT 
    o.Country,
    ROUND(AVG(o.Mean_Estimate),2) AS Avg_Obesity,
    ROUND(AVG(m.Mean_Estimate),2) AS Avg_Malnutrition
    FROM obesity o
    INNER JOIN malnutrition m 
    ON o.Country = m.Country
    GROUP BY o.Country
    ORDER BY avg_obesity DESC
    LIMIT 5;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig1 = go.Figure(data=[go.Pie(labels=df["Country"], values=df["Avg_Obesity"], pull=[0.1, 0, 0, 0])])
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    fig1.update_layout(title=dict(text="Country VS Obesity",x=0.4, xanchor="center"),title_font=dict(size=30),
                          width=600,     # increase width
                          height=500  ,    # increase height
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))
    fig2= px.bar(data_frame=df,
                     x="Country",y="Avg_Malnutrition",title="Country VS Malnutrition",color="Country")
    fig2.update_layout(title_x=0.3,title_font=dict(size=30),
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))
    col1,col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1,use_container_width=False)
    with col2:
        st.plotly_chart(fig2,use_container_width=False)
    
    if st.button("⬅ Back to Combined Analysis"):
        st.session_state.page = "Combined Analysis"
        st.rerun()

# --------------------------------------------------
# Combined Query 2
# --------------------------------------------------
elif st.session_state.page == "Gender-based disparity":

    st.subheader("2. Gender-based disparity in both obesity and malnutrition")

    query = f"""SELECT 
    o.Gender,
    ROUND(AVG(o.Mean_Estimate),2) AS Obesity,
    ROUND(AVG(m.Mean_Estimate),2) AS Malnutrition
    FROM obesity o
    INNER JOIN malnutrition m 
    ON o.Country = m.Country
    AND o.Year = m.Year
    AND o.Gender = m.Gender
    GROUP BY o.Gender;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x='Gender',y=["Malnutrition","Obesity"],barmode="group",title="Obesity Vs Malnutrition by Gender",
                 color_discrete_sequence=["#1f77b4", "#ff0e56"])
    fig.update_layout(title_x=0.35,title_font=dict(size=35),
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))
    

    st.plotly_chart(fig,use_container_width=True)
    
    if st.button("⬅ Back to Combined Analysis"):
        st.session_state.page = "Combined Analysis"
        st.rerun()


# --------------------------------------------------
# Combined Query 3
# --------------------------------------------------
elif st.session_state.page == "Region-wise avg estimates":

    st.subheader("3. Region-wise avg estimates side-by-side(Africa and America)")

    query = f"""SELECT 
    o.Region,
    ROUND(AVG(o.Mean_Estimate),2) AS Avg_Obesity,
    ROUND(AVG(m.Mean_Estimate),2) AS Avg_Malnutrition
    FROM obesity o
    INNER JOIN malnutrition m
    ON o.Country = m.Country
    AND o.Year = m.Year
    WHERE o.Region IN ('Africa', 'Americas')
    GROUP BY o.Region;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    
    fig = px.bar(data_frame=df,x='Region',y=["Avg_Obesity", "Avg_Malnutrition"],title="Obesity Vs Malnutrition by Region",
                 barmode='group',color_discrete_sequence=["#99c3e1", "#f479d3"])
    fig.update_layout(title_x=0.35,title_font=dict(size=35),
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))

    st.plotly_chart(fig,use_container_width=True)
    
    if st.button("⬅ Back to Combined Analysis"):
        st.session_state.page = "Combined Analysis"
        st.rerun()


# --------------------------------------------------
# Combined Query 4
# --------------------------------------------------
elif st.session_state.page == "obesity up & malnutrition down":

    st.subheader("4. Countries with obesity up & malnutrition down")

    query = f"""SELECT 
    o.Country,
    MAX(CASE WHEN o.Year = 2022 THEN o.Mean_Estimate END) 
        - MAX(CASE WHEN o.Year = 2012 THEN o.Mean_Estimate END) 
        AS obesity_change,

    MAX(CASE WHEN m.Year = 2022 THEN m.Mean_Estimate END) 
        - MAX(CASE WHEN m.Year = 2012 THEN m.Mean_Estimate END) 
        AS malnutrition_change
        
    FROM obesity o
    INNER JOIN malnutrition m
    ON o.Country = m.Country
    AND o.Year = m.Year
    GROUP BY o.Country
    HAVING obesity_change > 0 
    AND malnutrition_change < 0;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    fig = px.bar(data_frame=df,x="Country",y=["obesity_change","malnutrition_change"],barmode="relative",
                 title="Obesity Vs Malnutrition by Country")
    fig.update_layout(title_x=0.35,title_font=dict(size=35),
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))

    st.plotly_chart(fig,use_container_width=True)
    
    if st.button("⬅ Back to Combined Analysis"):
        st.session_state.page = "Combined Analysis"
        st.rerun()


# --------------------------------------------------
# Combined Query 5
# --------------------------------------------------
elif st.session_state.page == "Age-wise trend analysis":

    st.subheader("5. Age-wise trend analysis")

    query = f"""SELECT 
    o.Age_Group,
    o.Year,
    ROUND(AVG(o.Mean_Estimate),2) AS avg_obesity,
    ROUND(AVG(m.Mean_Estimate),2) AS avg_malnutrition
    FROM obesity o
    INNER JOIN malnutrition m 
    ON o.Country = m.Country
    AND o.Year = m.Year
    AND o.Age_Group = m.Age_Group
    GROUP BY o.Age_Group, o.Year
    ORDER BY o.Age_Group, o.Year;"""

    df = pd.read_sql(query,db_engine)
    st.dataframe(df,use_container_width=True)

    df_melt = df.melt(
    id_vars=["Year","Age_Group"],
    value_vars=["avg_obesity","avg_malnutrition"],
    var_name="Indicator",
    value_name="Value")

    fig = px.bar(data_frame=df_melt,x="Year",y="Value",color="Indicator",barmode="group",
                 facet_col="Age_Group",title="Obesity Vs Malnutrition by Age Group")
    fig.update_layout(title_x=0.35,title_font=dict(size=35),
                          hoverlabel=dict(
                              bgcolor="#9325FB",   # Background color
                              font_size=14,
                              font_color="white"))
    st.plotly_chart(fig,use_container_width=True)
    
    if st.button("⬅ Back to Combined Analysis"):
        st.session_state.page = "Combined Analysis"
        st.rerun()
