import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, quote

# Configuration
st.set_page_config(
    page_title="Scraping BUMIDOM - Archives Nationales", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌐 Scraping des Archives BUMIDOM")
st.markdown("Extraction des documents sans Selenium - Requêtes HTTP directes")

def search_archives_site(query="bumidom", page=1, per_page=10):
    """Recherche sur le site des archives sans Selenium"""
    
    base_url = "https://archives.assemblee-nationale.fr"
    
    # Essayer différentes approches
    search_methods = [
        # Méthode 1: Recherche via paramètres URL
        lambda: search_via_url_params(base_url, query, page, per_page),
        # Méthode 2: Scrap de la page de recherche
        lambda: scrape_search_page(base_url, query, page),
        # Méthode 3: Utilisation de l'API interne
        lambda: try_internal_api(base_url, query, page)
    ]
    
    for method in search_methods:
        try:
            result = method()
            if result and len(result) > 0:
                return result
        except Exception as e:
            st.warning(f"Méthode échouée: {type(e).__name__}")
            continue
    
    return []

def search_via_url_params(base_url, query, page, per_page):
    """Essaye de trouver la structure de recherche via URL"""
    
    # Patterns d'URL de recherche courants
    search_patterns = [
        f"{base_url}/search?q={quote(query)}&page={page}",
        f"{base_url}/recherche?query={quote(query)}&page={page}",
        f"{base_url}/cri/search?q={quote(query)}&page={page}",
        f"{base_url}/cri?query={quote(query)}&page={page}",
        f"{base_url}/advanced-search?search={quote(query)}&p={page}",
        f"{base_url}/archives/search?query={quote(query)}&page={page}",
    ]
    
    for url in search_patterns:
        try:
            response = requests.get(url, timeout=10, headers=get_headers())
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                documents = extract_documents_from_html(soup, page)
                if documents:
                    st.success(f"Pattern trouvé: {url}")
                    return documents
        except Exception as e:
            continue
    
    return []

def scrape_search_page(base_url, query, page):
    """Scrap la page d'accueil pour trouver des résultats"""
    
    try:
        # D'abord, accéder à la page principale
        response = requests.get(base_url, timeout=10, headers=get_headers())
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher des formulaires de recherche
        forms = soup.find_all('form')
        for form in forms:
            if form.find('input', {'type': 'search'}) or form.find('input', {'name': 'q'}):
                # Trouvé un formulaire de recherche
                action = form.get('action', '')
                method = form.get('method', 'get').lower()
                
                # Construire l'URL de recherche
                if action:
                    search_url = urljoin(base_url, action)
                else:
                    search_url = base_url + '/search'
                
                # Faire la recherche
                params = {'q': query, 'page': page}
                if method == 'get':
                    response = requests.get(search_url, params=params, timeout=10, headers=get_headers())
                else:
                    response = requests.post(search_url, data=params, timeout=10, headers=get_headers())
                
                if response.status_code == 200:
                    soup_results = BeautifulSoup(response.content, 'html.parser')
                    documents = extract_documents_from_html(soup_results, page)
                    if documents:
                        return documents
                        
    except Exception as e:
        st.warning(f"Erreur scraping page: {e}")
    
    return []

def try_internal_api(base_url, query, page):
    """Essaye de trouver une API interne"""
    
    # Chercher des endpoints API courants
    api_endpoints = [
        f"{base_url}/api/search",
        f"{base_url}/api/v1/search",
        f"{base_url}/search/api",
        f"{base_url}/cri/api/search"
    ]
    
    for endpoint in api_endpoints:
        try:
            params = {
                'q': query,
                'page': page,
                'format': 'json'
            }
            response = requests.get(endpoint, params=params, timeout=10, headers=get_headers())
            if response.status_code == 200:
                try:
                    data = response.json()
                    documents = parse_api_response(data, page)
                    if documents:
                        st.success(f"API trouvée: {endpoint}")
                        return documents
                except:
                    # Pas du JSON, essayer autre chose
                    continue
        except:
            continue
    
    return []

def get_headers():
    """Retourne les headers pour les requêtes HTTP"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

def extract_documents_from_html(soup, page_num):
    """Extrait les documents depuis le HTML"""
    
    documents = []
    
    # Chercher les résultats de recherche
    result_selectors = [
        '.search-result',
        '.result-item',
        '.document',
        '.item',
        'li.result',
        'div.result',
        'article',
        '.list-item',
        'tr[class*="result"]',
        '[class*="search"] [class*="item"]',
        '.search-results li',
        '.results .item'
    ]
    
    for selector in result_selectors:
        results = soup.select(selector)
        if len(results) > 2:  # Au moins quelques résultats
            st.info(f"Trouvé {len(results)} résultats avec: {selector}")
            
            for idx, result in enumerate(results):
                try:
                    doc = extract_document_info(result, idx, page_num)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    continue
            break
    
    # Si pas trouvé avec les sélecteurs, chercher les liens PDF
    if not documents:
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        for idx, link in enumerate(pdf_links[:20]):
            try:
                doc = {
                    'id': f"P{page_num}-{idx+1}",
                    'titre': link.get_text(strip=True) or f"PDF {idx+1}",
                    'url': make_absolute_url(link.get('href', '')),
                    'page': page_num,
                    'type': 'PDF'
                }
                documents.append(doc)
            except:
                continue
    
    return documents

def extract_document_info(element, idx, page_num):
    """Extrait les informations d'un élément de document"""
    
    try:
        # Titre
        title_selectors = ['h2', 'h3', 'h4', '.title', '.titre', 'a.title', 'strong', 'b']
        title = ""
        for selector in title_selectors:
            title_elem = element.find(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break
        
        if not title:
            title = f"Document {idx+1}"
        
        # URL
        url = ""
        link_elem = element.find('a', href=True)
        if link_elem:
            url = make_absolute_url(link_elem.get('href'))
        
        # Description/Extrait
        desc_selectors = ['p', '.description', '.snippet', '.extrait', '.summary']
        description = ""
        for selector in desc_selectors:
            desc_elem = element.find(selector)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                break
        
        # Date
        date_selectors = ['time', '.date', '.publication-date', '.datetime']
        date_text = ""
        for selector in date_selectors:
            date_elem = element.find(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                break
        
        # Type de document
        doc_type = detect_document_type(title, description)
        
        # Législature
        legislature = extract_legislature(title)
        
        # Année
        year = extract_year(date_text) or extract_year(title) or extract_year(description)
        
        # Mentions BUMIDOM
        mentions = count_mentions(title + " " + description)
        
        return {
            'id': f"P{page_num}-{idx+1}",
            'titre': title,
            'url': url,
            'description': description,
            'date': date_text,
            'type': doc_type,
            'législature': legislature,
            'année': year,
            'mentions_bumidom': mentions,
            'page': page_num,
            'index': idx + 1
        }
        
    except Exception as e:
        return None

def make_absolute_url(url):
    """Convertit une URL relative en absolue"""
    if not url:
        return ""
    
    base_domain = "https://archives.assemblee-nationale.fr"
    
    if url.startswith('http'):
        return url
    elif url.startswith('/'):
        return base_domain + url
    else:
        return base_domain + '/' + url

def detect_document_type(title, description):
    """Détecte le type de document"""
    text = (title + " " + description).lower()
    
    if any(x in text for x in ['constitution', 'constit']):
        return "Constitution"
    elif any(x in text for x in ['journal officiel', 'j.o.', 'jo ']):
        return "Journal Officiel"
    elif 'compte rendu' in text:
        return "Compte Rendu"
    elif 'cri' in text:
        return "CRI"
    elif 'rapport' in text:
        return "Rapport"
    elif 'débat' in text:
        return "Débat"
    else:
        return "Document"

def extract_legislature(text):
    """Extrait la législature du texte"""
    if not text:
        return ""
    
    patterns = [
        r'(\d+)(?:è?me|ème)?\s*(?:législature|legislature|leg)',
        r'législature\s*(\d+)',
        r'(\d+)(?:è?me|ème)\s*leg'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}ème"
    
    return ""

def extract_year(text):
    """Extrait l'année du texte"""
    if not text:
        return None
    
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

def parse_api_response(data, page_num):
    """Parse une réponse d'API JSON"""
    
    documents = []
    
    # Différents formats d'API possibles
    if isinstance(data, dict):
        # Chercher les résultats dans différentes clés
        results_keys = ['results', 'items', 'documents', 'data', 'hits']
        
        for key in results_keys:
            if key in data and isinstance(data[key], list):
                for idx, item in enumerate(data[key]):
                    try:
                        doc = parse_api_item(item, idx, page_num)
                        if doc:
                            documents.append(doc)
                    except:
                        continue
                break
    
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            try:
                doc = parse_api_item(item, idx, page_num)
                if doc:
                    documents.append(doc)
            except:
                continue
    
    return documents

def parse_api_item(item, idx, page_num):
    """Parse un élément d'API"""
    
    # Mapping des champs possibles
    title = item.get('title') or item.get('titre') or item.get('name') or f"Item {idx+1}"
    url = item.get('url') or item.get('link') or item.get('file') or ""
    description = item.get('description') or item.get('extrait') or item.get('snippet') or ""
    date = item.get('date') or item.get('publication_date') or item.get('created') or ""
    
    # Type de document
    doc_type = item.get('type') or detect_document_type(title, description)
    
    # Législature
    legislature = item.get('legislature') or extract_legislature(title)
    
    # Année
    year = item.get('year') or extract_year(date) or extract_year(title)
    
    # Mentions
    mentions = count_mentions(title + " " + description)
    
    return {
        'id': f"API-P{page_num}-{idx+1}",
        'titre': title,
        'url': make_absolute_url(url),
        'description': description,
        'date': date,
        'type': doc_type,
        'législature': legislature,
        'année': year,
        'mentions_bumidom': mentions,
        'page': page_num,
        'index': idx + 1,
        'source': 'api'
    }

def test_document_access(url):
    """Teste l'accès à un document"""
    
    if not url:
        return {
            'accessible': False,
            'error': 'URL vide'
        }
    
    try:
        # HEAD request pour vérifier l'existence
        response = requests.head(url, timeout=10, allow_redirects=True, headers=get_headers())
        
        return {
            'accessible': response.status_code == 200,
            'status': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'is_pdf': 'pdf' in response.headers.get('content-type', '').lower(),
            'size': response.headers.get('content-length')
        }
        
    except requests.exceptions.Timeout:
        return {
            'accessible': False,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'accessible': False,
            'error': str(e)
        }

def download_document(url):
    """Télécharge un document"""
    
    try:
        response = requests.get(url, timeout=30, headers=get_headers(), stream=True)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Erreur téléchargement: {e}")
    
    return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Paramètres de recherche
        st.markdown("### 🔍 Paramètres de recherche")
        
        search_query = st.text_input("Terme de recherche:", value="bumidom")
        total_pages = st.slider("Nombre de pages:", 1, 20, 10)
        results_per_page = st.slider("Résultats par page:", 5, 50, 10)
        
        # Filtres
        st.markdown("### 🎯 Filtres")
        
        min_year = st.number_input("Année min:", 1900, 2025, 1960)
        max_year = st.number_input("Année max:", 1900, 2025, 1990)
        
        doc_types = st.multiselect(
            "Types de documents:",
            ["Tous", "Constitution", "Journal Officiel", "Compte Rendu", "CRI", "Rapport", "Débat", "Document"],
            default=["Tous"]
        )
        
        # Boutons d'action
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            scrape_btn = st.button("🚀 Lancer le scraping", type="primary", use_container_width=True)
        with col2:
            reset_btn = st.button("🔄 Réinitialiser", use_container_width=True)
        
        st.markdown("---")
        
        # Info système
        st.markdown("### ℹ️ Information")
        st.info(f"""
        **Configuration:**
        - Pages: {total_pages}
        - Terme: {search_query}
        - Période: {min_year}-{max_year}
        
        **Méthode:** Requêtes HTTP directes
        """)
    
    # Initialisation session state
    if 'scraping_results' not in st.session_state:
        st.session_state.scraping_results = None
    if 'scraping_progress' not in st.session_state:
        st.session_state.scraping_progress = {}
    
    # Réinitialisation
    if reset_btn:
        st.session_state.scraping_results = None
        st.session_state.scraping_progress = {}
        st.rerun()
    
    # Lancement du scraping
    if scrape_btn:
        with st.spinner("Démarrage du scraping..."):
            all_documents = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num in range(1, total_pages + 1):
                status_text.text(f"Page {page_num}/{total_pages} en cours...")
                
                try:
                    # Recherche sur cette page
                    page_docs = search_archives_site(
                        query=search_query,
                        page=page_num,
                        per_page=results_per_page
                    )
                    
                    if page_docs:
                        all_documents.extend(page_docs)
                        st.success(f"✓ Page {page_num}: {len(page_docs)} documents")
                    else:
                        st.warning(f"⚠ Page {page_num}: Aucun document")
                    
                except Exception as e:
                    st.error(f"✗ Page {page_num}: Erreur - {str(e)[:100]}")
                
                # Mise à jour progression
                progress = page_num / total_pages
                progress_bar.progress(progress)
                
                # Pause pour éviter le blocage
                time.sleep(1)
            
            # Sauvegarder les résultats
            st.session_state.scraping_results = all_documents
            progress_bar.empty()
            status_text.empty()
            
            if all_documents:
                st.success(f"✅ Scraping terminé ! {len(all_documents)} documents trouvés.")
            else:
                st.warning("⚠️ Aucun document trouvé.")
    
    # Affichage des résultats
    if st.session_state.scraping_results is not None:
        results = st.session_state.scraping_results
        
        if results:
            # Statistiques
            st.subheader("📊 Statistiques")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Documents", len(results))
            with col2:
                pages = len(set(r.get('page', 1) for r in results))
                st.metric("Pages", pages)
            with col3:
                valid_urls = sum(1 for r in results if r.get('url', '').startswith('http'))
                st.metric("URLs valides", valid_urls)
            with col4:
                total_mentions = sum(r.get('mentions_bumidom', 0) for r in results)
                st.metric("Mentions", total_mentions)
            
            # Filtrage
            st.subheader("🎯 Filtrage")
            
            # Appliquer les filtres
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
            
            # Pagination
            items_per_page = st.slider("Documents par page:", 5, 50, 10, key="pagination")
            total_pages_view = max(1, (len(filtered_results) + items_per_page - 1) // items_per_page)
            
            if total_pages_view > 1:
                current_page = st.number_input("Page:", 1, total_pages_view, 1, key="current_page")
                start_idx = (current_page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, len(filtered_results))
                current_docs = filtered_results[start_idx:end_idx]
            else:
                current_docs = filtered_results
            
            # Tableau des résultats
            st.subheader("📋 Documents")
            
            if current_docs:
                # Créer DataFrame
                df_data = []
                for doc in current_docs:
                    df_data.append({
                        'ID': doc.get('id', ''),
                        'Titre': doc.get('titre', '')[:100] + ('...' if len(doc.get('titre', '')) > 100 else ''),
                        'Type': doc.get('type', ''),
                        'Année': doc.get('année', ''),
                        'Législature': doc.get('législature', ''),
                        'Page': doc.get('page', ''),
                        'URL': '✅' if doc.get('url') else '❌'
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Détail du document sélectionné
                st.subheader("🔍 Détail")
                
                doc_options = [f"{doc['id']} - {doc['titre'][:80]}..." for doc in current_docs]
                selected_option = st.selectbox("Sélectionner un document:", doc_options)
                
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
                            st.markdown(f"**Année:** {selected_doc.get('année', '')}")
                            st.markdown(f"**Date:** {selected_doc.get('date', '')}")
                            st.markdown(f"**Page source:** {selected_doc.get('page', '')}")
                            st.markdown(f"**Mentions BUMIDOM:** {selected_doc.get('mentions_bumidom', 0)}")
                            
                            if selected_doc.get('description'):
                                st.markdown("**Description:**")
                                st.write(selected_doc['description'])
                            
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
                                            st.success("📄 Fichier PDF")
                                            
                                            # Téléchargement
                                            if st.button("📥 Télécharger", key=f"dl_{selected_id}"):
                                                content = download_document(selected_doc['url'])
                                                if content:
                                                    filename = f"{selected_id}.pdf"
                                                    st.download_button(
                                                        label="💾 Sauvegarder",
                                                        data=content,
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
                            else:
                                st.warning("Pas d'URL disponible")
            
            # Analyses
            st.subheader("📈 Analyses")
            
            tab1, tab2, tab3 = st.tabs(["Par année", "Par type", "Par page"])
            
            with tab1:
                # Distribution par année
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
                else:
                    st.info("Aucune donnée d'année disponible")
            
            with tab2:
                # Distribution par type
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
                # Distribution par page
                page_counts = {}
                for doc in filtered_results:
                    page = doc.get('page', 1)
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
            st.subheader("💾 Export")
            
            export_format = st.selectbox(
                "Format d'export:",
                ["CSV", "JSON", "TXT (URLs)", "Excel"]
            )
            
            if st.button("📤 Exporter les données"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if export_format == "CSV":
                    df_export = pd.DataFrame(filtered_results)
                    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv_data,
                        file_name=f"bumidom_{timestamp}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = json.dumps(filtered_results, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json_data,
                        file_name=f"bumidom_{timestamp}.json",
                        mime="application/json"
                    )
                
                elif export_format == "TXT (URLs)":
                    urls = "\n".join([doc.get('url', '') for doc in filtered_results if doc.get('url')])
                    
                    st.download_button(
                        label="📥 Télécharger URLs",
                        data=urls,
                        file_name=f"bumidom_urls_{timestamp}.txt",
                        mime="text/plain"
                    )
                
                elif export_format == "Excel":
                    df_export = pd.DataFrame(filtered_results)
                    
                    # Utiliser un buffer pour Excel
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Documents')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=excel_data,
                        file_name=f"bumidom_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        else:
            st.warning("⚠️ Aucun document trouvé")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🌐 Scraping des Archives BUMIDOM
        
        ### 🎯 Objectif:
        Extraire les documents BUMIDOM depuis le site:
        **https://archives.assemblee-nationale.fr**
        
        Sans utiliser Selenium - uniquement des requêtes HTTP directes.
        
        ### ⚙️ Fonctionnalités:
        
        1. **Recherche multi-pages** (1-20 pages)
        2. **Extraction intelligente** des métadonnées
        3. **Détection automatique** des types de documents
        4. **Test d'accessibilité** des URLs
        5. **Téléchargement des PDFs**
        6. **Analyse et visualisation** complète
        7. **Export multi-formats** (CSV, JSON, Excel, TXT)
        
        ### 🔧 Comment ça marche:
        
        L'application essaye plusieurs méthodes pour trouver les documents:
        
        ```
        1. Recherche via paramètres URL
        2. Parsing des formulaires de recherche
        3. Détection des résultats de recherche
        4. Extraction des liens PDF
        5. Analyse du contenu HTML
        ```
        
        ### ⚠️ Limitations:
        
        - Dépend de la structure du site
        - Pas de JavaScript (sites SPA)
        - Peut être bloqué par anti-scraping
        - Rate les données chargées dynamiquement
        
        ### 🚀 Prêt à commencer?
        
        Configurez les paramètres dans la sidebar et cliquez sur **"Lancer le scraping"**!
        """)
        
        # Conseils d'amélioration
        with st.expander("💡 Conseils pour améliorer les résultats"):
            st.markdown("""
            ### Si le scraping ne fonctionne pas bien:
            
            1. **Vérifiez la disponibilité du site**
            ```python
            import requests
            response = requests.get("https://archives.assemblee-nationale.fr")
            print(response.status_code)  # Doit retourner 200
            ```
            
            2. **Inspectez la structure du site**
               - Visitez le site manuellement
               - Cherchez les URLs de recherche
               - Identifiez les sélecteurs CSS
            
            3. **Modifiez les sélecteurs CSS**
               - Dans `extract_documents_from_html()`
               - Ajoutez vos propres sélecteurs
            
            4. **Utilisez l'API si disponible**
               - Cherchez `/api/` ou `/search/json`
               - Inspectez les requêtes réseau
            
            5. **Ajoutez des délais**
               - Pour éviter le blocage IP
               - Respectez `robots.txt`
            """)

if __name__ == "__main__":
    main()
