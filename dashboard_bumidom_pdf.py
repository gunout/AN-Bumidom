import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
import io

# Configuration
st.set_page_config(
    page_title="Archives BUMIDOM - Analyse HTML", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Archives BUMIDOM - Extraction depuis HTML")
st.markdown("Analyse des pages de résultats HTML fournies")

# ============================
# DONNÉES RÉELLES DU HTML FOURNI
# ============================

# Extrait du HTML que vous avez fourni (simplifié pour l'exemple)
REAL_HTML_DATA = {
    "page1": """
    <div class="gsc-webResult gsc-result">
        <div class="gs-webResult gs-result">
            <div class="gsc-thumbnail-inside">
                <div class="gs-title">
                    <a class="gs-title" href="https://archives.assemblee-nationale.fr/6/cri/1978-1979-ordinaire2/017.pdf" target="_blank">COMPTE RENDU INTEGRAL - Assemblée nationale - Archives</a>
                </div>
            </div>
            <div class="gsc-url-top">
                <div class="gs-bidi-start-align gs-visibleUrl gs-visibleUrl-breadcrumb">
                    <span>archives.assemblee-nationale.fr</span><span> › cri</span><span> › 1978-1979-ordinaire2</span>
                </div>
            </div>
            <div class="gsc-table-result">
                <div class="gsc-table-cell-snippet-close">
                    <div class="gs-title gsc-table-cell-thumbnail gsc-thumbnail-left">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/6/cri/1978-1979-ordinaire2/017.pdf" target="_blank">COMPTE RENDU INTEGRAL - Assemblée nationale - Archives</a>
                    </div>
                    <div class="gs-fileFormat">
                        <span class="gs-fileFormat">Format de fichier&nbsp;: </span>
                        <span class="gs-fileFormatType">PDF/Adobe Acrobat</span>
                    </div>
                    <div class="gs-bidi-start-align gs-snippet" dir="ltr">16 févr. 2025 <b>...</b> <b>Bumidom</b> faire une formation professionnelle en métropole . En effet, la somme allouée aux stagiaires qui se trouvent loin de leur foyer et&nbsp;...</div>
                </div>
            </div>
        </div>
    </div>
    <div class="gsc-webResult gsc-result">
        <div class="gs-webResult gs-result">
            <div class="gsc-thumbnail-inside">
                <div class="gs-title">
                    <a class="gs-title" href="https://archives.assemblee-nationale.fr/4/qst/4-qst-1969-08-23.pdf" target="_blank">JOURNAL OFFICIEL - Assemblée nationale - Archives</a>
                </div>
            </div>
            <div class="gsc-url-top">
                <div class="gs-bidi-start-align gs-visibleUrl gs-visibleUrl-breadcrumb">
                    <span>archives.assemblee-nationale.fr</span><span> › qst</span><span> › 4-qst-1969-08-23</span>
                </div>
            </div>
            <div class="gsc-table-result">
                <div class="gsc-table-cell-snippet-close">
                    <div class="gs-title gsc-table-cell-thumbnail gsc-thumbnail-left">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/4/qst/4-qst-1969-08-23.pdf" target="_blank">JOURNAL OFFICIEL - Assemblée nationale - Archives</a>
                    </div>
                    <div class="gs-fileFormat">
                        <span class="gs-fileFormat">Format de fichier&nbsp;: </span>
                        <span class="gs-fileFormatType">PDF/Adobe Acrobat</span>
                    </div>
                    <div class="gs-bidi-start-align gs-snippet" dir="ltr">30 déc. 2025 <b>...</b> en métropole au titre du <b>Bumidom</b> la même année, M . le minist re de l 'économie et des finances indiquait dans sa réponse qu ' il n ' était.</div>
                </div>
            </div>
        </div>
    </div>
    """,
    "page2": """
    <div class="gsc-webResult gsc-result">
        <div class="gs-webResult gs-result">
            <div class="gsc-thumbnail-inside">
                <div class="gs-title">
                    <a class="gs-title" href="https://archives.assemblee-nationale.fr/2/cri/1964-1965-ordinaire1/021.pdf" target="_blank">Assemblée nationale - Archives</a>
                </div>
            </div>
            <div class="gsc-url-top">
                <div class="gs-bidi-start-align gs-visibleUrl gs-visibleUrl-breadcrumb">
                    <span>archives.assemblee-nationale.fr</span><span> › cri</span><span> › 1964-1965-ordinaire1</span>
                </div>
            </div>
            <div class="gsc-table-result">
                <div class="gsc-table-cell-snippet-close">
                    <div class="gs-title gsc-table-cell-thumbnail gsc-thumbnail-left">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/2/cri/1964-1965-ordinaire1/021.pdf" target="_blank">Assemblée nationale - Archives</a>
                    </div>
                    <div class="gs-fileFormat">
                        <span class="gs-fileFormat">Format de fichier&nbsp;: </span>
                        <span class="gs-fileFormatType">PDF/Adobe Acrobat</span>
                    </div>
                    <div class="gs-bidi-start-align gs-snippet" dir="ltr">écrit, ce n'est pas le <b>BUMIDOM</b> qui a mis à la disposition des migrants ... le <b>BUMIDOM</b> ayant apporté toutefois son aide, sous la forme d'une subvention&nbsp;...</div>
                </div>
            </div>
        </div>
    </div>
    <div class="gsc-webResult gsc-result">
        <div class="gs-webResult gs-result">
            <div class="gsc-thumbnail-inside">
                <div class="gs-title">
                    <a class="gs-title" href="https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/051.pdf" target="_blank">JOURNAL OFFICIEL - Assemblée nationale - Archives</a>
                </div>
            </div>
            <div class="gsc-url-top">
                <div class="gs-bidi-start-align gs-visibleUrl gs-visibleUrl-breadcrumb">
                    <span>archives.assemblee-nationale.fr</span><span> › cri</span><span> › 1976-1977-ordinaire2</span>
                </div>
            </div>
            <div class="gsc-table-result">
                <div class="gsc-table-cell-snippet-close">
                    <div class="gs-title gsc-table-cell-thumbnail gsc-thumbnail-left">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/051.pdf" target="_blank">JOURNAL OFFICIEL - Assemblée nationale - Archives</a>
                    </div>
                    <div class="gs-fileFormat">
                        <span class="gs-fileFormat">Format de fichier&nbsp;: </span>
                        <span class="gs-fileFormatType">PDF/Adobe Acrobat</span>
                    </div>
                    <div class="gs-bidi-start-align gs-snippet" dir="ltr">De même, il est exact que le <b>Bumidom</b> offre aux candidats à la migration des stages de rattrapage scolaire ou de préformation dans ses centres de Simandes et&nbsp;...</div>
                </div>
            </div>
        </div>
    </div>
    """,
    "page3": """
    <div class="gsc-webResult gsc-result">
        <div class="gs-webResult gs-result">
            <div class="gsc-thumbnail-inside">
                <div class="gs-title">
                    <a class="gs-title" href="https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/065.pdf" target="_blank">JOURS AL OFFICIEL - Assemblée nationale - Archives</a>
                </div>
            </div>
            <div class="gsc-url-top">
                <div class="gs-bidi-start-align gs-visibleUrl gs-visibleUrl-breadcrumb">
                    <span>archives.assemblee-nationale.fr</span><span> › cri</span><span> › 1970-1971-ordinaire1</span>
                </div>
            </div>
            <div class="gsc-table-result">
                <div class="gsc-table-cell-snippet-close">
                    <div class="gs-title gsc-table-cell-thumbnail gsc-thumbnail-left">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/065.pdf" target="_blank">JOURS AL OFFICIEL - Assemblée nationale - Archives</a>
                    </div>
                    <div class="gs-fileFormat">
                        <span class="gs-fileFormat">Format de fichier&nbsp;: </span>
                        <span class="gs-fileFormatType">PDF/Adobe Acrobat</span>
                    </div>
                    <div class="gs-bidi-start-align gs-snippet" dir="ltr">30 avr. 2025 <b>...</b> <b>Bumidom</b> dans des centres de formation professionne'le ; 7.789 dans des centres F. P. A. ; 3.241 dans des centres du <b>Bumidom</b>;. 943 dans d&nbsp;...</div>
                </div>
            </div>
        </div>
    </div>
    """
}

# ============================
# FONCTIONS D'ANALYSE
# ============================

def parse_html_results(html_content, page_num):
    """Parse le HTML pour extraire les résultats"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # Trouver tous les résultats Google CSE
    result_elements = soup.find_all('div', class_=['gsc-webResult', 'gsc-result', 'gs-webResult', 'gs-result'])
    
    if not result_elements:
        # Essayer un autre pattern
        result_elements = soup.find_all(class_=re.compile(r'result|webResult', re.I))
    
    st.info(f"Page {page_num}: {len(result_elements)} résultats trouvés")
    
    for idx, element in enumerate(result_elements):
        try:
            doc = extract_document_info(element, idx, page_num)
            if doc:
                results.append(doc)
        except Exception as e:
            st.warning(f"Erreur extraction {idx}: {str(e)[:50]}")
            continue
    
    return results

def extract_document_info(element, idx, page_num):
    """Extrait les informations d'un document"""
    
    try:
        # Titre et URL
        title_elem = element.find('a', class_='gs-title')
        if not title_elem:
            # Essayer d'autres sélecteurs
            title_elem = element.find('a', href=re.compile(r'\.pdf$', re.I))
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        
        # Snippet/Extrait
        snippet_elem = element.find('div', class_='gs-snippet')
        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
        
        # Date dans le snippet
        date_match = re.search(r'(\d{1,2}\s+\w+\.?\s+\d{4})', snippet)
        date = date_match.group(1) if date_match else ""
        
        # Année
        year = None
        if date:
            year_match = re.search(r'(\d{4})', date)
            if year_match:
                year = int(year_match.group(1))
        
        # Si pas de date dans le snippet, essayer d'extraire de l'URL
        if not year:
            url_year_match = re.search(r'/(\d{4})-(\d{4})/', url)
            if url_year_match:
                year = int(url_year_match.group(1))
        
        # Type de document
        doc_type = determine_doc_type(title, snippet)
        
        # Législature
        legislature = extract_legislature(title, url)
        
        # Fichier
        file_name = url.split('/')[-1] if '/' in url else ""
        
        # Mentions BUMIDOM
        mentions = count_bumidom_mentions(title + " " + snippet)
        
        # Session/Ordinaire
        session = ""
        if 'ordinaire1' in url:
            session = "Session ordinaire 1"
        elif 'ordinaire2' in url:
            session = "Session ordinaire 2"
        elif 'extraordinaire' in url:
            session = "Session extraordinaire"
        
        # Numéro de page dans le PDF (si disponible)
        page_in_pdf = ""
        pdf_page_match = re.search(r'/(\d{3})\.pdf$', url)
        if pdf_page_match:
            page_in_pdf = int(pdf_page_match.group(1))
        
        return {
            'id': f"P{page_num:02d}-{idx+1:03d}",
            'titre': title,
            'url': url,
            'extrait': snippet[:400] + "..." if len(snippet) > 400 else snippet,
            'date': date,
            'année': year,
            'type': doc_type,
            'législature': legislature,
            'session': session,
            'fichier': file_name,
            'page_pdf': page_in_pdf,
            'mentions': mentions,
            'page_source': page_num,
            'index': idx + 1
        }
        
    except Exception as e:
        st.warning(f"Erreur extraction document: {str(e)[:100]}")
        return None

def determine_doc_type(title, snippet):
    """Détermine le type de document"""
    text = (title + " " + snippet).upper()
    
    if 'CONSTITUTION' in text:
        return "Constitution"
    elif 'JOURNAL' in text or 'JOUR' in text or 'OFFICIEL' in text:
        return "Journal Officiel"
    elif 'COMPTE RENDU' in text:
        return "Compte Rendu"
    elif 'SEANCE' in text or 'SÉANCE' in text:
        return "Séance"
    elif 'QUESTION' in text or 'QST' in text:
        return "Question"
    elif 'TABLES' in text or 'ANALYTIQUE' in text:
        return "Tables analytiques"
    elif 'RÉPUBLIQUE' in text:
        return "Débat parlementaire"
    else:
        return "Document"

def extract_legislature(title, url):
    """Extrait la législature"""
    # Chercher dans le titre
    leg_match = re.search(r'(\d+)(?:è?me|ème|°|\')\s*(?:LÉGISLATURE|LEGISLATURE|Leg)', title)
    if leg_match:
        return f"{leg_match.group(1)}ème"
    
    # Chercher dans l'URL (pattern: /2/cri/, /4/qst/, etc.)
    url_match = re.search(r'/(\d)/[a-z]+/', url)
    if url_match:
        leg_num = url_match.group(1)
        return f"{leg_num}ème"
    
    # Essayer d'extraire des années de session
    year_match = re.search(r'/(\d{4})-(\d{4})/', url)
    if year_match:
        year1 = int(year_match.group(1))
        # Déterminer la législature approximative par l'année
        if 1958 <= year1 <= 1962:
            return "1ère"
        elif 1962 <= year1 <= 1967:
            return "2ème"
        elif 1967 <= year1 <= 1968:
            return "3ème"
        elif 1968 <= year1 <= 1973:
            return "4ème"
        elif 1973 <= year1 <= 1978:
            return "5ème"
        elif 1978 <= year1 <= 1981:
            return "6ème"
        elif 1981 <= year1 <= 1986:
            return "7ème"
        elif 1986 <= year1 <= 1988:
            return "8ème"
    
    return ""

def count_bumidom_mentions(text):
    """Compte les mentions de BUMIDOM"""
    if not text:
        return 0
    text_upper = text.upper()
    return text_upper.count('BUMIDOM') + text_upper.count('BUMIDOM')

def test_pdf_access(url):
    """Teste l'accessibilité d'un PDF"""
    if not url:
        return {'accessible': False, 'error': 'URL vide'}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Essayer une requête HEAD d'abord
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        return {
            'accessible': response.status_code == 200,
            'status': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'is_pdf': 'pdf' in response.headers.get('content-type', '').lower(),
            'size': response.headers.get('content-length')
        }
        
    except Exception as e:
        return {'accessible': False, 'error': str(e)[:100]}

def download_pdf(url):
    """Télécharge un PDF"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Erreur téléchargement: {str(e)[:100]}")
    
    return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.markdown("### 🔍 Options d'analyse")
        
        total_pages = st.slider("Pages à analyser:", 1, 10, 3)
        
        st.markdown("### 🎯 Filtres")
        
        col_year1, col_year2 = st.columns(2)
        with col_year1:
            min_year = st.number_input("Année min:", 1900, 2025, 1960)
        with col_year2:
            max_year = st.number_input("Année max:", 1900, 2025, 1990)
        
        doc_types = st.multiselect(
            "Types de documents:",
            ["Tous", "Constitution", "Journal Officiel", "Compte Rendu", 
             "Séance", "Question", "Tables analytiques", "Document"],
            default=["Tous"]
        )
        
        legislatures = st.multiselect(
            "Législatures:",
            ["Toutes", "1ère", "2ème", "3ème", "4ème", "5ème", "6ème", "7ème", "8ème"],
            default=["Toutes"]
        )
        
        st.markdown("### ⚡ Options avancées")
        
        test_access = st.checkbox("Tester l'accès aux PDFs", value=True)
        extract_details = st.checkbox("Extraire les détails", value=True)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            analyze_btn = st.button("🔍 Analyser HTML", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state.analysis_results = None
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("### ℹ️ Information")
        st.info(f"""
        **Configuration:**
        - Pages HTML: {total_pages}
        - Période: {min_year}-{max_year}
        - Types: {len(doc_types)} sélectionnés
        
        **Source:**
        Données réelles extraites du HTML fourni
        """)
    
    # Initialisation
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    
    # Analyse
    if analyze_btn:
        with st.spinner("Analyse des pages HTML..."):
            all_results = []
            stats = {
                'total_documents': 0,
                'pages_analysées': 0,
                'start_time': time.time()
            }
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num in range(1, total_pages + 1):
                status_text.text(f"Analyse page {page_num}/{total_pages}...")
                
                # Récupérer le HTML de la page
                page_key = f"page{page_num}"
                if page_key in REAL_HTML_DATA:
                    html_content = REAL_HTML_DATA[page_key]
                    page_results = parse_html_results(html_content, page_num)
                    
                    if page_results:
                        all_results.extend(page_results)
                        stats['pages_analysées'] += 1
                        st.success(f"✓ Page {page_num}: {len(page_results)} documents")
                    else:
                        st.warning(f"⚠ Page {page_num}: Aucun document extrait")
                else:
                    st.warning(f"⚠ Page {page_num}: Données non disponibles")
                
                progress_bar.progress(page_num / total_pages)
                time.sleep(0.5)
            
            stats['total_documents'] = len(all_results)
            stats['end_time'] = time.time()
            stats['duration'] = stats['end_time'] - stats['start_time']
            
            st.session_state.analysis_results = all_results
            st.session_state.analysis_stats = stats
            
            progress_bar.empty()
            status_text.empty()
            
            if all_results:
                st.success(f"✅ Analyse terminée ! {len(all_results)} documents extraits en {stats['duration']:.1f}s.")
            else:
                st.warning("⚠️ Aucun document extrait")
    
    # Affichage des résultats
    if st.session_state.analysis_results is not None:
        results = st.session_state.analysis_results
        stats = st.session_state.analysis_stats
        
        if results:
            # Statistiques
            st.subheader("📊 Statistiques d'analyse")
            
            col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
            
            with col_stat1:
                st.metric("Documents", stats.get('total_documents', 0))
            with col_stat2:
                st.metric("Pages analysées", stats.get('pages_analysées', 0))
            with col_stat3:
                st.metric("Durée", f"{stats.get('duration', 0):.1f}s")
            with col_stat4:
                years = len(set(r.get('année') for r in results if r.get('année')))
                st.metric("Années", years)
            with col_stat5:
                total_mentions = sum(r.get('mentions', 0) for r in results)
                st.metric("Mentions BUMIDOM", total_mentions)
            
            # Filtrage
            st.subheader("🎯 Filtrage des résultats")
            
            filtered_results = []
            for doc in results:
                # Filtre année
                year = doc.get('année')
                if year and (year < min_year or year > max_year):
                    continue
                
                # Filtre type
                doc_type = doc.get('type', 'Document')
                if "Tous" not in doc_types and doc_type not in doc_types:
                    continue
                
                # Filtre législature
                leg = doc.get('législature', '')
                if "Toutes" not in legislatures and leg not in legislatures:
                    continue
                
                filtered_results.append(doc)
            
            st.info(f"📄 {len(filtered_results)} documents après filtrage")
            
            # Affichage des documents
            st.subheader("📋 Documents extraits")
            
            if filtered_results:
                # Pagination
                items_per_page = st.slider("Documents par page:", 5, 50, 10, key="display_pagination")
                total_pages_view = max(1, (len(filtered_results) + items_per_page - 1) // items_per_page)
                
                if total_pages_view > 1:
                    current_page = st.number_input("Page:", 1, total_pages_view, 1, key="display_page")
                    start_idx = (current_page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(filtered_results))
                    current_docs = filtered_results[start_idx:end_idx]
                    st.caption(f"Documents {start_idx+1}-{end_idx} sur {len(filtered_results)}")
                else:
                    current_docs = filtered_results
                
                # Tableau
                df_data = []
                for doc in current_docs:
                    df_data.append({
                        'ID': doc.get('id', ''),
                        'Titre': doc.get('titre', '')[:60] + ('...' if len(doc.get('titre', '')) > 60 else ''),
                        'Type': doc.get('type', ''),
                        'Année': doc.get('année', ''),
                        'Législature': doc.get('législature', ''),
                        'Page': doc.get('page_source', ''),
                        'Mentions': doc.get('mentions', 0),
                        'Fichier': doc.get('fichier', '')[:15]
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Détail d'un document
                st.subheader("🔍 Détail du document")
                
                if current_docs:
                    doc_options = [f"{doc['id']} - {doc['titre'][:50]}..." for doc in current_docs]
                    selected_option = st.selectbox("Sélectionner un document:", doc_options, key="doc_select")
                    
                    if selected_option:
                        selected_id = selected_option.split(' - ')[0]
                        selected_doc = next((d for d in current_docs if d['id'] == selected_id), None)
                        
                        if selected_doc:
                            col_detail1, col_detail2 = st.columns([2, 1])
                            
                            with col_detail1:
                                st.markdown(f"**ID:** {selected_doc.get('id', '')}")
                                st.markdown(f"**Titre:** {selected_doc.get('titre', '')}")
                                st.markdown(f"**Type:** {selected_doc.get('type', '')}")
                                st.markdown(f"**Législature:** {selected_doc.get('législature', '')}")
                                st.markdown(f"**Session:** {selected_doc.get('session', '')}")
                                st.markdown(f"**Année:** {selected_doc.get('année', '')}")
                                st.markdown(f"**Date:** {selected_doc.get('date', '')}")
                                st.markdown(f"**Page source:** {selected_doc.get('page_source', '')}")
                                st.markdown(f"**Page PDF:** {selected_doc.get('page_pdf', '')}")
                                st.markdown(f"**Mentions BUMIDOM:** {selected_doc.get('mentions', 0)}")
                                st.markdown(f"**Fichier:** {selected_doc.get('fichier', '')}")
                                
                                if selected_doc.get('extrait'):
                                    st.markdown("**Extrait:**")
                                    extrait = selected_doc['extrait']
                                    # Mettre en évidence BUMIDOM
                                    highlighted = re.sub(
                                        r'(BUMIDOM|Bumidom)',
                                        r'**\1**',
                                        extrait
                                    )
                                    st.markdown(f"> {highlighted}")
                                
                                if selected_doc.get('url'):
                                    st.markdown("**URL:**")
                                    st.code(selected_doc['url'])
                            
                            with col_detail2:
                                st.markdown("**Actions:**")
                                
                                if selected_doc.get('url') and test_access:
                                    # Test d'accès
                                    if st.button("🔗 Tester l'accès PDF", key=f"test_{selected_id}"):
                                        access_info = test_pdf_access(selected_doc['url'])
                                        
                                        if access_info.get('accessible'):
                                            st.success(f"✅ Accessible (HTTP {access_info.get('status')})")
                                            
                                            if access_info.get('is_pdf'):
                                                st.success("📄 Fichier PDF détecté")
                                                if access_info.get('size'):
                                                    size_mb = int(access_info.get('size')) / (1024 * 1024)
                                                    st.info(f"Taille: {size_mb:.1f} MB")
                                                
                                                # Téléchargement
                                                if st.button("📥 Télécharger PDF", key=f"dl_{selected_id}"):
                                                    pdf_content = download_pdf(selected_doc['url'])
                                                    if pdf_content:
                                                        filename = selected_doc.get('fichier', f"{selected_id}.pdf")
                                                        st.download_button(
                                                            label="💾 Sauvegarder PDF",
                                                            data=pdf_content,
                                                            file_name=filename,
                                                            mime="application/pdf",
                                                            key=f"save_{selected_id}"
                                                        )
                                            else:
                                                st.warning(f"Type: {access_info.get('content_type', 'Inconnu')}")
                                        else:
                                            st.error(f"❌ Non accessible")
                                            if access_info.get('error'):
                                                st.error(f"Erreur: {access_info.get('error')}")
                                    
                                    # Lien direct
                                    st.markdown(f"[🔗 Ouvrir le PDF]({selected_doc['url']})")
            
            # Analyses
            st.subheader("📈 Analyses")
            
            tab1, tab2, tab3, tab4 = st.tabs(["Par année", "Par type", "Par législature", "Par page"])
            
            with tab1:
                year_counts = {}
                for doc in filtered_results:
                    year = doc.get('année')
                    if year:
                        if year not in year_counts:
                            year_counts[year] = 0
                        year_counts[year] += 1
                
                if year_counts:
                    df_years = pd.DataFrame({
                        'Année': list(year_counts.keys()),
                        'Documents': list(year_counts.values())
                    }).sort_values('Année')
                    
                    st.bar_chart(df_years.set_index('Année'))
            
            with tab2:
                type_counts = {}
                for doc in filtered_results:
                    doc_type = doc.get('type', 'Inconnu')
                    if doc_type not in type_counts:
                        type_counts[doc_type] = 0
                    type_counts[doc_type] += 1
                
                if type_counts:
                    df_types = pd.DataFrame({
                        'Type': list(type_counts.keys()),
                        'Documents': list(type_counts.values())
                    })
                    
                    st.bar_chart(df_types.set_index('Type'))
            
            with tab3:
                leg_counts = {}
                for doc in filtered_results:
                    leg = doc.get('législature')
                    if leg:
                        if leg not in leg_counts:
                            leg_counts[leg] = 0
                        leg_counts[leg] += 1
                
                if leg_counts:
                    df_leg = pd.DataFrame({
                        'Législature': list(leg_counts.keys()),
                        'Documents': list(leg_counts.values())
                    })
                    
                    try:
                        df_leg['Num'] = df_leg['Législature'].str.extract(r'(\d+)').astype(int)
                        df_leg = df_leg.sort_values('Num')
                    except:
                        pass
                    
                    st.bar_chart(df_leg.set_index('Législature'))
            
            with tab4:
                page_counts = {}
                for doc in filtered_results:
                    page = doc.get('page_source', 1)
                    if page not in page_counts:
                        page_counts[page] = 0
                    page_counts[page] += 1
                
                if page_counts:
                    df_pages = pd.DataFrame({
                        'Page': list(page_counts.keys()),
                        'Documents': list(page_counts.values())
                    }).sort_values('Page')
                    
                    st.bar_chart(df_pages.set_index('Page'))
            
            # Export
            st.subheader("💾 Export des données")
            
            export_format = st.selectbox(
                "Format d'export:",
                ["CSV", "JSON", "Excel", "URLs seulement"]
            )
            
            if st.button("📤 Exporter les résultats"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if export_format == "CSV":
                    df_export = pd.DataFrame(filtered_results)
                    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv_data,
                        file_name=f"bumidom_html_{timestamp}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = json.dumps(filtered_results, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json_data,
                        file_name=f"bumidom_html_{timestamp}.json",
                        mime="application/json"
                    )
                
                elif export_format == "Excel":
                    df_export = pd.DataFrame(filtered_results)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Documents')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=excel_data,
                        file_name=f"bumidom_html_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                elif export_format == "URLs seulement":
                    urls = "\n".join([doc.get('url', '') for doc in filtered_results if doc.get('url')])
                    
                    st.download_button(
                        label="📥 Télécharger URLs",
                        data=urls,
                        file_name=f"bumidom_urls_{timestamp}.txt",
                        mime="text/plain"
                    )
        
        else:
            st.warning("⚠️ Aucun document extrait")
    
    else:
        # Écran d'accueil
        st.markdown(""
