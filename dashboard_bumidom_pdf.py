import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, quote, urlencode

# Configuration
st.set_page_config(
    page_title="Scraping BUMIDOM - 10 Pages Google CSE", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌐 Scraping BUMIDOM - 10 Pages Google CSE")
st.markdown("Extraction complète des 10 pages de résultats Google Custom Search")

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

def extract_google_cse_results(html_content, page_num):
    """Extrait les résultats d'une page Google Custom Search"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    documents = []
    
    # Trouver tous les résultats de recherche Google CSE
    # Sélecteurs spécifiques à Google CSE
    results = soup.find_all('div', class_=['gsc-webResult', 'gsc-result'])
    
    if not results:
        # Essayer un autre sélecteur
        results = soup.find_all('div', class_='gs-webResult')
    
    if not results:
        # Essayer avec les table rows
        results = soup.find_all('div', class_='gsc-table-result')
    
    st.info(f"Page {page_num}: {len(results)} résultats trouvés")
    
    for idx, result in enumerate(results):
        try:
            doc_info = extract_cse_result_info(result, idx, page_num)
            if doc_info:
                documents.append(doc_info)
        except Exception as e:
            st.warning(f"Erreur extraction résultat {idx}: {str(e)[:50]}")
            continue
    
    return documents

def extract_cse_result_info(result_element, idx, page_num):
    """Extrait les informations d'un résultat Google CSE"""
    
    try:
        # Titre et URL
        title_elem = result_element.find('a', class_='gs-title')
        if not title_elem:
            title_elem = result_element.find('a', {'class': re.compile(r'.*title.*')})
        
        title = title_elem.get_text(strip=True) if title_elem else f"Résultat {idx+1}"
        url = title_elem.get('href', '') if title_elem else ''
        
        # URL de redirection Google
        data_cturl = title_elem.get('data-cturl', '') if title_elem else ''
        
        # Extrait/snippet
        snippet_elem = result_element.find('div', class_='gs-snippet')
        if not snippet_elem:
            snippet_elem = result_element.find('div', class_='gsc-table-cell-snippet-close')
        
        snippet = ""
        if snippet_elem:
            # Extraire le texte du snippet
            snippet_text = snippet_elem.get_text(strip=True)
            # Nettoyer le snippet
            snippet = re.sub(r'\s+', ' ', snippet_text)
        
        # Format du fichier
        file_format = ""
        format_elem = result_element.find('span', class_='gs-fileFormatType')
        if format_elem:
            file_format = format_elem.get_text(strip=True)
        
        # Date dans le snippet
        date_match = re.search(r'(\d{1,2}\s+\w+\.?\s+\d{4})', snippet)
        date = date_match.group(1) if date_match else ""
        
        # Année
        year = None
        year_match = re.search(r'(\d{4})', date) if date else None
        if year_match:
            year = int(year_match.group(1))
        else:
            # Essayer d'extraire l'année de l'URL
            url_year_match = re.search(r'/(\d{4})-(\d{4})/', url)
            if url_year_match:
                year = int(url_year_match.group(1))
        
        # Type de document
        doc_type = "Document"
        if 'CONSTITUTION' in title.upper():
            doc_type = "Constitution"
        elif 'JOURNAL' in title.upper() or 'JOUIUAL' in title.upper() or 'JOURS' in title.upper():
            doc_type = "Journal Officiel"
        elif 'COMPTE RENDU' in title.upper():
            doc_type = "Compte Rendu"
        elif 'SEANCE' in title.upper():
            doc_type = "Séance"
        elif 'TABLES' in title.upper() or 'ANALYTIQUE' in title.upper():
            doc_type = "Tables analytiques"
        elif 'RÉPUBLIQUE' in title.upper():
            doc_type = "Débat parlementaire"
        elif 'ASSEMBLÉE NATIONALE' in title.upper() or 'ASSEMBLEE NATIONALE' in title.upper():
            doc_type = "CRI"
        
        # Législature
        legislature = ""
        leg_match = re.search(r'(\d+)(?:è?me|ème|°|\')\s*(?:législature|legislature|Leg)', title, re.IGNORECASE)
        if leg_match:
            legislature = f"{leg_match.group(1)}ème"
        else:
            # Extraire de l'URL
            url_leg_match = re.search(r'/(\d)/cri/', url)
            if url_leg_match:
                leg_num = url_leg_match.group(1)
                if leg_num == '2':
                    legislature = "2ème"
                elif leg_num == '3':
                    legislature = "3ème"
                elif leg_num == '4':
                    legislature = "4ème"
                elif leg_num == '5':
                    legislature = "5ème"
                elif leg_num == '6':
                    legislature = "6ème"
                elif leg_num == '7':
                    legislature = "7ème"
                elif leg_num == '8':
                    legislature = "8ème"
        
        # Période parlementaire
        periode = ""
        if 'ordinaire1' in url:
            periode = "Session ordinaire 1"
        elif 'ordinaire2' in url:
            periode = "Session ordinaire 2"
        elif 'extraordinaire' in url:
            periode = "Session extraordinaire"
        
        # Nom du fichier
        file_name = url.split('/')[-1] if '/' in url else ""
        
        # Mentions BUMIDOM
        mentions = 0
        search_text = (title + " " + snippet).lower()
        mentions += search_text.count('bumidom')
        mentions += search_text.count('b.u.m.i.d.o.m.')
        
        # Informations supplémentaires
        additional_info = {
            'url_redirection': data_cturl,
            'format_fichier': file_format,
            'fichier': file_name,
            'mentions_total': mentions
        }
        
        return {
            'id': f"P{page_num}-{idx+1}",
            'titre': title,
            'url': url,
            'extrait': snippet[:500] + "..." if len(snippet) > 500 else snippet,
            'date': date,
            'année': year,
            'type': doc_type,
            'législature': legislature,
            'période': periode,
            'page': page_num,
            'index': idx + 1,
            **additional_info
        }
        
    except Exception as e:
        st.warning(f"Erreur extraction CSE: {str(e)[:100]}")
        return None

def scrape_google_cse_pages(query="bumidom", total_pages=10):
    """Scrape les pages Google CSE"""
    
    base_url = "https://archives.assemblee-nationale.fr"
    all_documents = []
    
    # ID du moteur de recherche Google CSE (extrait du HTML)
    cx = "014917347718038151697:kltwr00yvbk"
    
    for page_num in range(1, total_pages + 1):
        with st.spinner(f"Scraping page {page_num}/{total_pages}..."):
            
            # Méthode 1: Accès direct via l'URL Google CSE
            try:
                # Construire l'URL Google CSE
                start_index = (page_num - 1) * 10
                google_cse_url = f"https://cse.google.com/cse"
                
                params = {
                    'cx': cx,
                    'q': query,
                    'start': start_index,
                    'num': 10,
                    'hl': 'fr',
                    'ie': 'UTF-8',
                    'oe': 'UTF-8'
                }
                
                response = requests.get(google_cse_url, params=params, headers=get_headers(), timeout=15)
                
                if response.status_code == 200:
                    page_docs = extract_google_cse_results(response.content, page_num)
                    if page_docs:
                        all_documents.extend(page_docs)
                        st.success(f"✓ Page {page_num}: {len(page_docs)} documents")
                    else:
                        st.warning(f"⚠ Page {page_num}: Aucun document via CSE direct")
                        
                else:
                    st.warning(f"⚠ Page {page_num}: Erreur CSE ({response.status_code})")
                    
            except Exception as e:
                st.warning(f"⚠ Page {page_num}: Erreur CSE - {str(e)[:100]}")
            
            # Méthode 2: Utiliser l'URL simulée si la première échoue
            if page_num <= len(all_documents) // 10:
                continue
                
            try:
                # URL simulée basée sur le pattern observé
                simulated_url = f"{base_url}/cse?q={quote(query)}&start={start_index}"
                response = requests.get(simulated_url, headers=get_headers(), timeout=10)
                
                if response.status_code == 200:
                    page_docs = extract_google_cse_results(response.content, page_num)
                    if page_docs:
                        all_documents.extend(page_docs)
                        st.success(f"✓ Page {page_num}: {len(page_docs)} documents (simulé)")
                
            except:
                pass
            
            # Pause pour éviter le blocage
            time.sleep(1)
    
    return all_documents

def test_url_access(url):
    """Teste l'accessibilité d'une URL"""
    
    if not url or not url.startswith('http'):
        return {
            'accessible': False,
            'status': 0,
            'error': 'URL invalide'
        }
    
    try:
        # Essayer d'abord HEAD
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
            'status': 408,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'accessible': False,
            'status': 0,
            'error': str(e)[:100]
        }

def download_pdf(url):
    """Télécharge un fichier PDF"""
    
    try:
        response = requests.get(url, timeout=30, headers=get_headers(), stream=True)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Erreur téléchargement: {str(e)[:100]}")
    
    return None

def simulate_results_for_demo():
    """Simule des résultats pour la démonstration (basé sur le HTML fourni)"""
    
    st.info("Mode démonstration: Utilisation des données du HTML fourni")
    
    # Extraire les données du HTML fourni
    html_content = st.session_state.demo_html if 'demo_html' in st.session_state else ""
    
    if not html_content:
        # HTML de démonstration (extrait simplifié)
        html_content = """
        <div class="gsc-webResult gsc-result">
            <div class="gs-webResult gs-result">
                <div class="gsc-thumbnail-inside">
                    <div class="gs-title">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/6/cri/1978-1979-ordinaire2/017.pdf">COMPTE RENDU INTEGRAL - Assemblée nationale - Archives</a>
                    </div>
                </div>
                <div class="gs-bidi-start-align gs-snippet" dir="ltr">16 févr. 2025 ... Bumidom faire une formation professionnelle en métropole . En effet, la somme allouée aux stagiaires qui se trouvent loin de leur foyer et ...</div>
            </div>
        </div>
        <div class="gsc-webResult gsc-result">
            <div class="gs-webResult gs-result">
                <div class="gsc-thumbnail-inside">
                    <div class="gs-title">
                        <a class="gs-title" href="https://archives.assemblee-nationale.fr/4/qst/4-qst-1969-08-23.pdf">JOURNAL OFFICIEL - Assemblée nationale - Archives</a>
                    </div>
                </div>
                <div class="gs-bidi-start-align gs-snippet" dir="ltr">30 déc. 2025 ... en métropole au titre du Bumidom la même année, M . le minist re de l 'économie et des finances indiquait dans sa réponse qu ' il n ' était.</div>
            </div>
        </div>
        """
    
    # Extraire les documents du HTML
    documents = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extraire les résultats
    results = soup.find_all('div', class_=['gsc-webResult', 'gsc-result', 'gs-webResult', 'gs-result'])
    
    for page_num in range(1, 11):  # 10 pages
        for idx in range(10):  # 10 résultats par page
            if idx < len(results):
                result = results[idx]
                doc_info = extract_cse_result_info(result, idx, page_num)
                if doc_info:
                    # Modifier pour simuler différentes pages
                    doc_info['id'] = f"P{page_num}-{idx+1}"
                    doc_info['page'] = page_num
                    doc_info['année'] = 1960 + (page_num * 2) + (idx % 5)
                    documents.append(doc_info)
    
    return documents[:100]  # Limiter à 100 documents

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration Google CSE")
        
        st.markdown("### 🔍 Paramètres de recherche")
        
        search_query = st.text_input("Terme de recherche:", value="bumidom")
        total_pages = st.slider("Pages à scraper:", 1, 20, 10)
        
        st.markdown("### 🎯 Filtres")
        
        min_year = st.number_input("Année min:", 1900, 2025, 1960)
        max_year = st.number_input("Année max:", 1900, 2025, 1990)
        
        doc_types = st.multiselect(
            "Types de documents:",
            ["Tous", "Constitution", "Journal Officiel", "Compte Rendu", "Séance", 
             "CRI", "Débat parlementaire", "Tables analytiques", "Document"],
            default=["Tous"]
        )
        
        st.markdown("### ⚡ Mode")
        
        mode = st.radio(
            "Mode d'extraction:",
            ["Démonstration (données simulées)", "Réel (Google CSE)"],
            index=0
        )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            scrape_btn = st.button("🚀 Lancer le scraping", type="primary", use_container_width=True)
        with col2:
            reset_btn = st.button("🔄 Réinitialiser", use_container_width=True)
        
        st.markdown("---")
        
        # Info Google CSE
        st.markdown("### ℹ️ Google Custom Search")
        st.info(f"""
        **Configuration:**
        - Moteur ID: 014917347718038151697:kltwr00yvbk
        - Pages: {total_pages}
        - Terme: {search_query}
        - Période: {min_year}-{max_year}
        
        **Mode:** {mode}
        """)
    
    # Initialisation session state
    if 'scraping_results' not in st.session_state:
        st.session_state.scraping_results = None
    
    # Réinitialisation
    if reset_btn:
        st.session_state.scraping_results = None
        st.rerun()
    
    # Lancement du scraping
    if scrape_btn:
        with st.spinner("Démarrage du scraping..."):
            
            if "Démonstration" in mode:
                # Mode démonstration
                results = simulate_results_for_demo()
            else:
                # Mode réel
                results = scrape_google_cse_pages(search_query, total_pages)
            
            st.session_state.scraping_results = results
            
            if results:
                st.success(f"✅ Scraping terminé ! {len(results)} documents trouvés.")
            else:
                st.warning("⚠️ Aucun document trouvé.")
    
    # Affichage des résultats
    if st.session_state.scraping_results is not None:
        results = st.session_state.scraping_results
        
        if results:
            # Statistiques
            st.subheader("📊 Statistiques")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Documents", len(results))
            with col2:
                pages = len(set(r.get('page', 1) for r in results))
                st.metric("Pages", pages)
            with col3:
                years = len(set(r.get('année') for r in results if r.get('année')))
                st.metric("Années", years)
            with col4:
                legislatures = len(set(r.get('législature') for r in results if r.get('législature')))
                st.metric("Législatures", legislatures)
            with col5:
                total_mentions = sum(r.get('mentions_total', 0) for r in results)
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
                st.caption(f"Documents {start_idx+1}-{end_idx} sur {len(filtered_results)}")
            else:
                current_docs = filtered_results
            
            # Tableau des résultats
            st.subheader("📋 Documents")
            
            if current_docs:
                # Créer DataFrame pour affichage
                df_data = []
                for doc in current_docs:
                    df_data.append({
                        'ID': doc.get('id', ''),
                        'Titre': doc.get('titre', '')[:80] + ('...' if len(doc.get('titre', '')) > 80 else ''),
                        'Type': doc.get('type', ''),
                        'Année': doc.get('année', ''),
                        'Législature': doc.get('législature', ''),
                        'Page': doc.get('page', ''),
                        'Mentions': doc.get('mentions_total', 0),
                        'URL': '✅' if doc.get('url') else '❌'
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Détail du document sélectionné
                st.subheader("🔍 Détail")
                
                doc_options = [f"{doc['id']} - {doc['titre'][:60]}..." for doc in current_docs]
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
                            st.markdown(f"**Période:** {selected_doc.get('période', '')}")
                            st.markdown(f"**Page source:** {selected_doc.get('page', '')}")
                            st.markdown(f"**Mentions BUMIDOM:** {selected_doc.get('mentions_total', 0)}")
                            st.markdown(f"**Format:** {selected_doc.get('format_fichier', '')}")
                            st.markdown(f"**Fichier:** {selected_doc.get('fichier', '')}")
                            
                            if selected_doc.get('extrait'):
                                st.markdown("**Extrait:**")
                                # Mettre en évidence BUMIDOM
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
                                
                                if selected_doc.get('url_redirection'):
                                    st.markdown("**URL Google:**")
                                    st.code(selected_doc['url_redirection'])
                        
                        with col_detail2:
                            st.markdown("**Actions:**")
                            
                            if selected_doc.get('url'):
                                # Test d'accès
                                if st.button("🔗 Tester l'accès", key=f"test_{selected_id}"):
                                    access_info = test_url_access(selected_doc['url'])
                                    
                                    if access_info.get('accessible'):
                                        st.success(f"✅ Accessible")
                                        st.info(f"Code: {access_info.get('status')}")
                                        
                                        if access_info.get('is_pdf'):
                                            st.success("📄 Fichier PDF détecté")
                                            
                                            # Téléchargement
                                            if st.button("📥 Télécharger", key=f"dl_{selected_id}"):
                                                pdf_content = download_pdf(selected_doc['url'])
                                                if pdf_content:
                                                    filename = f"{selected_id}_{selected_doc.get('fichier', 'document.pdf')}"
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
                            
                            # Statistiques avancées
                            st.markdown("**Statistiques avancées:**")
                            if selected_doc.get('extrait'):
                                text = selected_doc['extrait'].lower()
                                count_bumidom = text.count('bumidom')
                                count_b_umidom = text.count('b.u.m.i.d.o.m.')
                                st.metric("BUMIDOM", count_bumidom)
                                st.metric("B.U.M.I.D.O.M.", count_b_umidom)
            
            # Analyses
            st.subheader("📈 Analyses")
            
            tab1, tab2, tab3, tab4 = st.tabs(["Par année", "Par type", "Par législature", "Par page"])
            
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
                # Distribution par législature
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
                    
                    # Trier numériquement
                    try:
                        df_leg['Num'] = df_leg['Législature'].str.extract(r'(\d+)').astype(int)
                        df_leg = df_leg.sort_values('Num')
                    except:
                        pass
                    
                    st.bar_chart(df_leg.set_index('Législature'))
            
            with tab4:
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
            st.subheader("💾 Export des données")
            
            export_format = st.selectbox(
                "Format d'export:",
                ["CSV", "JSON", "TXT (URLs)", "Excel", "Rapport PDF"]
            )
            
            if st.button("📤 Exporter les données"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if export_format == "CSV":
                    df_export = pd.DataFrame(filtered_results)
                    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv_data,
                        file_name=f"bumidom_cse_{timestamp}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = json.dumps(filtered_results, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json_data,
                        file_name=f"bumidom_cse_{timestamp}.json",
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
                        file_name=f"bumidom_cse_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                elif export_format == "Rapport PDF":
                    # Générer un rapport texte
                    rapport = f"""
                    RAPPORT D'EXTRACTION BUMIDOM - GOOGLE CSE
                    ============================================
                    
                    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    Terme recherché: {search_query}
                    Pages analysées: {total_pages}
                    Documents trouvés: {len(filtered_results)}
                    
                    STATISTIQUES:
                    -------------
                    • Documents par année: {len(set(d.get('année') for d in filtered_results if d.get('année')))}
                    • Législatures couvertes: {len(set(d.get('législature') for d in filtered_results if d.get('législature')))}
                    • Types de documents: {len(set(d.get('type') for d in filtered_results))}
                    • Mentions BUMIDOM totales: {sum(d.get('mentions_total', 0) for d in filtered_results)}
                    
                    DOCUMENTS:
                    ----------
                    """
                    
                    for doc in filtered_results[:50]:  # Limiter à 50 dans le rapport
                        rapport += f"""
                    {doc.get('id')} - {doc.get('titre')}
                      Année: {doc.get('année', 'N/A')}
                      Législature: {doc.get('législature', 'N/A')}
                      Type: {doc.get('type', 'N/A')}
                      URL: {doc.get('url', 'N/A')}
                      Extrait: {doc.get('extrait', '')[:100]}...
                    """
                    
                    st.download_button(
                        label="📥 Télécharger Rapport",
                        data=rapport,
                        file_name=f"rapport_bumidom_{timestamp}.txt",
                        mime="text/plain"
                    )
        
        else:
            st.warning("⚠️ Aucun document trouvé")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🌐 Scraping Google Custom Search Engine (CSE)
        
        ### 🎯 Objectif:
        Extraire les **10 pages de résultats** BUMIDOM depuis le moteur de recherche Google CSE intégré au site:
        **https://archives.assemblee-nationale.fr**
        
        ### 📊 Ce que vous obtiendrez:
        
        1. **Documents PDF** complets des archives
        2. **Métadonnées structurées** (titre, date, législature, type)
        3. **Extraits de texte** avec mentions BUMIDOM
        4. **URLs directes** vers les fichiers PDF
        5. **Analyses statistiques** complètes
        
        ### 🔧 Fonctionnalités:
        
        - **Scraping multi-pages** (1-20 pages)
        - **Extraction intelligente** Google CSE
        - **Filtrage avancé** par année, type, législature
        - **Test d'accessibilité** des PDFs
        - **Téléchargement direct** des documents
        - **Analyses visuelles** (graphiques, statistiques)
        - **Export multi-formats** (CSV, JSON, Excel, TXT)
        
        ### ⚡ Deux modes disponibles:
        
        1. **Mode Démonstration**: Données simulées pour tester rapidement
        2. **Mode Réel**: Accès réel à Google CSE (nécessite une connexion)
        
        ### 🚀 Comment commencer:
        
        1. Configurez les paramètres dans la sidebar
        2. Sélectionnez le mode (Démonstration ou Réel)
        3. Cliquez sur **"Lancer le scraping"**
        4. Explorez, filtrez et exportez les résultats
        """)
        
        # Aperçu des données
        with st.expander("👁️ Aperçu des données disponibles"):
            st.markdown("""
            ### Structure des documents extraits:
            
            ```json
            {
              "id": "P3-1",
              "titre": "JOURNAL OFFICIEL - Assemblée nationale - Archives",
              "url": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire2/038.pdf",
              "extrait": "5 janv. 2025 ... 5 novembre 1971 par l'intermédiaire du Bumidom...",
              "date": "5 janv. 2025",
              "année": 1971,
              "type": "Journal Officiel",
              "législature": "4ème",
              "période": "Session ordinaire 2",
              "page": 3,
              "mentions_total": 2
            }
            ```
            
            ### Exemples de données réelles:
            
            | Page | Document | Année | Législature | Type |
            |------|----------|-------|-------------|------|
            | 1 | COMPTE RENDU INTEGRAL | 1978 | 6ème | Compte Rendu |
            | 2 | JOURNAL OFFICIEL | 1969 | 4ème | Journal Officiel |
            | 3 | CONSTITUTION DU 4 OCTOBRE 1958 | 1964 | 2ème | Constitution |
            | 4 | 86° SEANCE | 1976 | 5ème | Séance |
            | 5 | DE LA RÉPUBLIQUE FRANÇAISE | 1986 | 8ème | Débat parlementaire |
            
            ### Statistiques attendues:
            - **~100 documents** (10 pages × ~10 résultats/page)
            - **Période**: 1964-1986 environ
            - **Législatures**: 2ème à 8ème
            - **Types**: Journaux Officiels, Comptes Rendus, Constitutions, etc.
            """)

if __name__ == "__main__":
    main()
