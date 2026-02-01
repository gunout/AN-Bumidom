import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, quote, urlencode
import io

# Configuration
st.set_page_config(
    page_title="Archives BUMIDOM - Recherche Réelle", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Archives BUMIDOM - Recherche en Temps Réel")
st.markdown("Recherche directe sur le site des Archives de l'Assemblée Nationale")

@st.cache_data(ttl=3600)
def get_headers():
    """Retourne les headers pour les requêtes HTTP"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://archives.assemblee-nationale.fr/'
    }

def search_archives_direct(query="bumidom", page=1, per_page=10):
    """Recherche directe sur le site des archives"""
    
    base_url = "https://archives.assemblee-nationale.fr"
    all_results = []
    
    try:
        # D'abord, accéder à la page principale pour obtenir le token CSRF
        session = requests.Session()
        main_response = session.get(base_url, headers=get_headers(), timeout=10)
        
        if main_response.status_code != 200:
            st.error(f"Erreur d'accès au site: {main_response.status_code}")
            return []
        
        # Analyser la page pour trouver le formulaire de recherche
        soup = BeautifulSoup(main_response.content, 'html.parser')
        
        # Chercher le formulaire de recherche
        search_form = None
        search_input = None
        
        # Méthode 1: Chercher un input de recherche
        search_inputs = soup.find_all('input', {
            'type': ['search', 'text'],
            'name': ['q', 'query', 'search', 'recherche']
        })
        
        for input_elem in search_inputs:
            if input_elem.get('placeholder', '').lower() in ['rechercher', 'search', 'chercher']:
                search_input = input_elem
                # Trouver le formulaire parent
                search_form = input_elem.find_parent('form')
                break
        
        # Méthode 2: Chercher le formulaire Google CSE
        if not search_form:
            google_forms = soup.find_all('form', {'action': re.compile(r'google', re.I)})
            if google_forms:
                search_form = google_forms[0]
        
        # Méthode 3: Chercher des scripts avec configuration CSE
        if not search_form:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'google' in script.string and 'search' in script.string:
                    # Extraire l'ID CSE
                    cse_match = re.search(r'cx\s*:\s*["\']([^"\']+)["\']', script.string)
                    if cse_match:
                        cse_id = cse_match.group(1)
                        st.info(f"Google CSE ID trouvé: {cse_id}")
                        return search_via_google_cse(cse_id, query, page, per_page)
        
        # Si on a trouvé un formulaire, l'utiliser
        if search_form:
            form_action = search_form.get('action', '')
            form_method = search_form.get('method', 'get').lower()
            
            if form_action:
                search_url = urljoin(base_url, form_action)
            else:
                search_url = base_url + '/search'
            
            # Préparer les paramètres
            params = {}
            if search_input and search_input.get('name'):
                params[search_input.get('name')] = query
            
            # Ajouter d'autres champs cachés
            hidden_inputs = search_form.find_all('input', {'type': 'hidden'})
            for hidden in hidden_inputs:
                if hidden.get('name') and hidden.get('value'):
                    params[hidden.get('name')] = hidden.get('value')
            
            # Ajouter la pagination
            params['start'] = (page - 1) * per_page
            
            # Faire la recherche
            if form_method == 'post':
                response = session.post(search_url, data=params, headers=get_headers(), timeout=15)
            else:
                response = session.get(search_url, params=params, headers=get_headers(), timeout=15)
            
            if response.status_code == 200:
                results = parse_search_results(response.content, page)
                return results
        
        # Si aucune méthode ne fonctionne, essayer l'URL de recherche directe
        return try_direct_search_urls(base_url, query, page, per_page, session)
        
    except Exception as e:
        st.error(f"Erreur lors de la recherche: {str(e)[:200]}")
        return []

def try_direct_search_urls(base_url, query, page, per_page, session):
    """Essayer différentes URLs de recherche directes"""
    
    # URLs de recherche courantes
    search_patterns = [
        f"{base_url}/search?q={quote(query)}&start={(page-1)*per_page}",
        f"{base_url}/recherche?query={quote(query)}&page={page}",
        f"{base_url}/cri/search?q={quote(query)}&p={page}",
        f"{base_url}/advanced-search?q={quote(query)}&start={(page-1)*per_page}",
        f"{base_url}/archives/search?q={quote(query)}&page={page}",
        f"{base_url}/?s={quote(query)}&paged={page}",
    ]
    
    for url in search_patterns:
        try:
            response = session.get(url, headers=get_headers(), timeout=10)
            if response.status_code == 200:
                results = parse_search_results(response.content, page)
                if results:
                    st.success(f"Pattern trouvé: {url}")
                    return results
        except:
            continue
    
    return []

def search_via_google_cse(cse_id, query, page, per_page):
    """Recherche via Google Custom Search Engine"""
    
    try:
        # URL de l'API Google CSE
        api_url = "https://www.googleapis.com/customsearch/v1"
        
        # Paramètres (note: nécessite une clé API)
        params = {
            'key': 'AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY',  # Clé API Google générique (peut être limitée)
            'cx': cse_id,
            'q': query,
            'start': (page - 1) * per_page + 1,
            'num': per_page,
            'hl': 'fr',
            'lr': 'lang_fr'
        }
        
        response = requests.get(api_url, params=params, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return parse_google_cse_results(data, page)
        else:
            st.warning(f"API Google CSE: {response.status_code}")
            return []
            
    except Exception as e:
        st.warning(f"Erreur Google CSE: {str(e)[:100]}")
        return []

def parse_search_results(html_content, page_num):
    """Parse les résultats de recherche"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # Chercher les résultats Google CSE
    cse_results = soup.find_all('div', class_=['gsc-webResult', 'gsc-result', 'gs-webResult', 'gs-result'])
    if cse_results:
        return parse_cse_results(cse_results, page_num)
    
    # Chercher les résultats de recherche génériques
    generic_results = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'(result|item|document|search)', re.I))
    
    for idx, result in enumerate(generic_results[:20]):  # Limiter à 20 résultats
        try:
            doc = extract_generic_result_info(result, idx, page_num)
            if doc:
                results.append(doc)
        except Exception as e:
            continue
    
    # Si pas de résultats génériques, chercher les liens PDF
    if not results:
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        for idx, link in enumerate(pdf_links[:20]):
            try:
                doc = extract_pdf_link_info(link, idx, page_num)
                if doc:
                    results.append(doc)
            except:
                continue
    
    return results

def parse_cse_results(cse_elements, page_num):
    """Parse les résultats Google CSE"""
    
    results = []
    
    for idx, element in enumerate(cse_elements):
        try:
            # Titre et URL
            title_elem = element.find('a', class_='gs-title')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            
            # Snippet
            snippet_elem = element.find('div', class_='gs-snippet')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Date
            date_match = re.search(r'(\d{1,2}\s+\w+\.?\s+\d{4})', snippet)
            date = date_match.group(1) if date_match else ""
            
            # Année
            year = None
            if date:
                year_match = re.search(r'(\d{4})', date)
                if year_match:
                    year = int(year_match.group(1))
            
            # Type de document
            doc_type = determine_document_type(title, snippet)
            
            # Législature
            legislature = extract_legislature(title, url)
            
            # Fichier
            file_name = url.split('/')[-1] if '/' in url else ""
            
            # Mentions BUMIDOM
            mentions = count_mentions(title + " " + snippet)
            
            results.append({
                'id': f"CSE-P{page_num}-{idx+1:03d}",
                'titre': title,
                'url': url,
                'extrait': snippet[:300] + "..." if len(snippet) > 300 else snippet,
                'date': date,
                'année': year,
                'type': doc_type,
                'législature': legislature,
                'fichier': file_name,
                'mentions': mentions,
                'page_source': page_num,
                'source': 'Google CSE'
            })
            
        except Exception as e:
            continue
    
    return results

def parse_google_cse_results(data, page_num):
    """Parse les résultats de l'API Google CSE"""
    
    results = []
    
    if 'items' in data:
        for idx, item in enumerate(data['items']):
            try:
                title = item.get('title', '')
                url = item.get('link', '')
                snippet = item.get('snippet', '')
                
                # Date
                date_info = item.get('pagemap', {}).get('metatags', [{}])[0]
                date = date_info.get('article:published_time', date_info.get('dc.date', ''))
                
                # Année
                year = None
                year_match = re.search(r'(\d{4})', date) if date else None
                if year_match:
                    year = int(year_match.group(1))
                
                # Type
                doc_type = determine_document_type(title, snippet)
                
                # Législature
                legislature = extract_legislature(title, url)
                
                # Fichier
                file_name = url.split('/')[-1] if '/' in url else ""
                
                # Mentions
                mentions = count_mentions(title + " " + snippet)
                
                results.append({
                    'id': f"API-P{page_num}-{idx+1:03d}",
                    'titre': title,
                    'url': url,
                    'extrait': snippet[:300] + "..." if len(snippet) > 300 else snippet,
                    'date': date[:10] if date else "",
                    'année': year,
                    'type': doc_type,
                    'législature': legislature,
                    'fichier': file_name,
                    'mentions': mentions,
                    'page_source': page_num,
                    'source': 'Google CSE API'
                })
                
            except Exception as e:
                continue
    
    return results

def extract_generic_result_info(element, idx, page_num):
    """Extrait les informations d'un résultat générique"""
    
    try:
        # Titre et URL
        title_elem = element.find(['h2', 'h3', 'h4', 'h5', 'a'])
        if not title_elem:
            return None
        
        if title_elem.name == 'a':
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
        else:
            title = title_elem.get_text(strip=True)
            link_elem = title_elem.find_next('a')
            url = link_elem.get('href', '') if link_elem else ""
        
        # Description
        desc_elem = element.find(['p', 'div', 'span'], class_=re.compile(r'(desc|summary|snippet|extrait)', re.I))
        snippet = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Date
        date_elem = element.find(['time', 'span', 'div'], class_=re.compile(r'(date|time|pub)', re.I))
        date = date_elem.get_text(strip=True) if date_elem else ""
        
        # Année
        year = extract_year_from_text(title + " " + snippet + " " + date)
        
        # Type
        doc_type = determine_document_type(title, snippet)
        
        # Législature
        legislature = extract_legislature(title, url)
        
        # Fichier
        file_name = url.split('/')[-1] if '/' in url else ""
        
        # Mentions
        mentions = count_mentions(title + " " + snippet)
        
        return {
            'id': f"GEN-P{page_num}-{idx+1:03d}",
            'titre': title,
            'url': make_absolute_url(url),
            'extrait': snippet[:200] + "..." if len(snippet) > 200 else snippet,
            'date': date,
            'année': year,
            'type': doc_type,
            'législature': legislature,
            'fichier': file_name,
            'mentions': mentions,
            'page_source': page_num,
            'source': 'Recherche générique'
        }
        
    except Exception as e:
        return None

def extract_pdf_link_info(link_element, idx, page_num):
    """Extrait les informations d'un lien PDF"""
    
    try:
        title = link_element.get_text(strip=True) or f"Document PDF {idx+1}"
        url = link_element.get('href', '')
        
        # Chercher des informations autour du lien
        parent = link_element.parent
        context = parent.get_text(strip=True) if parent else ""
        
        # Date
        date_match = re.search(r'(\d{1,2}\s+\w+\.?\s+\d{4})', context)
        date = date_match.group(1) if date_match else ""
        
        # Année
        year = extract_year_from_text(context)
        
        # Type
        doc_type = "PDF"
        if 'cri' in url.lower():
            doc_type = "CRI"
        elif 'constitution' in context.lower():
            doc_type = "Constitution"
        elif 'journal' in context.lower():
            doc_type = "Journal Officiel"
        
        # Législature
        legislature = extract_legislature_from_url(url)
        
        # Fichier
        file_name = url.split('/')[-1] if '/' in url else ""
        
        # Mentions
        mentions = count_mentions(title + " " + context)
        
        return {
            'id': f"PDF-P{page_num}-{idx+1:03d}",
            'titre': title,
            'url': make_absolute_url(url),
            'extrait': context[:150] + "..." if len(context) > 150 else context,
            'date': date,
            'année': year,
            'type': doc_type,
            'législature': legislature,
            'fichier': file_name,
            'mentions': mentions,
            'page_source': page_num,
            'source': 'Lien PDF'
        }
        
    except Exception as e:
        return None

def make_absolute_url(url):
    """Convertit une URL relative en absolue"""
    if not url:
        return ""
    
    base_url = "https://archives.assemblee-nationale.fr"
    
    if url.startswith('http'):
        return url
    elif url.startswith('/'):
        return base_url + url
    elif url.startswith('./'):
        return base_url + url[1:]
    else:
        return base_url + '/' + url

def determine_document_type(title, snippet):
    """Détermine le type de document"""
    text = (title + " " + snippet).lower()
    
    if any(x in text for x in ['constitution', 'constit']):
        return "Constitution"
    elif any(x in text for x in ['journal officiel', 'j.o.', 'jo ']):
        return "Journal Officiel"
    elif 'compte rendu' in text:
        return "Compte Rendu"
    elif any(x in text for x in ['cri', 'compte rendu intégral']):
        return "CRI"
    elif 'séance' in text or 'seance' in text:
        return "Séance"
    elif 'débat' in text or 'debat' in text:
        return "Débat"
    elif 'rapport' in text:
        return "Rapport"
    elif 'question' in text or 'qst' in text:
        return "Question"
    else:
        return "Document"

def extract_legislature(title, url):
    """Extrait la législature"""
    # Chercher dans le titre
    leg_match = re.search(r'(\d+)(?:è?me|ème|°|\')\s*(?:législature|legislature|leg)', title, re.I)
    if leg_match:
        return f"{leg_match.group(1)}ème"
    
    # Chercher dans l'URL
    url_leg_match = re.search(r'/(\d)/cri/', url) or re.search(r'/(\d)/qst/', url)
    if url_leg_match:
        return f"{url_leg_match.group(1)}ème"
    
    return ""

def extract_legislature_from_url(url):
    """Extrait la législature depuis l'URL"""
    match = re.search(r'/(\d)/cri/', url) or re.search(r'/(\d)/qst/', url)
    if match:
        return f"{match.group(1)}ème"
    return ""

def extract_year_from_text(text):
    """Extrait l'année du texte"""
    match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if match:
        try:
            return int(match.group(1))
        except:
            return None
    return None

def count_mentions(text):
    """Compte les mentions de BUMIDOM"""
    if not text:
        return 0
    text_lower = text.lower()
    return text_lower.count('bumidom')

def test_document_access(url):
    """Teste l'accessibilité d'un document"""
    if not url:
        return {'accessible': False, 'error': 'URL vide'}
    
    try:
        response = requests.head(url, headers=get_headers(), timeout=10, allow_redirects=True)
        return {
            'accessible': response.status_code == 200,
            'status': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'is_pdf': 'pdf' in response.headers.get('content-type', '').lower()
        }
    except Exception as e:
        return {'accessible': False, 'error': str(e)[:100]}

def download_document(url):
    """Télécharge un document"""
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Erreur: {str(e)[:100]}")
    return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Recherche Archives AN")
        
        st.markdown("### 🔍 Paramètres")
        
        search_query = st.text_input("Terme de recherche:", value="bumidom")
        total_pages = st.slider("Nombre de pages:", 1, 10, 3)
        
        st.markdown("### 🎯 Filtres")
        
        col_year1, col_year2 = st.columns(2)
        with col_year1:
            min_year = st.number_input("Depuis:", 1900, 2025, 1960)
        with col_year2:
            max_year = st.number_input("Jusqu'à:", 1900, 2025, 1990)
        
        doc_types = st.multiselect(
            "Types de documents:",
            ["Tous", "Constitution", "Journal Officiel", "Compte Rendu", "CRI", 
             "Séance", "Débat", "Rapport", "Question", "PDF", "Document"],
            default=["Tous"]
        )
        
        st.markdown("### ⚡ Options")
        
        search_method = st.selectbox(
            "Méthode de recherche:",
            ["Auto-détection", "Google CSE", "Recherche directe", "Liens PDF"]
        )
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            search_btn = st.button("🔍 Lancer la recherche", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state.search_results = None
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("### ℹ️ Informations")
        st.info(f"""
        **Recherche:**
        - Terme: {search_query}
        - Pages: {total_pages}
        - Période: {min_year}-{max_year}
        - Méthode: {search_method}
        
        **Site cible:**
        archives.assemblee-nationale.fr
        """)
    
    # Initialisation
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'search_stats' not in st.session_state:
        st.session_state.search_stats = {}
    
    # Recherche
    if search_btn:
        with st.spinner("Recherche en cours..."):
            all_results = []
            stats = {
                'total_documents': 0,
                'successful_pages': 0,
                'failed_pages': 0,
                'start_time': time.time()
            }
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num in range(1, total_pages + 1):
                status_text.text(f"Page {page_num}/{total_pages}...")
                
                try:
                    # Recherche selon la méthode choisie
                    if search_method == "Google CSE":
                        # Utiliser Google CSE (avec ID hardcodé pour le site)
                        cse_id = "014917347718038151697:kltwr00yvbk"
                        page_results = search_via_google_cse(cse_id, search_query, page_num, 10)
                    elif search_method == "Recherche directe":
                        page_results = search_archives_direct(search_query, page_num, 10)
                    elif search_method == "Liens PDF":
                        # Recherche spécifique PDF
                        page_results = search_pdf_documents(search_query, page_num)
                    else:  # Auto-détection
                        page_results = search_archives_direct(search_query, page_num, 10)
                    
                    if page_results:
                        all_results.extend(page_results)
                        stats['successful_pages'] += 1
                        st.success(f"✓ Page {page_num}: {len(page_results)} résultats")
                    else:
                        stats['failed_pages'] += 1
                        st.warning(f"⚠ Page {page_num}: Aucun résultat")
                        
                except Exception as e:
                    stats['failed_pages'] += 1
                    st.error(f"✗ Page {page_num}: Erreur - {str(e)[:100]}")
                
                # Mise à jour progression
                progress_bar.progress(page_num / total_pages)
                
                # Pause pour éviter le blocage
                time.sleep(1)
            
            stats['total_documents'] = len(all_results)
            stats['end_time'] = time.time()
            stats['duration'] = stats['end_time'] - stats['start_time']
            
            st.session_state.search_results = all_results
            st.session_state.search_stats = stats
            
            progress_bar.empty()
            status_text.empty()
            
            if all_results:
                st.success(f"✅ Recherche terminée ! {len(all_results)} documents trouvés en {stats['duration']:.1f}s.")
            else:
                st.warning("⚠️ Aucun document trouvé.")
    
    # Affichage des résultats
    if st.session_state.search_results is not None:
        results = st.session_state.search_results
        stats = st.session_state.search_stats
        
        if results:
            # Statistiques
            st.subheader("📊 Statistiques de recherche")
            
            col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
            
            with col_stat1:
                st.metric("Documents", stats.get('total_documents', 0))
            with col_stat2:
                st.metric("Pages réussies", stats.get('successful_pages', 0))
            with col_stat3:
                st.metric("Durée", f"{stats.get('duration', 0):.1f}s")
            with col_stat4:
                years = len(set(r.get('année') for r in results if r.get('année')))
                st.metric("Années", years)
            with col_stat5:
                total_mentions = sum(r.get('mentions', 0) for r in results)
                st.metric("Mentions", total_mentions)
            
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
                
                filtered_results.append(doc)
            
            st.info(f"📄 {len(filtered_results)} documents après filtrage")
            
            # Affichage des documents
            st.subheader("📋 Documents trouvés")
            
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
                        'Source': doc.get('source', '')[:10]
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
                                st.markdown(f"**Source:** {selected_doc.get('source', '')}")
                                st.markdown(f"**Législature:** {selected_doc.get('législature', '')}")
                                st.markdown(f"**Année:** {selected_doc.get('année', '')}")
                                st.markdown(f"**Date:** {selected_doc.get('date', '')}")
                                st.markdown(f"**Page source:** {selected_doc.get('page_source', '')}")
                                st.markdown(f"**Mentions BUMIDOM:** {selected_doc.get('mentions', 0)}")
                                st.markdown(f"**Fichier:** {selected_doc.get('fichier', '')}")
                                
                                if selected_doc.get('extrait'):
                                    st.markdown("**Extrait:**")
                                    extrait = selected_doc['extrait']
                                    highlighted = re.sub(
                                        r'(bumidom|b\.u\.m\.i\.d\.o\.m\.)',
                                        r'**\1**',
                                        extrait,
                                        flags=re.IGNORECASE
                                    )
                                    st.markdown(f"> {highlighted}")
                                
                                if selected_doc.get('url'):
                                    st.markdown("**URL:**")
                                    st.code(selected_doc['url'])
                            
                            with col_detail2:
                                st.markdown("**Actions:**")
                                
                                if selected_doc.get('url'):
                                    # Test d'accès
                                    if st.button("🔗 Tester l'accès", key=f"test_{selected_id}"):
                                        access_info = test_document_access(selected_doc['url'])
                                        
                                        if access_info.get('accessible'):
                                            st.success(f"✅ Accessible")
                                            st.info(f"Code: {access_info.get('status')}")
                                            
                                            if access_info.get('is_pdf'):
                                                st.success("📄 Fichier PDF détecté")
                                                
                                                # Téléchargement
                                                if st.button("📥 Télécharger", key=f"dl_{selected_id}"):
                                                    pdf_content = download_document(selected_doc['url'])
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
                                    st.markdown(f"[🔗 Ouvrir dans navigateur]({selected_doc['url']})")
            
            # Analyses
            st.subheader("📈 Analyses")
            
            tab1, tab2, tab3 = st.tabs(["Par année", "Par type", "Par source"])
            
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
                source_counts = {}
                for doc in filtered_results:
                    source = doc.get('source', 'Inconnu')
                    if source not in source_counts:
                        source_counts[source] = 0
                    source_counts[source] += 1
                
                if source_counts:
                    df_sources = pd.DataFrame({
                        'Source': list(source_counts.keys()),
                        'Documents': list(source_counts.values())
                    })
                    
                    st.bar_chart(df_sources.set_index('Source'))
            
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
                        file_name=f"bumidom_recherche_{timestamp}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = json.dumps(filtered_results, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json_data,
                        file_name=f"bumidom_recherche_{timestamp}.json",
                        mime="application/json"
                    )
                
                elif export_format == "Excel":
                    df_export = pd.DataFrame(filtered_results)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Résultats')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=excel_data,
                        file_name=f"bumidom_recherche_{timestamp}.xlsx",
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
            st.warning("⚠️ Aucun document trouvé")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🔍 Recherche Archives BUMIDOM
        
        ### 🎯 Accès direct aux Archives de l'Assemblée Nationale
        
        Cette application permet de rechercher **en temps réel** les documents contenant "BUMIDOM" dans les archives de l'Assemblée Nationale.
        
        ### 🌐 Méthodes de recherche disponibles:
        
        1. **Auto-détection** - Détecte automatiquement le moteur de recherche
        2. **Google CSE** - Utilise le moteur Google Custom Search intégré
        3. **Recherche directe** - Parcourt les formulaires de recherche
        4. **Liens PDF** - Extrait directement les liens PDF
        
        ### 📊 Ce que vous pouvez faire:
        
        - Rechercher "bumidom" sur plusieurs pages
        - Filtrer par année (1960-1990)
        - Trier par type de document
        - Tester l'accessibilité des PDFs
        - Télécharger les documents
        - Exporter les résultats
        
        ### 🚀 Pour commencer:
        
        1. Configurez les paramètres dans la sidebar
        2. Cliquez sur **"Lancer la recherche"**
        3. Explorez les résultats avec les filtres
        4. Téléchargez ou exportez les données
        """)
        
        with st.expander("ℹ️ Informations techniques"):
            st.markdown("""
            ### Structure du site cible:
            
            Le site `archives.assemblee-nationale.fr` utilise:
            
            1. **Google Custom Search Engine (CSE)** pour la recherche
            2. **URLs structurées** pour les documents PDF
            3. **Patterns prévisibles** pour les archives par législature
            
            ### Exemples d'URLs:
            
            ```
            https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf
            https://archives.assemblee-nationale.fr/2/qst/2-qst-1964-09-12.pdf
            ```
            
            ### Limitations connues:
            
            - Le site peut bloquer les requêtes trop rapides
            - Certains documents nécessitent une authentification
            - La recherche Google CSE peut avoir des limites
            """)

def search_pdf_documents(query, page_num):
    """Recherche spécifique pour les documents PDF"""
    
    base_url = "https://archives.assemblee-nationale.fr"
    
    try:
        # Essayer différentes URLs contenant "cri" (Comptes Rendus Intégraux)
        search_urls = [
            f"{base_url}/cri?q={quote(query)}&p={page_num}",
            f"{base_url}/archives/search?type=pdf&q={quote(query)}&page={page_num}",
            f"{base_url}/advanced-search?format=pdf&q={quote(query)}&start={(page_num-1)*10}"
        ]
        
        session = requests.Session()
        
        for url in search_urls:
            try:
                response = session.get(url, headers=get_headers(), timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Chercher tous les liens PDF
                    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    
                    results = []
                    for idx, link in enumerate(pdf_links[:10]):
                        doc = extract_pdf_link_info(link, idx, page_num)
                        if doc:
                            results.append(doc)
                    
                    if results:
                        return results
            except:
                continue
        
        return []
        
    except Exception as e:
        st.warning(f"Erreur recherche PDF: {str(e)[:100]}")
        return []

if __name__ == "__main__":
    main()
