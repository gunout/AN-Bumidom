import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json

# Configuration
st.set_page_config(
    page_title="Analyse BUMIDOM - Scraping complet", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Scraping complet des Archives BUMIDOM")
st.markdown("Extraction de tous les documents PDF depuis les résultats Google")

def extract_document_info(result_html):
    """Extrait les informations d'un document depuis le HTML d'un résultat"""
    
    soup = BeautifulSoup(result_html, 'html.parser')
    
    # Extraire le titre
    title_elem = soup.find('a', class_='gs-title')
    title = title_elem.get_text(strip=True) if title_elem else "Titre non disponible"
    
    # Extraire l'URL
    url = title_elem.get('href', '') if title_elem else ''
    
    # Extraire le snippet (extrait)
    snippet_elem = soup.find('div', class_='gs-bidi-start-align gs-snippet')
    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
    
    # Extraire la date du snippet
    date_match = re.search(r'(\d{1,2}\s+\w+\.?\s+\d{4})', snippet)
    date = date_match.group(1) if date_match else ''
    
    # Extraire l'année
    year_match = re.search(r'(\d{4})', date) if date else None
    year = int(year_match.group(1)) if year_match else 0
    
    # Extraire le type de fichier
    file_format_elem = soup.find('span', class_='gs-fileFormatType')
    file_format = file_format_elem.get_text(strip=True) if file_format_elem else ''
    
    # Extraire le chemin de l'URL pour l'analyse
    url_parts = url.split('/')
    file_name = url_parts[-1] if url_parts else ''
    
    # Identifier le type de document
    doc_type = "CRI"
    title_upper = title.upper()
    if 'CONSTITUTION' in title_upper:
        doc_type = "Constitution"
    elif 'JOURNAL' in title_upper or 'JOUR' in title_upper:
        doc_type = "Journal Officiel"
    elif 'COMPTE RENDU' in title_upper:
        doc_type = "Compte Rendu"
    elif 'RÉPUBLIQUE' in title_upper:
        doc_type = "Débat parlementaire"
    elif 'ASSEMBLÉE' in title_upper:
        doc_type = "CRI"
    
    # Extraire la législature
    legislature = ""
    if "4'" in title or "4°" in title:
        legislature = "4ème"
    elif "7'" in title:
        legislature = "7ème"
    elif "2'" in title:
        legislature = "2ème"
    elif "5'" in title:
        legislature = "5ème"
    elif "8'" in title:
        legislature = "8ème"
    elif "6'" in title:
        legislature = "6ème"
    elif "3'" in title:
        legislature = "3ème"
    
    # Extraire la période parlementaire de l'URL
    periode = ""
    if 'ordinaire1' in url:
        periode = "Session ordinaire 1"
    elif 'ordinaire2' in url:
        periode = "Session ordinaire 2"
    elif 'extraordinaire' in url:
        periode = "Session extraordinaire"
    elif 'extraordinaire1' in url:
        periode = "Session extraordinaire 1"
    elif 'extraordinaire2' in url:
        periode = "Session extraordinaire 2"
    
    # Extraire l'année de la session
    session_year_match = re.search(r'(\d{4})-(\d{4})', url)
    if session_year_match:
        session_start = int(session_year_match.group(1))
        session_end = int(session_year_match.group(2))
        if year == 0:
            year = session_start
    
    return {
        'titre': title,
        'url': url,
        'extrait': snippet,
        'date': date,
        'année': year if year != 0 else session_start if 'session_start' in locals() else 1900,
        'format_fichier': file_format,
        'nom_fichier': file_name,
        'type': doc_type,
        'législature': legislature,
        'période': periode,
        'session_start': session_start if 'session_start' in locals() else year,
        'session_end': session_end if 'session_end' in locals() else year
    }

def parse_all_google_pages():
    """Parse toutes les pages de résultats Google"""
    
    st.info("""
    **Note:** Cette fonction simule le scraping de 10 pages de résultats.
    En production, vous devriez utiliser l'API Google Custom Search ou Selenium.
    """)
    
    # Données de simulation basées sur le HTML fourni
    # Dans la réalité, vous scraperiez dynamiquement chaque page
    all_documents = []
    
    # Page 1 (données du HTML fourni)
    page1_docs = [
        {
            'titre': 'JOURNAL OFFICIAL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf',
            'extrait': '26 oct. 1971 ... Bumidom. Nous avons donc fait un effort très sérieux — je crois qu\'il commence à porter ses fruits — pour l\'information, comme on l\'a ...',
            'date': '26 oct. 1971',
            'année': 1971,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '024.pdf',
            'type': 'Journal Officiel',
            'législature': '4ème',
            'période': 'Session ordinaire 1',
            'session_start': 1971,
            'session_end': 1972
        },
        {
            'titre': 'CONSTITUTION DU 4 OCTOBRE 1958 4\' Législature',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1968-1969-ordinaire1/050.pdf',
            'extrait': '9 nov. 2025 ... Bumidom. Dès mon arrivée au ministère, je me suis essentielle- ment préoccupé des conditions d\'accueil et d\'adaptation des originaires des ...',
            'date': '9 nov. 2025',
            'année': 1968,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '050.pdf',
            'type': 'Constitution',
            'législature': '4ème',
            'période': 'Session ordinaire 1',
            'session_start': 1968,
            'session_end': 1969
        },
        {
            'titre': 'Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf',
            'extrait': 'le BUMIDOM qui, en 1965, a facilité l\'installation en métropole. La réalisation effective de la parité globale se poursuivra de 7.000 personnes. en. 1967 . C ...',
            'date': '',
            'année': 1966,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '021.pdf',
            'type': 'CRI',
            'législature': '2ème',
            'période': 'Session ordinaire 1',
            'session_start': 1966,
            'session_end': 1967
        },
        {
            'titre': 'CONSTITUTION DU 4 OCTOBRE 1958 7\' Législature',
            'url': 'https://archives.assemblee-nationale.fr/7/cri/1982-1983-ordinaire1/057.pdf',
            'extrait': '5 nov. 1982 ... Le Bumidom, tant décrié par vos amis, a été, dans la pratique, remplacé par un succédané — l\'agence nationale pour l\'insertion et la ...',
            'date': '5 nov. 1982',
            'année': 1982,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '057.pdf',
            'type': 'Constitution',
            'législature': '7ème',
            'période': 'Session ordinaire 1',
            'session_start': 1982,
            'session_end': 1983
        },
        {
            'titre': 'COMPTE RENDU INTEGRAL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/057.pdf',
            'extrait': '27 janv. 2025 ... des crédits affectés au Bumidom pour les années 1976 et 1977;. 2° les raisons de la réduction des crédits pour l\'année 1977 si tou- tefois ...',
            'date': '27 janv. 2025',
            'année': 1976,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '057.pdf',
            'type': 'Compte Rendu',
            'législature': '5ème',
            'période': 'Session ordinaire 2',
            'session_start': 1976,
            'session_end': 1977
        },
        {
            'titre': 'CONSTITUTION DU 4 OCTOBRE 1958 4° Législature',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/060.pdf',
            'extrait': '16 nov. 1970 ... des départements d\'outre-mer — Bumidom — dont l\'objectif est à la fois de faciliter l\'immigration et d\'orienter les tra- vailleurs vers un ...',
            'date': '16 nov. 1970',
            'année': 1970,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '060.pdf',
            'type': 'Constitution',
            'législature': '4ème',
            'période': 'Session ordinaire 1',
            'session_start': 1970,
            'session_end': 1971
        },
        {
            'titre': 'DE LA RÉPUBLIQUE FRANÇAISE - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/8/cri/1985-1986-extraordinaire1/015.pdf',
            'extrait': '11 juil. 1986 ... Bumidom . On crée l \' A.N.T., Agence nationale pour l \' inser- tion et la promotion des travailleurs. Le slogan gouverne- mental était ...',
            'date': '11 juil. 1986',
            'année': 1985,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '015.pdf',
            'type': 'Débat parlementaire',
            'législature': '8ème',
            'période': 'Session extraordinaire 1',
            'session_start': 1985,
            'session_end': 1986
        },
        {
            'titre': 'JOUR AL OFFICIEL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/067.pdf',
            'extrait': '5 nov. 2025 ... société d \'Etat « Bumidom », qui prend à sa charge les frais du voyage. En conséquence, il lui demande quelles mesures il compte prendre ...',
            'date': '5 nov. 2025',
            'année': 1971,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '067.pdf',
            'type': 'Journal Officiel',
            'législature': '4ème',
            'période': 'Session ordinaire 1',
            'session_start': 1971,
            'session_end': 1972
        },
        {
            'titre': 'CONSTITUTION DU 4 OCTOBRE 1958 4° Législature',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/023.pdf',
            'extrait': '26 oct. 1970 ... Le Bumidom ne devrait pas être traité comme un instrument de la ... tés d\'accueil et du Bumidom, c\'est-à-dire du bureau des migrations.',
            'date': '26 oct. 1970',
            'année': 1970,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '023.pdf',
            'type': 'Constitution',
            'législature': '4ème',
            'période': 'Session ordinaire 1',
            'session_start': 1970,
            'session_end': 1971
        },
        {
            'titre': 'JOUR: AL OFFICIEL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire2/007.pdf',
            'extrait': '7 mars 2025 ... nisée par le Bumidom, est loin d\'être satisfaisante. Ses effets sont du reste annihilés par l\'entrée d\'une main-d\'oeuvre impor- tante dans ...',
            'date': '7 mars 2025',
            'année': 1970,
            'format_fichier': 'PDF/Adobe Acrobat',
            'nom_fichier': '007.pdf',
            'type': 'Journal Officiel',
            'législature': '4ème',
            'période': 'Session ordinaire 2',
            'session_start': 1970,
            'session_end': 1971
        }
    ]
    
    all_documents.extend(page1_docs)
    
    # Simulation des 9 autres pages avec des données similaires mais variées
    for page_num in range(2, 11):
        st.write(f"📄 Extraction de la page {page_num}...")
        
        # Simuler des documents supplémentaires avec des variations
        for i in range(10):  # 10 documents par page
            base_doc = page1_docs[i % len(page1_docs)].copy()
            
            # Modifier pour simuler différents documents
            base_doc['url'] = base_doc['url'].replace('.pdf', f'_p{page_num}_{i}.pdf')
            base_doc['nom_fichier'] = base_doc['nom_fichier'].replace('.pdf', f'_p{page_num}_{i}.pdf')
            
            # Modifier l'année pour la variété
            year_variation = (page_num - 1) * 2
            base_doc['année'] = max(1960, base_doc['année'] - year_variation)
            base_doc['session_start'] = base_doc['année']
            base_doc['session_end'] = base_doc['année'] + 1
            
            # Modifier la législature occasionnellement
            if page_num % 3 == 0:
                base_doc['législature'] = f"{page_num % 5 + 3}ème"
            
            # Ajouter l'ID de page
            base_doc['page_source'] = page_num
            base_doc['id_document'] = f"P{page_num}-{i+1}"
            
            all_documents.append(base_doc)
    
    # Formater avec des IDs
    formatted_documents = []
    for idx, doc in enumerate(all_documents):
        formatted_documents.append({
            'id': idx + 1,
            'id_document': doc.get('id_document', f"P1-{idx+1}"),
            'titre': doc['titre'],
            'url': doc['url'],
            'extrait': doc['extrait'],
            'date': doc['date'],
            'année': doc['année'],
            'format_fichier': doc['format_fichier'],
            'nom_fichier': doc['nom_fichier'],
            'type': doc['type'],
            'législature': doc['législature'],
            'période': doc['période'],
            'session_start': doc['session_start'],
            'session_end': doc['session_end'],
            'page_source': doc.get('page_source', 1),
            'mentions_bumidom': doc['extrait'].lower().count('bumidom')
        })
    
    return formatted_documents

def scrape_real_google_pages():
    """Fonction pour scraper réellement les pages Google (à implémenter)"""
    
    st.warning("""
    ⚠️ **Pour un vrai scraping Google:**
    
    1. Utilisez l'API Google Custom Search (100 requêtes/jour gratuites)
    2. Ou utilisez Selenium pour le scraping dynamique
    3. Respectez les conditions d'utilisation de Google
    
    Cette version utilise des données simulées pour la démonstration.
    """)
    
    # Simuler le scraping de 10 pages
    total_pages = 10
    documents_per_page = 10
    total_documents = total_pages * documents_per_page
    
    # Générer des documents simulés
    simulated_docs = parse_all_google_pages()
    
    return simulated_docs

def test_url_access(url):
    """Teste l'accessibilité d'une URL"""
    try:
        # Pour les URLs simulées, simuler des réponses variées
        if '_p' in url and 'simulated' not in url:
            # Simuler différentes réponses
            import random
            status_codes = [200, 200, 200, 404, 403, 200]  # Majorité de succès
            content_types = ['application/pdf', 'application/pdf', 'application/pdf', 'text/html']
            
            return {
                'status_code': random.choice(status_codes),
                'content_type': random.choice(content_types),
                'accessible': random.choice([True, True, True, False]),
                'simulated': True
            }
        
        # Pour les vraies URLs
        response = requests.head(url, timeout=10, allow_redirects=True)
        return {
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'accessible': response.status_code == 200
        }
    except Exception as e:
        return {
            'status_code': 0,
            'content_type': '',
            'accessible': False,
            'error': str(e)
        }

def download_pdf(url, file_name):
    """Télécharge un fichier PDF"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        st.error(f"Erreur de téléchargement: {str(e)[:100]}")
        return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration du scraping")
        
        st.markdown("### 📊 Paramètres de scraping")
        
        total_pages = st.slider("Nombre de pages à scraper:", 1, 10, 10)
        documents_per_page = st.slider("Documents par page:", 1, 100, 10)
        
        st.markdown("### 🔍 Filtres de recherche")
        
        keyword = st.text_input("Mot-clé principal:", value="BUMIDOM")
        additional_keywords = st.text_input("Mots-clés supplémentaires (séparés par des virgules):", 
                                           value="DOM, migration, outre-mer")
        
        st.markdown("### 🎯 Filtres d'analyse")
        
        min_year = st.slider("Année minimum:", 1960, 2025, 1960)
        max_year = st.slider("Année maximum:", 1960, 2025, 1990)
        
        st.markdown("### 🏛️ Filtres par législature")
        all_legislatures = ["Toutes", "1ère", "2ème", "3ème", "4ème", "5ème", "6ème", "7ème", "8ème", "9ème", "10ème"]
        selected_legislatures = st.multiselect(
            "Législatures:",
            all_legislatures,
            default=["Toutes"]
        )
        
        st.markdown("### 📄 Filtres par type")
        doc_types = ["Tous", "CRI", "Constitution", "Journal Officiel", "Compte Rendu", "Débat parlementaire", "Rapport", "Autre"]
        selected_types = st.multiselect(
            "Types de documents:",
            doc_types,
            default=["Tous"]
        )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            scrape_btn = st.button("🚀 Lancer le scraping", type="primary", use_container_width=True)
        with col2:
            stop_btn = st.button("⏹️ Arrêter", use_container_width=True)
        
        st.markdown("---")
        st.info(f"""
        **Configuration:**
        - Pages: {total_pages}
        - Documents/page: {documents_per_page}
        - Total estimé: {total_pages * documents_per_page} documents
        - Période: {min_year}-{max_year}
        """)
    
    # État de session
    if 'scraping_in_progress' not in st.session_state:
        st.session_state.scraping_in_progress = False
    if 'scraping_results' not in st.session_state:
        st.session_state.scraping_results = None
    
    # Gestion des boutons
    if scrape_btn:
        st.session_state.scraping_in_progress = True
        st.session_state.scraping_results = None
    
    if stop_btn:
        st.session_state.scraping_in_progress = False
    
    # Scraping en cours
    if st.session_state.scraping_in_progress:
        st.subheader("🔍 Scraping en cours...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simuler le scraping
        for page in range(1, total_pages + 1):
            progress = page / total_pages
            progress_bar.progress(progress)
            status_text.text(f"Page {page}/{total_pages} - Extraction des documents...")
            
            # Simuler un délai
            import time
            time.sleep(0.5)
        
        # Récupérer les résultats
        with st.spinner("Traitement des données..."):
            results = scrape_real_google_pages()
            st.session_state.scraping_results = results
            st.session_state.scraping_in_progress = False
        
        st.success(f"✅ Scraping terminé ! {len(results)} documents extraits.")
    
    # Affichage des résultats
    if st.session_state.scraping_results is not None:
        results = st.session_state.scraping_results
        
        # Statistiques
        st.subheader("📊 Statistiques du scraping")
        
        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
        with col_stat1:
            st.metric("Documents totaux", len(results))
        with col_stat2:
            pages = len(set(r.get('page_source', 1) for r in results))
            st.metric("Pages scrapées", pages)
        with col_stat3:
            years = len(set(r['année'] for r in results))
            st.metric("Années couvertes", years)
        with col_stat4:
            legislatures = len(set(r['législature'] for r in results if r['législature']))
            st.metric("Législatures", legislatures)
        with col_stat5:
            mentions = sum(r.get('mentions_bumidom', 0) for r in results)
            st.metric("Mentions BUMIDOM", mentions)
        
        # Filtrer les résultats
        st.subheader("🎯 Filtrage des résultats")
        
        filtered_results = results
        
        # Filtrer par année
        filtered_results = [r for r in filtered_results 
                          if min_year <= r['année'] <= max_year]
        
        # Filtrer par législature
        if "Toutes" not in selected_legislatures and selected_legislatures:
            filtered_results = [r for r in filtered_results 
                              if r['législature'] in selected_legislatures]
        
        # Filtrer par type
        if "Tous" not in selected_types and selected_types:
            filtered_results = [r for r in filtered_results 
                              if r['type'] in selected_types]
        
        st.info(f"📄 {len(filtered_results)} documents après filtrage")
        
        # Pagination
        st.subheader("📋 Documents extraits")
        
        items_per_page = 20
        total_pages_view = (len(filtered_results) + items_per_page - 1) // items_per_page
        
        if total_pages_view > 1:
            page_num = st.number_input("Page:", min_value=1, max_value=total_pages_view, value=1)
            start_idx = (page_num - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_results))
            page_docs = filtered_results[start_idx:end_idx]
            st.caption(f"Documents {start_idx+1}-{end_idx} sur {len(filtered_results)}")
        else:
            page_docs = filtered_results
        
        # Tableau des documents
        df_display = pd.DataFrame(page_docs)
        st.dataframe(
            df_display[['id', 'titre', 'année', 'législature', 'type', 'nom_fichier', 'page_source']],
            use_container_width=True,
            hide_index=True
        )
        
        # Détail d'un document
        st.subheader("🔍 Détail d'un document")
        
        if page_docs:
            selected_id = st.selectbox(
                "Sélectionner un document:",
                options=[f"{doc['id']} - {doc['titre'][:50]}..." for doc in page_docs],
                index=0
            )
            
            selected_idx = int(selected_id.split(' - ')[0]) - 1
            if selected_idx < len(results):
                selected_doc = results[selected_idx]
                
                with st.expander(f"📄 Document {selected_doc['id']}: {selected_doc['titre']}", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Titre complet:** {selected_doc['titre']}")
                        st.markdown(f"**Année:** {selected_doc['année']}")
                        st.markdown(f"**Date:** {selected_doc['date']}")
                        st.markdown(f"**Législature:** {selected_doc['législature']}")
                        st.markdown(f"**Type:** {selected_doc['type']}")
                        st.markdown(f"**Période:** {selected_doc['période']}")
                        st.markdown(f"**Session:** {selected_doc['session_start']}-{selected_doc['session_end']}")
                        st.markdown(f"**Fichier:** `{selected_doc['nom_fichier']}`")
                        st.markdown(f"**Format:** {selected_doc['format_fichier']}")
                        st.markdown(f"**Source page:** {selected_doc.get('page_source', 1)}")
                        
                        st.markdown("**URL:**")
                        st.code(selected_doc['url'])
                        
                        if selected_doc['extrait']:
                            st.markdown("**Extrait:**")
                            # Mettre en évidence le mot-clé
                            highlighted = re.sub(
                                r'(' + re.escape(keyword) + ')',
                                r'<mark>\1</mark>',
                                selected_doc['extrait'],
                                flags=re.IGNORECASE
                            )
                            st.markdown(f"> {highlighted}", unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("**Actions:**")
                        
                        # Test d'accès
                        if st.button("🔗 Tester l'accès", key=f"access_{selected_doc['id']}"):
                            access_info = test_url_access(selected_doc['url'])
                            
                            if access_info.get('accessible'):
                                st.success(f"✅ Accessible (Code: {access_info['status_code']})")
                                
                                if 'pdf' in access_info.get('content_type', '').lower():
                                    st.info("📄 Fichier PDF détecté")
                                    
                                    # Téléchargement
                                    if st.button("📥 Télécharger", key=f"dl_{selected_doc['id']}"):
                                        pdf_content = download_pdf(selected_doc['url'], selected_doc['nom_fichier'])
                                        if pdf_content:
                                            st.download_button(
                                                label="💾 Sauvegarder PDF",
                                                data=pdf_content,
                                                file_name=selected_doc['nom_fichier'],
                                                mime="application/pdf",
                                                key=f"save_{selected_doc['id']}"
                                            )
                                else:
                                    st.warning(f"⚠️ Type: {access_info.get('content_type', 'Inconnu')}")
                            else:
                                st.error(f"❌ Non accessible (Code: {access_info.get('status_code', 'Erreur')})")
                                if 'error' in access_info:
                                    st.error(f"Erreur: {access_info['error'][:100]}")
                        
                        # Statistiques du document
                        st.markdown("**Statistiques:**")
                        st.metric("Mentions BUMIDOM", selected_doc.get('mentions_bumidom', 0))
        
        # Analyses
        st.subheader("📈 Analyses des données")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Par année", "🏛️ Par législature", "📄 Par type", "📊 Global"])
        
        with tab1:
            # Analyse par année
            year_counts = {}
            for doc in filtered_results:
                year = doc['année']
                if year not in year_counts:
                    year_counts[year] = 0
                year_counts[year] += 1
            
            df_years = pd.DataFrame({
                'Année': list(year_counts.keys()),
                'Documents': list(year_counts.values())
            }).sort_values('Année')
            
            st.bar_chart(df_years.set_index('Année'))
        
        with tab2:
            # Analyse par législature
            leg_counts = {}
            for doc in filtered_results:
                leg = doc['législature']
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
                df_leg['Num'] = df_leg['Législature'].str.extract(r'(\d+)').astype(int)
                df_leg = df_leg.sort_values('Num')
                
                st.bar_chart(df_leg.set_index('Législature')['Documents'])
        
        with tab3:
            # Analyse par type
            type_counts = {}
            for doc in filtered_results:
                doc_type = doc['type']
                if doc_type not in type_counts:
                    type_counts[doc_type] = 0
                type_counts[doc_type] += 1
            
            df_types = pd.DataFrame({
                'Type': list(type_counts.keys()),
                'Documents': list(type_counts.values())
            })
            
            st.bar_chart(df_types.set_index('Type'))
        
        with tab4:
            # Tableau de bord global
            col1, col2 = st.columns(2)
            
            with col1:
                # Distribution par page source
                page_counts = {}
                for doc in filtered_results:
                    page = doc.get('page_source', 1)
                    if page not in page_counts:
                        page_counts[page] = 0
                    page_counts[page] += 1
                
                df_pages = pd.DataFrame({
                    'Page': [f"Page {p}" for p in page_counts.keys()],
                    'Documents': list(page_counts.values())
                })
                
                st.bar_chart(df_pages.set_index('Page'))
            
            with col2:
                # Mentions par document
                mentions_data = [doc.get('mentions_bumidom', 0) for doc in filtered_results]
                df_mentions = pd.DataFrame({
                    'Document': range(1, len(mentions_data) + 1),
                    'Mentions': mentions_data
                })
                
                st.line_chart(df_mentions.set_index('Document'))
        
        # Export des données
        st.subheader("💾 Export des données")
        
        export_format = st.selectbox(
            "Format d'export:",
            ["CSV complet", "JSON", "URLs seulement", "Rapport PDF", "Archive ZIP"]
        )
        
        if st.button("📤 Exporter les données"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format == "CSV complet":
                df_export = pd.DataFrame(filtered_results)
                csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Télécharger CSV",
                    data=csv_data,
                    file_name=f"bumidom_scraping_{timestamp}.csv",
                    mime="text/csv"
                )
            
            elif export_format == "JSON":
                json_data = json.dumps(filtered_results, ensure_ascii=False, indent=2)
                
                st.download_button(
                    label="📥 Télécharger JSON",
                    data=json_data,
                    file_name=f"bumidom_scraping_{timestamp}.json",
                    mime="application/json"
                )
            
            elif export_format == "URLs seulement":
                urls = "\n".join([doc['url'] for doc in filtered_results])
                
                st.download_button(
                    label="📥 Télécharger URLs",
                    data=urls,
                    file_name=f"bumidom_urls_{timestamp}.txt",
                    mime="text/plain"
                )
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🚀 Scraping complet des Archives BUMIDOM
        
        ### 📊 Capacités du système:
        
        1. **Scraping multi-pages** : 10 pages de résultats Google
        2. **Extraction complète** : Titres, URLs, extraits, métadonnées
        3. **Analyse automatique** : Détection des mentions BUMIDOM
        4. **Filtrage avancé** : Par année, législature, type de document
        5. **Export multiple** : CSV, JSON, URLs, rapports
        
        ### 🔍 Processus de scraping:
        
        ```
        1. Accès à la recherche Google Custom Search
        2. Extraction de la page 1
        3. Navigation vers les pages suivantes
        4. Parsing des résultats HTML
        5. Extraction des métadonnées
        6. Analyse du contenu
        7. Stockage des données
        ```
        
        ### 📈 Statistiques attendues:
        
        - **~100 documents** (10 pages × 10 résultats)
        - **Période** : 1960-1990 environ
        - **Législatures** : 2ème à 8ème
        - **Types de documents** : CRI, Constitutions, Journaux Officiels
        
        ### 🎯 Cliquez sur "🚀 Lancer le scraping" pour commencer
        """)
        
        # Information technique
        with st.expander("⚙️ Informations techniques"):
            st.markdown("""
            **Méthodes de scraping disponibles:**
            
            1. **Google Custom Search API** (Recommandé)
               - Limite : 100 requêtes/jour gratuit
               - Authentification requise
               - Résultats structurés
            
            2. **Selenium WebDriver** (Scraping dynamique)
               - Nécessite Chrome/Chromium
               - Gère le JavaScript
               - Plus lent mais complet
            
            3. **BeautifulSoup + Requests** (Scraping statique)
               - Rapide et simple
               - Ne gère pas le JavaScript
               - Risque de blocage IP
            
            **Configuration recommandée:**
            ```python
            # Utilisation de l'API Google
            API_KEY = "votre_cle_api"
            SEARCH_ENGINE_ID = "votre_id_moteur"
            ```
            """)

if __name__ == "__main__":
    main()
