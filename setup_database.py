import sqlite3
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Read the scraped data
df = pd.read_csv('faqs.csv')

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('faqs.db')
cursor = conn.cursor()

# Create table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
''')

logger.info("Database and table created successfully.")

# Insert data into the table
for index, row in df.iterrows():
    cursor.execute('''
        INSERT INTO faqs (question, answer)
        VALUES (?, ?)
    ''', (row['question'], row['answer']))

conn.commit()
logger.info("Data inserted into the database successfully.")

# Close the connection
conn.close()
