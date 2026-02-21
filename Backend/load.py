import os
import pandas as pd
from sqlalchemy import create_engine

# PostgreSQL connection
engine = create_engine("postgresql://postgres:tiger@localhost:5432/business_data")

# Folder where your files are located
folder_path = r"D:\DataLens\DataLens\Backend\dataset"   # <-- CHANGE THIS

# Loop through all Excel/CSV files
for file in os.listdir(folder_path):
    if file.endswith(".csv") or file.endswith(".xlsx"):
        file_path = os.path.join(folder_path, file)

        print(f"Loading {file}...")

        # Read file
        if file.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Create table name from file name
        table_name = file.replace(".csv", "").replace(".xlsx", "").lower()

        # Load into PostgreSQL
        df.to_sql(table_name, engine, if_exists="replace", index=False)

        print(f"{table_name} imported successfully!")

print("All files imported!")