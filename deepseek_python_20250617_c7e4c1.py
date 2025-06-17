import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin

# Configuration
st.set_page_config(page_title="CDSCO SEC Link Finder", layout="wide")
CDSCO_BASE_URL = "https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/"
MAX_DOCS = 10

def get_pdf_links():
    """Fetch PDF links with proper session handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        session = requests.Session()
        response = session.get(CDSCO_BASE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'common_download.jsp' in href:
                full_url = urljoin(CDSCO_BASE_URL, href)
                title = a.text.strip() or f"Document {len(pdf_links)+1}"
                pdf_links.append({
                    'title': title,
                    'url': full_url,
                    'direct_url': f"https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadSECFiles/{title.replace(' ', '_')}.pdf"
                })
                if len(pdf_links) >= MAX_DOCS:
                    break
        
        return pdf_links
    
    except Exception as e:
        st.error(f"Failed to fetch documents: {str(e)}")
        return []

# Streamlit UI
st.title("CDSCO SEC Document Link Finder")
st.write("This tool helps you find and access SEC documents from the CDSCO website")

with st.spinner("Fetching document links..."):
    pdf_links = get_pdf_links()

if not pdf_links:
    st.error("No documents found. The website structure may have changed.")
else:
    st.success(f"Found {len(pdf_links)} documents")
    
    search_term = st.text_input("Filter documents by title:", "")
    
    filtered_links = pdf_links
    if search_term:
        search_term = search_term.lower()
        filtered_links = [doc for doc in pdf_links if search_term in doc['title'].lower()]
        st.write(f"Showing {len(filtered_links)} matching documents")
    
    for doc in filtered_links:
        with st.expander(f"📄 {doc['title']}"):
            st.write("Official Page Link:")
            st.markdown(f"[{CDSCO_BASE_URL}]({CDSCO_BASE_URL})")
            
            st.write("Potential Download Links (may require manual access):")
            st.markdown(f"1. [Standard Download Link]({doc['url']})")
            st.markdown(f"2. [Alternative Download Attempt]({doc['direct_url']})")
            
            st.write("How to access:")
            st.write("1. Right-click any link and select 'Open in new tab'")
            st.write("2. If prompted, complete any authentication required")
            st.write("3. The document should download automatically")

st.markdown("---")
st.write("Note: Due to CDSCO website restrictions, direct PDF text extraction isn't currently possible.")
st.write("For official access, please visit: [CDSCO SEC Page](https://cdsco.gov.in/opencms/opencms/en/Committees/SEC/)")