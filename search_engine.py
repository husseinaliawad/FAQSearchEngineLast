import os
import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import torch
from sentence_transformers import SentenceTransformer, util

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self, db_path='faqs.db'):
        # Load data into DataFrame
        self.df = self.load_data(db_path)
        logger.info(f"Loaded {len(self.df)} FAQs from the database.")

        # Initialize TF-IDF Vectorizer for VSM
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df['question'] + " " + self.df['answer'])
        logger.info("TF-IDF matrix created for VSM.")

        # Initialize BERT model for advanced retrieval
        self.bert_model = SentenceTransformer('distilbert-base-nli-stsb-mean-tokens')
        self.bert_embeddings = self.bert_model.encode(self.df['question'] + " " + self.df['answer'], convert_to_tensor=True)
        logger.info("BERT embeddings created for advanced retrieval.")

    def load_data(self, db_path):
        """Load data from SQLite database into a DataFrame."""
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM faqs", conn)
        conn.close()
        return df

    def reload_data(self, db_path='faqs.db'):
        """Reload data from the database and update models."""
        self.df = self.load_data(db_path)
        logger.info(f"Reloaded {len(self.df)} FAQs from the database.")

        # Recreate the TF-IDF matrix and BERT embeddings
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df['question'] + " " + self.df['answer'])
        logger.info("TF-IDF matrix recreated after reloading data.")
        self.bert_embeddings = self.bert_model.encode(self.df['question'] + " " + self.df['answer'], convert_to_tensor=True)
        logger.info("BERT embeddings recreated after reloading data.")

    def boolean_search(self, query):
        logger.info(f"Performing Boolean search for query: {query}")
        keywords = query.lower().split()
        results = self.df[self.df.apply(
            lambda row: all(
                word in (str(row['question']).lower() + " " + str(row['answer']).lower())
                for word in keywords
            ), axis=1
        )]
        logger.info(f"Boolean search found {len(results)} results.")
        return results

    def extended_boolean_search(self, query):
        logger.info(f"Performing Extended Boolean search for query: {query}")
        try:
            # Handle single keywords directly
            if "AND" not in query and "OR" not in query and "NOT" not in query:
                query_str = f"(question.str.contains('{query}') or answer.str.contains('{query}'))"
            else:
                # Replace logical operators with pandas-compatible equivalents
                query = query.lower()
                conditions = []
                tokens = query.split()
                i = 0
                while i < len(tokens):
                    token = tokens[i]
                    if token == "and":
                        conditions[-1] = f"({conditions[-1]}) & "
                    elif token == "or":
                        conditions[-1] = f"({conditions[-1]}) | "
                    elif token == "not" and i + 1 < len(tokens):
                        conditions.append(f"~(question.str.contains('{tokens[i + 1]}') or answer.str.contains('{tokens[i + 1]}'))")
                        i += 1
                    else:
                        conditions.append(f"(question.str.contains('{token}') or answer.str.contains('{token}'))")
                    i += 1
                query_str = "".join(conditions)

            # Execute query using pandas
            filtered_rows = self.df.query(query_str, engine='python')
            logger.info(f"Extended Boolean search found {len(filtered_rows)} results.")
            return filtered_rows
        except Exception as e:
            logger.error(f"Error in Extended Boolean search: {e}")
            return pd.DataFrame()

    def vector_search(self, query, top_n=5):
        logger.info(f"Performing Vector Space Model search for query: {query}")
        query_vec = self.vectorizer.transform([query])
        cosine_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        related_doc_indices = cosine_sim.argsort()[-top_n:][::-1]
        results = self.df.iloc[related_doc_indices]
        logger.info(f"Vector search found {len(results)} results.")
        return results

    def bert_search(self, query, top_n=5):
        logger.info(f"Performing BERT search for query: {query}")
        query_embedding = self.bert_model.encode(query, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(query_embedding, self.bert_embeddings)[0]
        top_results = torch.topk(cosine_scores, k=min(top_n, len(self.df)))
        related_doc_indices = top_results.indices.cpu().numpy()
        results = self.df.iloc[related_doc_indices]
        logger.info(f"BERT search found {len(results)} results.")
        return results

# Example usage:
if __name__ == "__main__":
    engine = SearchEngine()

    # Example queries
    query = "Dubai travel requirements"
    logger.info("Boolean Search Results:")
    print(engine.boolean_search(query))

    logger.info("Extended Boolean Search Results:")
    print(engine.extended_boolean_search("Dubai AND travel NOT requirements"))

    logger.info("Vector Search Results:")
    print(engine.vector_search(query))

    logger.info("BERT Search Results:")
    print(engine.bert_search(query))
