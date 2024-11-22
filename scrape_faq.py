import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_from_html(html_content):
    """
    تستخدم BeautifulSoup لتحليل HTML واستخراج النصوص المنسقة بما في ذلك القوائم.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # استخراج النصوص من الفقرات
    paragraphs = soup.find_all('p')
    para_text = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
    
    # استخراج النصوص من القوائم
    lists = soup.find_all('ul')
    list_text = ''
    for ul in lists:
        for li in ul.find_all('li'):
            list_text += f"- {li.get_text(strip=True)}\n"
    
    # دمج النصوص
    full_text = para_text + '\n' + list_text
    return full_text.strip()

def scrape_faq_page(url):
    # Set up Chrome options
    chrome_options = Options()
    # Uncomment the line below to see the browser in action (useful for debugging)
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")

    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    logger.info(f"Opening page: {url}")
    driver.get(url)

    try:
        # Wait until all question elements are present
        wait = WebDriverWait(driver, 30)  # Increased wait time
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'cta-overlay__anchor')))
        logger.info("All question elements loaded.")
    except Exception as e:
        logger.error(f"Error loading page {url}: {e}")
        driver.quit()
        return []

    try:
        # Find all question elements
        questions = driver.find_elements(By.CLASS_NAME, 'cta-overlay__anchor')
        logger.info(f"Number of questions found: {len(questions)}")
    except Exception as e:
        logger.error(f"Error finding question elements in {url}: {e}")
        driver.quit()
        return []

    faqs = []
    for idx, question in enumerate(questions, start=1):
        try:
            question_text = question.text.strip()
            logger.info(f"Scraping Question {idx}: {question_text}")

            # Scroll to the question element
            driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", question)
            time.sleep(1)  # Wait to ensure the element is in view

            # Click the question to reveal the answer
            question.click()
            logger.info(f"Clicked on Question {idx}")

            # Wait until the answer element is visible
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.accordion-overlay__content[data-cy='accordion-generic-item-content']")))
            logger.info(f"Answer for Question {idx} is now visible.")

            # Locate the parent container of the question
            parent = question.find_element(By.XPATH, "./ancestor::div[contains(@class, 'accordion-item')]")
            
            # Find the answer element within the parent container
            answer_element = parent.find_element(By.CSS_SELECTOR, "div.accordion-overlay__content[data-cy='accordion-generic-item-content']")
            
            # استخراج الـ HTML الداخلي لعنصر الجواب
            answer_html = answer_element.get_attribute('innerHTML')
            answer_text = extract_text_from_html(answer_html)

            # Check if the answer is not empty
            if not answer_text:
                logger.warning(f"Answer for question '{question_text}' is empty.")
                answer_text = "No answer found."

            # Append the question and answer to the list
            faqs.append({
                'question': question_text,
                'answer': answer_text
            })

            logger.info(f"Extracted Answer {idx}: {answer_text}")

            # Wait before moving to the next question
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error finding answer for question '{question_text}': {e}")
            faqs.append({
                'question': question_text,
                'answer': "No answer found."
            })

    logger.info(f"Total FAQs found in {url}: {len(faqs)}")

    driver.quit()
    return faqs

# List of FAQ page URLs
urls = [
    'https://www.dubaitourism.gov.ae/ar/faqs',
    'https://www.dubaitourism.gov.ae/en/faqs'
]

# List to store all FAQs
all_faqs = []

for url in urls:
    logger.info(f"Starting to scrape data from: {url}")
    faqs = scrape_faq_page(url)
    all_faqs.extend(faqs)

logger.info(f"Total FAQs scraped: {len(all_faqs)}")

# Save the data to a CSV file
if all_faqs:
    df = pd.DataFrame(all_faqs)
    df.to_csv('faqs.csv', index=False, encoding='utf-8-sig')  # Use appropriate encoding for Arabic support
    logger.info("Data scraped and saved to faqs.csv successfully!")
else:
    logger.warning("No FAQs scraped. Please check the class names and scraping logic.")
