import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import PyPDF2
import io
import time

# Set page config
st.set_page_config(
    page_title="CDSCO SEC Quick Search",
    page_icon="🔍",
    layout="wide"
)

# CDSCO SEC URLs
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
PDF_BASE_URL = "https://cdsco.gov.in/opencms/opencms/system/modules/CDSCO.WEB/elements/common_download.jsp"

def get_pdf_links(limit=50):
    """Get PDF links from the CDSCO SEC website (limited number for testing)"""
    try:
        response = requests.get(CDSCO_BASE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdf_links = []
        for link in soup.find_all('a', href=True):
            if len(pdf_links) >= limit:
                break
            if 'common_download.jsp' in link['href']:
                num_id = link['href'].split('num_id_pk=')[1]
                pdf_url = f"{PDF_BASE_URL}?num_id_pk={num_id}"
                pdf_links.append({
                    'url': pdf_url,
                    'title': link.text.strip(),
                    'id': num_id
                })
        return pdf_links
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def extract_text(pdf_url):
    """Extract text from a PDF file"""
    try:
        response = requests.get(pdf_url, timeout=15)
        response.raise_for_status()
        with io.BytesIO(response.content) as f:
            reader = PyPDF2.PdfReader(f)
            return " ".join(page.extract_text() or "" for page in reader.pages)
    except:
        return ""

def search_pdfs(pdf_list, keyword):
    """Search for keyword in PDFs (limited to first 50)"""
    results = []
    keyword = keyword.lower()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, pdf in enumerate(pdf_list[:50]):  # Explicit limit to 50
        status_text.text(f"Scanning {i+1}/50: {pdf['title'][:50]}...")
        progress_bar.progress((i + 1) / 50)
        
        text = extract_text(pdf['url'])
        if keyword in text.lower():
            results.append({
                'title': pdf['title'],
                'url': pdf['url'],
                'count': text.lower().count(keyword)
            })
        time.sleep(0.5)  # Brief pause
    
    progress_bar.empty()
    return results

# Streamlit UI
st.title("CDSCO SEC Quick Search (Test Mode)")
st.write("This test version scans only the first 50 documents for faster results.")

keyword = st.text_input("Enter keyword to search", placeholder="e.g., vaccine, trial")
if st.button("Search"):
    if keyword:
        with st.spinner("Loading first 50 documents..."):
            pdfs = get_pdf_links(limit=50)
        
        if not pdfs:
            st.error("No documents found")
        else:
            with st.spinner(f"Searching in {len(pdfs)} documents..."):
                matches = search_pdfs(pdfs, keyword)
            
            if matches:
                st.success(f"Found {len(matches)} matching documents")
                for doc in sorted(matches, key=lambda x: x['count'], reverse=True):
                    with st.expander(f"📄 {doc['title']} ({doc['count']} matches)"):
                        st.markdown(f"[Download PDF]({doc['url']})")
            else:
                st.warning("No matches found")
    else:
        st.warning("Please enter a keyword")

st.info("Note: This is a test version limited to 50 documents for faster results.")