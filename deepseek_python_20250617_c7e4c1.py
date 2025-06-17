import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import re
from urllib.parse import urljoin
import time

# Configure Streamlit
st.set_page_config(
    page_title="CDSCO SEC PDF Search",
    page_icon="🔍",
    layout="wide"
)

# Constants
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
MAX_DOCS = 50  # Limit for testing
REQUEST_TIMEOUT = 20

def get_pdf_links():
    """Extract PDF links from the CDSCO SEC page"""
    try:
        response = requests.get(CDSCO_BASE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdf_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'common_download.jsp' in href:
                full_url = urljoin(CDSCO_BASE_URL, href)
                title = link.text.strip() or f"Document {len(pdf_links)+1}"
                pdf_links.append({'url': full_url, 'title': title})
                if len(pdf_links) >= MAX_DOCS:
                    break
        return pdf_links
    except Exception as e:
        st.error(f"Failed to fetch documents: {str(e)}")
        return []

def extract_text_from_pdf(pdf_url):
    """Improved PDF text extraction with better error handling"""
    try:
        response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        with io.BytesIO(response.content) as pdf_file:
            try:
                reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Clean up text for better searching
                        text += re.sub(r'\s+', ' ', page_text).strip() + " "
                return text
            except PyPDF2.errors.PdfReadError:
                return ""
    except Exception as e:
        st.warning(f"Could not process {pdf_url}: {str(e)}")
        return ""

def search_documents(pdf_links, keyword):
    """Search documents for keyword matches"""
    results = []
    keyword = keyword.lower().strip()
    
    if not keyword:
        return results
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, pdf in enumerate(pdf_links[:MAX_DOCS]):
        status_text.text(f"Processing {i+1}/{min(len(pdf_links), MAX_DOCS)}: {pdf['title']}")
        progress_bar.progress((i + 1) / min(len(pdf_links), MAX_DOCS))
        
        text = extract_text_from_pdf(pdf['url'])
        if not text:
            continue
            
        text_lower = text.lower()
        if keyword in text_lower:
            # Count all occurrences
            count = text_lower.count(keyword)
            # Find sample positions
            matches = [m.start() for m in re.finditer(re.escape(keyword), text_lower)]
            samples = []
            for pos in matches[:3]:  # Get first 3 matches
                start = max(0, pos-20)
                end = min(len(text), pos+20+len(keyword))
                samples.append(text[start:end].strip())
                
            results.append({
                'title': pdf['title'],
                'url': pdf['url'],
                'count': count,
                'samples': samples
            })
        
        time.sleep(0.5)  # Be polite to the server
    
    progress_bar.empty()
    status_text.empty()
    return results

# Streamlit UI
st.title("CDSCO SEC Document Search")
st.write("Search engine for CDSCO Subject Expert Committee documents")

keyword = st.text_input("Search keyword:", help="Enter a word or phrase to search in documents")
search_button = st.button("Search Documents")

if search_button and keyword:
    with st.spinner("Fetching document list..."):
        pdf_links = get_pdf_links()
    
    if not pdf_links:
        st.error("No documents found on the CDSCO SEC page")
    else:
        st.info(f"Searching in {min(len(pdf_links), MAX_DOCS)} documents...")
        
        with st.spinner("Scanning documents..."):
            results = search_documents(pdf_links, keyword)
        
        if results:
            st.success(f"Found {len(results)} matching documents")
            for doc in sorted(results, key=lambda x: x['count'], reverse=True):
                with st.expander(f"📄 {doc['title']} ({doc['count']} matches)"):
                    st.markdown(f"**Document URL:** [{doc['url']}]({doc['url']})")
                    st.write("**Sample matches:**")
                    for sample in doc['samples']:
                        # Highlight the keyword
                        highlighted = sample.replace(
                            keyword, 
                            f"**{keyword}**"
                        )
                        st.write(f"- ...{highlighted}...")
        else:
            st.warning("No matches found. Try a different search term.")

elif search_button and not keyword:
    st.warning("Please enter a search keyword")

st.markdown("---")
st.info(f"Note: This test version is limited to scanning {MAX_DOCS} documents for faster results.")