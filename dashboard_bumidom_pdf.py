import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from urllib.parse import urljoin, quote, urlparse
import json
from datetime import datetime
import io

# Configuration
st.set_page_config(
    page_title="Scraper BUMIDOM - Archives AN", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Scraper BUMIDOM - Archives de l'Assemblée Nationale")
st.markdown("Recherche et analyse des documents PDF mentionnant BUMIDOM")

class SimpleBUMIDOMScraper:
    def __init__(self):
        self.base_url = "https://www.assemblee-nationale.fr"
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
    def create_session(self):
        """Crée une session HTTP avec des headers réalistes"""
        session = requests.Session()
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        session.headers.update(headers)
        return session
    
    def search_google_simple(self, keyword="BUMIDOM", max_results=100):
        """Utilise Google Search pour trouver des PDF sur le site AN"""
        
        st.info(f"Recherche Google pour '{keyword}'...")
        
        all_pdf_links = []
        
        # Construction de la requête Google
        query = f'site:assemblee-nationale.fr filetype:pdf "{keyword}"'
        encoded_query = quote(query)
        
        # Plusieurs pages de résultats Google
        for page in range(0, 10):  # 10 pages max
            start = page * 10
            
            try:
                st.write(f"🔍 Page Google {page + 1}...")
                
                # URL Google Search
                google_url = f"https://www.google.com/search?q={encoded_query}&start={start}"
                
                session = self.create_session()
                response = session.get(google_url, timeout=15)
                
                if response.status_code != 200:
                    st.warning(f"Google a retourné {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Chercher tous les liens dans les résultats
                all_links = soup.find_all('a')
                
                for link in all_links:
                    href = link.get('href', '')
                    
                    # Nettoyer les URLs Google
                    if href.startswith('/url?q='):
                        # Extraire l'URL réelle du paramètre Google
                        url_match = re.search(r'/url\?q=([^&]+)', href)
                        if url_match:
                            real_url = requests.utils.unquote(url_match.group(1))
                            
                            # Vérifier si c'est un PDF de l'AN
                            if (real_url.endswith('.pdf') or '.pdf?' in real_url) and \
                               'assemblee-nationale.fr' in real_url and \
                               keyword.lower() in real_url.lower():
                                
                                # Récupérer le titre
                                title = link.get_text(strip=True)
                                if not title or len(title) < 5:
                                    # Chercher un titre dans les parents
                                    parent = link.find_parent(['h3', 'div'])
                                    if parent:
                                        title = parent.get_text(strip=True)
                                
                                if not title:
                                    title = real_url.split('/')[-1]
                                
                                pdf_info = {
                                    'url': real_url,
                                    'title': title[:200],
                                    'source': 'Google Search',
                                    'page': page + 1,
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                # Éviter les doublons
                                if not any(p['url'] == real_url for p in all_pdf_links):
                                    all_pdf_links.append(pdf_info)
                                    st.write(f"  → PDF: {title[:80]}...")
                
                # Pause pour respecter Google
                time.sleep(random.uniform(2, 4))
                
                # Arrêter si on a assez de résultats
                if len(all_pdf_links) >= max_results:
                    break
                    
            except Exception as e:
                st.warning(f"Erreur page {page + 1}: {str(e)[:100]}")
                continue
        
        return all_pdf_links[:max_results]
    
    def search_direct_archives(self, keyword="BUMIDOM"):
        """Cherche directement dans les archives connues"""
        
        st.info("Recherche dans les archives directes...")
        
        all_pdf_links = []
        
        # URLs d'archives connues pour chaque législature
        archive_urls = [
            # 5ème législature (1973-1978) - Période BUMIDOM active
            ("https://archives.assemblee-nationale.fr/5/qst/", "Questions 5ème lég."),
            ("https://archives.assemblee-nationale.fr/5/cri/", "Débats 5ème lég."),
            
            # 6ème législature (1978-1981)
            ("https://archives.assemblee-nationale.fr/6/qst/", "Questions 6ème lég."),
            ("https://archives.assemblee-nationale.fr/6/cri/", "Débats 6ème lég."),
            
            # 4ème législature (1968-1973)
            ("https://archives.assemblee-nationale.fr/4/qst/", "Questions 4ème lég."),
            ("https://archives.assemblee-nationale.fr/4/cri/", "Débats 4ème lég."),
            
            # 7ème législature (1981-1986)
            ("https://archives.assemblee-nationale.fr/7/qst/", "Questions 7ème lég."),
            ("https://archives.assemblee-nationale.fr/7/cri/", "Débats 7ème lég."),
        ]
        
        session = self.create_session()
        
        for url, description in archive_urls:
            try:
                st.write(f"📂 {description}...")
                
                response = session.get(url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Chercher tous les liens PDF
                    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    
                    for link in pdf_links[:50]:  # Limiter à 50 par page
                        href = link.get('href', '')
                        
                        if href:
                            # Compléter l'URL si nécessaire
                            if not href.startswith('http'):
                                href = urljoin(url, href)
                            
                            # Vérifier si l'URL contient le mot-clé ou semble pertinente
                            title = link.get_text(strip=True)
                            
                            # Vérifier dans le titre ou l'URL
                            if (keyword.lower() in title.lower() or 
                                keyword.lower() in href.lower() or
                                'bumidom' in title.lower() or
                                'bumidom' in href.lower()):
                                
                                pdf_info = {
                                    'url': href,
                                    'title': title[:200] if title else href.split('/')[-1],
                                    'source': description,
                                    'page': 1,
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                if not any(p['url'] == href for p in all_pdf_links):
                                    all_pdf_links.append(pdf_info)
                                    st.write(f"  → Archive: {title[:80]}...")
                
                time.sleep(1)  # Pause entre les pages
                
            except Exception as e:
                st.warning(f"Erreur {description}: {str(e)[:100]}")
                continue
        
        return all_pdf_links
    
    def search_gallica_bnf(self, keyword="BUMIDOM"):
        """Cherche dans Gallica BnF (Journal Officiel)"""
        
        st.info("Recherche dans Gallica BnF (Journal Officiel)...")
        
        all_pdf_links = []
        
        # Gallica BnF - Journal Officiel des années BUMIDOM
        for year in range(1963, 1983):  # 1963-1982
            try:
                st.write(f"📅 {year}...")
                
                # URL de recherche Gallica
                query = f'"{keyword}" "Journal Officiel" {year}'
                encoded_query = quote(query)
                
                gallica_url = f"https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&query={encoded_query}&version=1.2"
                
                session = self.create_session()
                response = session.get(gallica_url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Chercher les liens dans la réponse SRU
                    for link in soup.find_all('uri'):
                        uri = link.get_text(strip=True)
                        if uri and '.pdf' in uri:
                            pdf_info = {
                                'url': uri,
                                'title': f"Journal Officiel {year} - {keyword}",
                                'source': f"Gallica BnF {year}",
                                'page': 1,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if not any(p['url'] == uri for p in all_pdf_links):
                                all_pdf_links.append(pdf_info)
                                st.write(f"  → Gallica: Journal Officiel {year}")
                
                time.sleep(1)
                
            except Exception as e:
                st.warning(f"Erreur année {year}: {str(e)[:100]}")
                continue
        
        return all_pdf_links
    
    def check_pdf_content(self, pdf_url, keyword="BUMIDOM"):
        """Vérifie si un PDF contient le mot-clé (méthode simple)"""
        try:
            session = self.create_session()
            
            # Télécharger seulement les premiers Ko pour vérifier
            headers = {'Range': 'bytes=0-100000'}  # Premier 100KB
            response = session.get(pdf_url, headers=headers, timeout=15, stream=True)
            
            if response.status_code in [200, 206]:  # 206 = Partial Content
                # Lire le contenu
                content = response.content
                
                # Convertir en texte (méthode simple pour les PDF textuels)
                try:
                    # Essayer de décoder en UTF-8
                    text = content.decode('utf-8', errors='ignore')
                    
                    # Rechercher le mot-clé
                    if keyword.lower() in text.lower():
                        # Compter les occurrences
                        occurrences = text.lower().count(keyword.lower())
                        
                        # Extraire un extrait
                        start_pos = text.lower().find(keyword.lower())
                        if start_pos != -1:
                            excerpt_start = max(0, start_pos - 100)
                            excerpt_end = min(len(text), start_pos + len(keyword) + 100)
                            excerpt = text[excerpt_start:excerpt_end].replace('\n', ' ').strip()
                        else:
                            excerpt = ""
                        
                        return {
                            'contains_keyword': True,
                            'occurrences': occurrences,
                            'excerpt': excerpt,
                            'error': None
                        }
                    else:
                        return {
                            'contains_keyword': False,
                            'occurrences': 0,
                            'excerpt': "",
                            'error': None
                        }
                        
                except:
                    # PDF binaire ou encodé différemment
                    return {
                        'contains_keyword': None,  # Inconnu
                        'occurrences': 0,
                        'excerpt': "",
                        'error': 'PDF binaire (OCR nécessaire)'
                    }
            else:
                return {
                    'contains_keyword': False,
                    'occurrences': 0,
                    'excerpt': "",
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'contains_keyword': False,
                'occurrences': 0,
                'excerpt': "",
                'error': str(e)[:100]
            }
    
    def multi_search(self, keyword="BUMIDOM", max_results=100):
        """Combine plusieurs méthodes de recherche"""
        
        st.info(f"Lancement de la recherche multi-sources pour '{keyword}'...")
        
        all_pdf_links = []
        
        # Méthodes de recherche
        methods = [
            ("Google Search", self.search_google_simple),
            ("Archives directes", self.search_direct_archives),
            ("Gallica BnF", self.search_gallica_bnf),
        ]
        
        progress_bar = st.progress(0)
        
        for idx, (method_name, method_func) in enumerate(methods):
            progress = (idx + 1) / len(methods)
            progress_bar.progress(progress)
            
            st.write(f"🔍 {method_name}...")
            
            try:
                results = method_func(keyword)
                
                # Fusionner les résultats
                for pdf in results:
                    if not any(p['url'] == pdf['url'] for p in all_pdf_links):
                        all_pdf_links.append(pdf)
                
                st.success(f"  → {len(results)} PDF trouvés")
                time.sleep(1)
                
            except Exception as e:
                st.warning(f"  → {method_name} échoué: {str(e)[:100]}")
        
        progress_bar.empty()
        
        return all_pdf_links[:max_results]

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        keyword = st.text_input("Mot-clé de recherche:", value="BUMIDOM")
        
        search_method = st.selectbox(
            "Méthode de recherche:",
            [
                "Multi-sources (recommandé)",
                "Google Search uniquement",
                "Archives directes",
                "Gallica BnF",
                "Test rapide"
            ]
        )
        
        max_results = st.slider("Résultats maximum:", 10, 200, 50)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            search_btn = st.button("🔍 Rechercher PDF", use_container_width=True)
        
        with col2:
            analyze_btn = st.button("🔬 Vérifier contenu", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Sources disponibles:**
        1. Google Search
        2. Archives AN directes
        3. Gallica BnF (JO)
        
        **Période cible:** 1963-1982
        """)
    
    # Initialisation
    scraper = SimpleBUMIDOMScraper()
    
    # État de session
    if 'pdf_links' not in st.session_state:
        st.session_state.pdf_links = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    
    # Actions
    if search_btn:
        with st.spinner("Recherche en cours..."):
            if search_method == "Multi-sources (recommandé)":
                pdf_links = scraper.multi_search(keyword, max_results)
            elif search_method == "Google Search uniquement":
                pdf_links = scraper.search_google_simple(keyword, max_results)
            elif search_method == "Archives directes":
                pdf_links = scraper.search_direct_archives(keyword)
            elif search_method == "Gallica BnF":
                pdf_links = scraper.search_gallica_bnf()
            else:
                # Test rapide
                pdf_links = scraper.search_direct_archives(keyword)[:10]
            
            st.session_state.pdf_links = pdf_links
            
            if pdf_links:
                st.success(f"✅ {len(pdf_links)} PDF trouvés")
                
                # Afficher les résultats
                df = pd.DataFrame(pdf_links)
                
                # Statistiques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("PDF trouvés", len(df))
                with col2:
                    sources = df['source'].nunique()
                    st.metric("Sources", sources)
                with col3:
                    unique_urls = df['url'].nunique()
                    st.metric("URLs uniques", unique_urls)
                
                # Table des résultats
                st.subheader("📋 Liste des PDF trouvés")
                
                for idx, pdf in enumerate(pdf_links):
                    with st.expander(f"{idx+1}. {pdf['title'][:80]}..."):
                        st.markdown(f"**URL:** `{pdf['url']}`")
                        st.markdown(f"**Source:** {pdf['source']}")
                        st.markdown(f"[🔗 Ouvrir le PDF]({pdf['url']})", unsafe_allow_html=True)
                
                # Export
                st.subheader("💾 Export")
                csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Télécharger la liste",
                    data=csv_data,
                    file_name=f"bumidom_urls_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.warning("❌ Aucun PDF trouvé")
                
                with st.expander("💡 Conseils de recherche"):
                    st.markdown("""
                    **Pour trouver des documents BUMIDOM:**
                    
                    1. **Recherchez manuellement sur:**
                       - [Archives AN - 5ème législature](https://archives.assemblee-nationale.fr/5/qst/)
                       - [Archives AN - 6ème législature](https://archives.assemblee-nationale.fr/6/qst/)
                       - [Gallica BnF](https://gallica.bnf.fr)
                    
                    2. **Termes alternatifs:**
                       - "Bureau des migrations"
                       - "Migration outre-mer"
                       - "DOM TOM migration"
                       - "Départements d'outre-mer"
                    
                    3. **Périodes clés:**
                       - 1973-1978 (5ème législature)
                       - 1978-1981 (6ème législature)
                    """)
    
    elif analyze_btn:
        if not st.session_state.pdf_links:
            st.warning("Veuillez d'abord rechercher des PDF")
        else:
            with st.spinner(f"Vérification du contenu pour {len(st.session_state.pdf_links[:max_results])} PDF..."):
                results = []
                
                for pdf_info in st.session_state.pdf_links[:max_results]:
                    st.write(f"🔎 Vérification: {pdf_info['title'][:50]}...")
                    
                    analysis = scraper.check_pdf_content(pdf_info['url'], keyword)
                    
                    result = {
                        **pdf_info,
                        **analysis
                    }
                    
                    results.append(result)
                    
                    if analysis['contains_keyword']:
                        st.success(f"  → Contient '{keyword}' ({analysis['occurrences']} occ.)")
                    elif analysis['contains_keyword'] is None:
                        st.info("  → PDF binaire (nécessite OCR)")
                    else:
                        st.write("  → Ne contient pas le mot-clé")
                
                st.session_state.analysis_results = results
                
                # Filtrer les PDF avec le mot-clé
                pdfs_with_keyword = [r for r in results if r.get('contains_keyword')]
                
                if pdfs_with_keyword:
                    st.success(f"✅ {len(pdfs_with_keyword)} PDF contiennent '{keyword}'")
                    
                    st.subheader("📋 PDF contenant BUMIDOM")
                    
                    for pdf in pdfs_with_keyword:
                        with st.expander(f"📄 {pdf['title'][:80]}... ({pdf['occurrences']} occ.)"):
                            col_a, col_b = st.columns([3, 1])
                            
                            with col_a:
                                st.markdown(f"**URL:** `{pdf['url']}`")
                                st.markdown(f"**Source:** {pdf['source']}")
                                st.markdown(f"**Occurrences:** {pdf['occurrences']}")
                                
                                if pdf.get('excerpt'):
                                    st.markdown("**Extrait:**")
                                    highlighted = re.sub(
                                        r'(' + re.escape(keyword) + ')',
                                        r'**\1**',
                                        pdf['excerpt'],
                                        flags=re.IGNORECASE
                                    )
                                    st.markdown(f"> {highlighted}")
                            
                            with col_b:
                                st.markdown(f"[🌐 Ouvrir PDF]({pdf['url']})", unsafe_allow_html=True)
                    
                    # Export des analyses
                    st.subheader("💾 Export des analyses")
                    df_analysis = pd.DataFrame(pdfs_with_keyword)
                    csv_analysis = df_analysis.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Télécharger analyses",
                        data=csv_analysis,
                        file_name=f"bumidom_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                    
                else:
                    st.warning(f"❌ Aucun des PDF analysés ne contient '{keyword}'")
                    
                    # Afficher quand même les résultats
                    if results:
                        st.subheader("📊 Résultats d'analyse")
                        df_all = pd.DataFrame(results)
                        st.dataframe(df_all[['title', 'contains_keyword', 'occurrences', 'error']])
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 📋 Scraper BUMIDOM - Archives AN
        
        Ce dashboard recherche des documents PDF mentionnant **BUMIDOM** dans les archives parlementaires.
        
        ### 🎯 Période cible: 1963-1982
        - **Création BUMIDOM:** 1963
        - **Activité principale:** 1963-1982
        - **Sources principales:** Questions écrites, débats parlementaires
        
        ### 🔍 Méthodes de recherche:
        
        **1. Google Search**
        - Recherche: `site:assemblee-nationale.fr filetype:pdf "BUMIDOM"`
        - Avantage: Index complet de Google
        - Limite: Peut manquer des documents non indexés
        
        **2. Archives directes**
        - Accède directement aux URLs connues
        - Législatures 4 à 7 (1968-1986)
        - Questions écrites et débats
        
        **3. Gallica BnF**
        - Journal Officiel historique
        - Archives complètes 1963-1982
        - PDF parfois scannés (OCR nécessaire)
        
        ### 🚀 Comment utiliser:
        
        1. **Cliquez sur "🔍 Rechercher PDF"** (Multi-sources recommandé)
        2. **Puis sur "🔬 Vérifier contenu"** pour analyser les PDF
        3. **Exportez** les résultats en CSV
        
        ### ⚠️ Notes importantes:
        
        - Certains PDF sont scannés (nécessitent OCR)
        - La recherche peut prendre 1-2 minutes
        - Respectez les limites de requêtes
        """)

# Installation requirements
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Installation")
st.sidebar.code("""
pip install streamlit requests beautifulsoup4 pandas
""")

if __name__ == "__main__":
    main()
