import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import re
import time
from urllib.parse import urljoin, parse_qs
import base64

# Configuration
st.set_page_config(page_title="CDSCO SEC PDF Search", layout="wide")
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
MAX_DOCS = 5  # Reduced for testing
DEBUG = True
SESSION = requests.Session()

def get_pdf_links():
    """Fetch PDF links with session cookies and proper headers"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # First get the main page to establish session
        SESSION.get(CDSCO_BASE_URL, headers=headers, timeout=20)
        
        # Then make the real request
        response = SESSION.get(CDSCO_BASE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'common_download.jsp' in href:
                # Extract the num_id_pk parameter
                query = urljoin(CDSCO_BASE_URL, href).split('?', 1)[-1]
                params = parse_qs(query)
                if 'num_id_pk' in params:
                    num_id = params['num_id_pk'][0]
                    full_url = f"https://cdsco.gov.in/opencms/opencms/system/modules/CDSCO.WEB/elements/download_sec.jsp?num_id_pk={num_id}"
                    title = a.text.strip() or f"Document {len(pdf_links)+1}"
                    pdf_links.append({
                        'url': full_url,
                        'title': title,
                        'num_id': num_id
                    })
                    if len(pdf_links) >= MAX_DOCS:
                        break
        
        if DEBUG:
            st.write(f"Found {len(pdf_links)} PDF links")
            st.json(pdf_links[:1])  # Show first link for debugging
        return pdf_links
    
    except Exception as e:
        st.error(f"Failed to fetch documents: {str(e)}")
        return []

def extract_text(pdf_url, num_id):
    """Extract text with proper session handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf, */*',
            'Referer': CDSCO_BASE_URL
        }
        
        # Try both download endpoints
        endpoints = [
            pdf_url,
            f"https://cdsco.gov.in/opencms/opencms/system/modules/CDSCO.WEB/elements/common_download.jsp?num_id_pk={num_id}"
        ]
        
        for url in endpoints:
            response = SESSION.get(url, headers=headers, timeout=30, stream=True)
            
            if DEBUG:
                st.write(f"Trying endpoint: {url}")
                st.write(f"Response status: {response.status_code}")
                st.write(f"Content type: {response.headers.get('Content-Type')}")
                st.write(f"First 50 bytes: {response.content[:50]}")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' in content_type.lower() or response.content.startswith(b'%PDF'):
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
                            continue
            
            time.sleep(1)  # Delay between attempts
    
    except Exception as e:
        if DEBUG:
            st.warning(f"Download failed: {str(e)}")
        return ""

def search_documents(pdf_list, keyword):
    """Search documents with enhanced debugging"""
    results = []
    keyword = keyword.lower().strip()
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    
    progress_bar = st.progress(0)
    
    for i, pdf in enumerate(pdf_list):
        progress_bar.progress((i + 1) / len(pdf_list))
        st.write(f"Processing: {pdf['title']}")
        
        text = extract_text(pdf['url'], pdf['num_id'])
        
        if DEBUG:
            if text:
                st.write(f"Extracted {len(text)} characters")
                if len(text) < 1000:
                    st.code(text[:500] + "...")
            else:
                st.warning("No text extracted")
        
        if text:
            matches = list(pattern.finditer(text))
            if matches:
                samples = []
                for match in matches[:3]:
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
        
        time.sleep(2)  # Increased delay
    
    progress_bar.empty()
    return results

# Streamlit UI
st.title("CDSCO SEC Document Search")
st.write("Enhanced version with proper session handling")

keyword = st.text_input("Search term:", "clinical")
search_btn = st.button("Search Documents")

if search_btn:
    st.write("## Step 1: Fetching Documents")
    with st.spinner("Loading document links..."):
        pdf_links = get_pdf_links()
    
    if not pdf_links:
        st.error("No documents found. The website structure may have changed.")
    else:
        st.write(f"## Step 2: Searching {len(pdf_links)} Documents")
        with st.spinner("Scanning documents..."):
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
            st.write("1. The server might be blocking our requests")
            st.write("2. Your search term might not exist in these documents")
            st.write("3. The documents might require authentication")

st.markdown("---")
st.write("Note: This version uses session handling to better mimic browser behavior.")