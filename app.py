from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from search_engine import SearchEngine
import logging
import sqlite3

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Search Engine
search_engine = SearchEngine(db_path='faqs.db')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_faq():
    question = request.form.get('question')
    answer = request.form.get('answer')
    
    if not question or not answer:
        logger.warning("Incomplete FAQ submission.")
        return "Please provide both question and answer.", 400
    
    try:
        # Insert into the database using a new connection
        conn = sqlite3.connect('faqs.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO faqs (question, answer)
            VALUES (?, ?)
        ''', (question, answer))
        conn.commit()
        conn.close()
        
        logger.info(f"Added new FAQ: {question}")
        
        # Reload the data in the Search Engine
        search_engine.reload_data(db_path='faqs.db')
        
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error adding new FAQ: {e}")
        return "An error occurred while adding the FAQ.", 500

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    algorithm = request.form.get('algorithm')
    
    if not query or not algorithm:
        logger.warning("Search request missing query or algorithm.")
        return redirect(url_for('index'))
    
    if algorithm == 'boolean':
        results = search_engine.boolean_search(query)
    elif algorithm == 'extended_boolean':
        results = search_engine.extended_boolean_search(query)
    elif algorithm == 'vector':
        results = search_engine.vector_search(query)
    elif algorithm == 'bert':
        results = search_engine.bert_search(query)
    else:
        results = pd.DataFrame()
        logger.warning(f"Unknown search algorithm selected: {algorithm}")
    
    return render_template('index.html', query=query, results=results)

if __name__ == '__main__':
    app.run(debug=True)
