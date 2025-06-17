import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import re
from urllib.parse import urljoin
import time
import pdfplumber  # More reliable PDF reader

# Configuration
st.set_page_config(page_title="CDSCO SEC PDF Search", layout="wide")
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
MAX_DOCS = 10  # Increased from 5 for better testing
DEBUG = True

def get_pdf_links():
    """Fetch PDF links with proper headers and timeout"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(CDSCO_BASE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'common_download.jsp' in href:
                full_url = urljoin(CDSCO_BASE_URL, href)
                title = a.text.strip() or f"Document {len(links)+1}"
                links.append({
                    'url': full_url,
                    'title': title,
                    'href': href
                })
                if len(links) >= MAX_DOCS:
                    break
        
        if DEBUG:
            st.write("🔍 Found PDF links:", [link['title'] for link in links])
        return links
    
    except Exception as e:
        st.error(f"Failed to fetch documents: {str(e)}")
        return []

def extract_text(pdf_url):
    """Extract text using pdfplumber with fallback to PyPDF2"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf, */*'
        }
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # First try pdfplumber (more reliable)
        try:
            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += re.sub(r'\s+', ' ', page_text).strip() + " "
            return text
        except:
            pass
        
        # Fallback to PyPDF2
        with io.BytesIO(response.content) as f:
            try:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += re.sub(r'\s+', ' ', page_text).strip() + " "
                return text
            except Exception as e:
                if DEBUG:
                    st.warning(f"⚠️ Could not read PDF: {str(e)}")
                return ""
    
    except Exception as e:
        if DEBUG:
            st.warning(f"⚠️ Download failed: {str(e)}")
        return ""

def search_documents(pdf_list, keyword):
    """Search documents with better matching"""
    results = []
    keyword = keyword.lower().strip()
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    
    progress_bar = st.progress(0)
    
    for i, pdf in enumerate(pdf_list):
        progress_bar.progress((i + 1) / len(pdf_list))
        st.write(f"🔎 Processing: {pdf['title']}")
        
        text = extract_text(pdf['url'])
        if not text:
            continue
            
        matches = list(pattern.finditer(text))
        if matches:
            samples = []
            for match in matches[:3]:  # Get first 3 matches
                start = max(0, match.start()-30)
                end = min(len(text), match.end()+30)
                context = text[start:end].replace('\n', ' ')
                samples.append(context.strip())
            
            results.append({
                'title': pdf['title'],
                'url': pdf['url'],
                'count': len(matches),
                'samples': samples
            })
        
        time.sleep(1)  # Respectful delay
    
    progress_bar.empty()
    return results

# Streamlit Interface
st.title("CDSCO SEC Document Search")
st.write("Improved version with better PDF handling")

keyword = st.text_input("Search term:", "clinical trial")
search_btn = st.button("Search Documents")

if search_btn:
    with st.spinner("Fetching documents..."):
        pdf_links = get_pdf_links()
    
    if not pdf_links:
        st.error("No documents found. The website structure may have changed.")
    else:
        with st.spinner(f"Searching in {len(pdf_links)} documents..."):
            results = search_documents(pdf_links, keyword)
        
        if results:
            st.success(f"Found {len(results)} matching documents")
            for doc in sorted(results, key=lambda x: x['count'], reverse=True):
                with st.expander(f"📄 {doc['title']} ({doc['count']} matches)"):
                    st.markdown(f"[Download PDF]({doc['url']})")
                    st.write("**Matches:**")
                    for sample in doc['samples']:
                        highlighted = re.sub(
                            re.escape(keyword), 
                            lambda m: f"**{m.group(0)}**", 
                            sample, 
                            flags=re.IGNORECASE
                        )
                        st.write(f"- ...{highlighted}...")
        else:
            st.warning("No matches found. Try these troubleshooting steps:")
            st.write("1. Try simpler search terms (e.g., 'study' instead of 'clinical trial')")
            st.write("2. Some PDFs may be image scans (we're working on OCR support)")
            st.write("3. Check if the documents contain your search term")

st.markdown("---")
st.write("Note: This version uses pdfplumber for more reliable PDF text extraction")