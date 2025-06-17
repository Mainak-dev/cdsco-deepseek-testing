import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import re
import time
from urllib.parse import urljoin

# Configuration
st.set_page_config(page_title="CDSCO SEC Debug Search", layout="wide")
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
TEST_LIMIT = 5  # Start with just 5 PDFs for debugging

# Debugging mode
DEBUG = True  # Set to False for normal operation

def get_pdf_links():
    """Fetch PDF links with enhanced error handling"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(CDSCO_BASE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'common_download.jsp' in href:
                full_url = urljoin(CDSCO_BASE_URL, href)
                links.append({
                    'url': full_url,
                    'title': a.text.strip() or f"Document {len(links)+1}",
                    'href': href
                })
                if len(links) >= TEST_LIMIT:
                    break
        
        if DEBUG:
            st.write("🔍 Debug: Found links:", links[:3])  # Show first 3 for inspection
        return links
    
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")
        return []

def extract_text_with_debug(pdf_info):
    """Extract text with detailed debugging"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(pdf_info['url'], headers=headers, timeout=30)
        
        if DEBUG:
            st.write(f"🔍 Debug: Fetching {pdf_info['title']} - Status: {response.status_code}")
            if response.status_code != 200:
                st.write(f"⚠️ Failed to fetch: {response.content[:100]}...")
        
        with io.BytesIO(response.content) as f:
            try:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f" PAGE {i+1}: " + page_text + " "
                    elif DEBUG:
                        st.write(f"⚠️ Empty page {i+1} in {pdf_info['title']}")
                
                if DEBUG and text:
                    st.write(f"📄 Sample text from {pdf_info['title']}:", text[:200] + "...")
                elif DEBUG:
                    st.write(f"⚠️ No text extracted from {pdf_info['title']}")
                
                return text
            
            except Exception as e:
                if DEBUG:
                    st.write(f"❌ PDF read error in {pdf_info['title']}: {str(e)}")
                return ""
    
    except Exception as e:
        if DEBUG:
            st.write(f"❌ Failed to process {pdf_info['title']}: {str(e)}")
        return ""

def search_with_diagnostics(pdf_list, keyword):
    """Search with detailed diagnostics"""
    results = []
    keyword = keyword.lower().strip()
    
    if DEBUG:
        st.write("🔍 Starting search for:", keyword)
    
    for i, pdf in enumerate(pdf_list[:TEST_LIMIT]):
        st.write(f"🔎 Processing {i+1}/{len(pdf_list)}: {pdf['title']}")
        
        text = extract_text_with_debug(pdf)
        if not text:
            continue
            
        text_lower = text.lower()
        matches = list(re.finditer(re.escape(keyword), text_lower))
        
        if DEBUG:
            st.write(f"ℹ️ Found {len(matches)} matches in {pdf['title']}")
        
        if matches:
            samples = []
            for match in matches[:3]:  # Get first 3 matches
                start = max(0, match.start()-20)
                end = min(len(text), match.end()+20)
                samples.append(text[start:end].strip())
            
            results.append({
                'title': pdf['title'],
                'url': pdf['url'],
                'count': len(matches),
                'samples': samples,
                'raw_text': text[:500] + "..." if DEBUG else None
            })
        
        time.sleep(1)  # Be polite to the server
    
    return results

# Streamlit Interface
st.title("CDSCO SEC Debug Search Tool")
st.warning("DEBUG MODE ENABLED - Showing diagnostic information")

keyword = st.text_input("Enter keyword to search:", "clinical")  # Default test term
search_btn = st.button("Run Diagnostic Search")

if search_btn:
    st.write("## Step 1: Fetching Document Links")
    pdf_links = get_pdf_links()
    
    if not pdf_links:
        st.error("No documents found - check connection or website structure")
    else:
        st.write(f"Found {len(pdf_links)} documents. Beginning search...")
        
        st.write("## Step 2: Searching Documents")
        results = search_with_diagnostics(pdf_links, keyword)
        
        st.write("## Step 3: Results")
        if results:
            st.success(f"Found {len(results)} matching documents")
            for doc in results:
                with st.expander(f"📄 {doc['title']} ({doc['count']} matches)"):
                    st.write(f"**URL:** {doc['url']}")
                    st.write("**Sample matches:**")
                    for sample in doc['samples']:
                        highlighted = sample.replace(keyword, f"**{keyword}**")
                        st.write("- ..." + highlighted + "...")
                    
                    if DEBUG and doc['raw_text']:
                        st.write("**First 500 chars:**", doc['raw_text'])
        else:
            st.error("No matches found - see diagnostics above")
            
            st.write("### Debugging Tips:")
            st.write("1. Try simpler search terms (e.g., 'study' instead of 'clinical study')")
            st.write("2. Check if PDFs contain text (some may be image scans)")
            st.write("3. Verify the website still uses the same structure")

st.markdown("---")
st.write("Debug information will help identify why matches aren't being found.")