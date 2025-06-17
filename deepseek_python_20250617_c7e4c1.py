import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import re
import time
from urllib.parse import urljoin
import base64

# Configuration
st.set_page_config(page_title="CDSCO SEC PDF Search", layout="wide")
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
MAX_DOCS = 10
DEBUG = True

def get_pdf_links():
    """Fetch PDF links from CDSCO website with error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(CDSCO_BASE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        if DEBUG and response.history:
            st.write("Redirect path:")
            for resp in response.history:
                st.write(f"→ {resp.status_code} {resp.url}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'common_download.jsp' in href:
                full_url = urljoin(CDSCO_BASE_URL, href)
                title = a.text.strip() or f"Document {len(pdf_links)+1}"
                pdf_links.append({
                    'url': full_url,
                    'title': title,
                    'href': href
                })
                if len(pdf_links) >= MAX_DOCS:
                    break
        
        if DEBUG:
            st.write(f"Found {len(pdf_links)} PDF links")
        return pdf_links
    
    except Exception as e:
        st.error(f"Failed to fetch documents: {str(e)}")
        return []

def verify_pdf_content(pdf_bytes):
    """Verify if content is a valid PDF"""
    return pdf_bytes.startswith(b'%PDF')

def extract_text(pdf_url):
    """Extract text from PDF using PyPDF2 with robust error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf'
        }
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        if not verify_pdf_content(response.content):
            if DEBUG:
                st.warning("Downloaded content is not a valid PDF")
                st.write(f"Content starts with: {response.content[:20]}")
            return ""
        
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
                    st.warning(f"PDF read error: {str(e)}")
                return ""
    
    except Exception as e:
        if DEBUG:
            st.warning(f"Download failed: {str(e)}")
        return ""

def search_documents(pdf_list, keyword):
    """Search documents for keyword matches"""
    results = []
    keyword = keyword.lower().strip()
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    
    progress_bar = st.progress(0)
    
    for i, pdf in enumerate(pdf_list):
        progress_bar.progress((i + 1) / len(pdf_list))
        st.write(f"Processing: {pdf['title']}")
        
        text = extract_text(pdf['url'])
        
        if DEBUG and text:
            st.write(f"Extracted {len(text)} characters")
            if len(text) < 1000:
                st.code(text[:500] + "...")
        
        if text:
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
        
        time.sleep(1)  # Be polite to the server
    
    progress_bar.empty()
    return results

# Streamlit UI
st.title("CDSCO SEC Document Search")
st.write("Robust PDF search tool with content verification")

keyword = st.text_input("Search term:", "clinical trial")
search_btn = st.button("Search Documents")

if search_btn:
    st.write("## Step 1: Fetching Documents")
    pdf_links = get_pdf_links()
    
    if not pdf_links:
        st.error("No documents found. The website structure may have changed.")
    else:
        st.write(f"## Step 2: Searching {len(pdf_links)} Documents")
        results = search_documents(pdf_links, keyword)
        
        st.write("## Step 3: Results")
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
            st.error("No matches found. Possible reasons:")
            st.write("1. The PDFs might be image scans (OCR not implemented)")
            st.write("2. Your search term might not exist in these documents")
            st.write("3. The documents might be corrupted or password protected")

st.markdown("---")
st.write("ℹ️ Debug mode is ON. Set DEBUG = False for cleaner output.")