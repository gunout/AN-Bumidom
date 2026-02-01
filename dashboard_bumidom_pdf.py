import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin
import base64
from datetime import datetime
import io

# Configuration
st.set_page_config(
    page_title="Scraper BUMIDOM - Archives CRIs", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Scraper BUMIDOM - Comptes Rendus Intégraux (CRI)")
st.markdown("Scraping direct des CRI (Comptes Rendus Intégraux) de l'Assemblée Nationale")

class CRIBUMIDOMScraper:
    def __init__(self):
        self.base_url = "https://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
    
    def generate_cri_urls(self, start_year=1963, end_year=1982):
        """Génère les URLs des CRI pour chaque année"""
        
        cri_urls = []
        
        # Structure des URLs: /cri/YYYY-YYYY-ordinaireX
        # Exemple: /cri/1971-1972-ordinaire1
        
        for year in range(start_year, end_year + 1):
            # Format: année1-année2 (année scolaire parlementaire)
            next_year = year + 1
            year_range = f"{year}-{next_year}"
            
            # Essayer différents formats
            formats = [
                f"{self.base_url}/cri/{year_range}-ordinaire1",
                f"{self.base_url}/cri/{year_range}-ordinaire2", 
                f"{self.base_url}/cri/{year_range}-ordinaire",
                f"{self.base_url}/cri/{year_range}",
                f"{self.base_url}/{self.get_legislature(year)}/cri/{year_range}-ordinaire1",
                f"{self.base_url}/{self.get_legislature(year)}/cri/"
            ]
            
            for url_format in formats:
                cri_urls.append({
                    'url': url_format,
                    'year': year,
                    'range': year_range,
                    'legislature': self.get_legislature(year)
                })
        
        return cri_urls
    
    def get_legislature(self, year):
        """Retourne la législature pour une année donnée"""
        if 1958 <= year <= 1962:
            return "1"
        elif 1962 <= year <= 1967:
            return "2"  
        elif 1967 <= year <= 1968:
            return "3"
        elif 1968 <= year <= 1973:
            return "4"
        elif 1973 <= year <= 1978:
            return "5"
        elif 1978 <= year <= 1981:
            return "6"
        elif 1981 <= year <= 1986:
            return "7"
        elif 1986 <= year <= 1988:
            return "8"
        else:
            return ""
    
    def scrape_cri_page(self, cri_info, keyword="BUMIDOM"):
        """Scrape une page CRI spécifique"""
        
        results = []
        
        try:
            st.write(f"🔍 {cri_info['year']} (Lég. {cri_info['legislature']})...")
            
            response = self.session.get(cri_info['url'], timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Chercher tous les liens PDF sur la page
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for link in pdf_links:
                    href = link.get('href', '')
                    if href:
                        # Compléter l'URL si nécessaire
                        if not href.startswith('http'):
                            href = urljoin(cri_info['url'], href)
                        
                        # Vérifier que c'est bien une URL AN
                        if 'assemblee-nationale.fr' in href:
                            title = link.get_text(strip=True)
                            if not title or len(title) < 3:
                                # Essayer de trouver un titre dans le parent
                                parent = link.find_parent(['li', 'div', 'td'])
                                if parent:
                                    title = parent.get_text(strip=True)[:150]
                            
                            if not title:
                                title = href.split('/')[-1]
                            
                            # Vérifier si le lien semble contenir le mot-clé
                            link_text = link.get_text(strip=True).lower()
                            href_lower = href.lower()
                            
                            if (keyword.lower() in link_text or 
                                keyword.lower() in href_lower or
                                'bumidom' in link_text):
                                
                                pdf_info = {
                                    'url': href,
                                    'title': title[:200],
                                    'year': cri_info['year'],
                                    'legislature': cri_info['legislature'],
                                    'source_page': cri_info['url'],
                                    'found_by': 'lien direct'
                                }
                                
                                results.append(pdf_info)
                                st.write(f"  → PDF: {title[:80]}...")
                
                # Si pas de PDF trouvés directement, chercher des liens vers des pages avec PDF
                if not results:
                    # Chercher des liens vers d'autres pages de débats
                    debate_links = soup.find_all('a', href=re.compile(r'cri|debat|seance', re.I))
                    
                    for debate_link in debate_links[:10]:  # Limiter à 10
                        debate_href = debate_link.get('href', '')
                        if debate_href and not debate_href.endswith('.pdf'):
                            if not debate_href.startswith('http'):
                                debate_href = urljoin(cri_info['url'], debate_href)
                            
                            # Explorer cette page de débat
                            debate_results = self.explore_debate_page(debate_href, keyword, cri_info)
                            results.extend(debate_results)
                
                return results
                
            else:
                st.write(f"  ⚠️ Page non trouvée: {response.status_code}")
                return []
                
        except Exception as e:
            st.write(f"  ❌ Erreur: {str(e)[:100]}")
            return []
    
    def explore_debate_page(self, url, keyword, cri_info):
        """Explore une page de débat pour trouver des PDF"""
        
        results = []
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Chercher des PDF sur cette page
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for link in pdf_links:
                    href = link.get('href', '')
                    if href:
                        if not href.startswith('http'):
                            href = urljoin(url, href)
                        
                        if 'assemblee-nationale.fr' in href:
                            title = link.get_text(strip=True)
                            if not title:
                                title = href.split('/')[-1]
                            
                            # Vérifier la pertinence
                            if keyword.lower() in link.get_text(strip=True).lower():
                                pdf_info = {
                                    'url': href,
                                    'title': title[:200],
                                    'year': cri_info['year'],
                                    'legislature': cri_info['legislature'],
                                    'source_page': url,
                                    'found_by': 'exploration débat'
                                }
                                
                                if not any(r['url'] == href for r in results):
                                    results.append(pdf_info)
            
            return results
            
        except:
            return []
    
    def search_specific_years(self, years_list, keyword="BUMIDOM"):
        """Recherche spécifique sur les années où BUMIDOM était actif"""
        
        st.info(f"Recherche sur {len(years_list)} années spécifiques...")
        
        all_results = []
        
        for year in years_list:
            # Générer l'URL pour cette année
            next_year = year + 1
            year_range = f"{year}-{next_year}"
            
            # Essayer plusieurs formats d'URL
            url_patterns = [
                f"{self.base_url}/cri/{year_range}-ordinaire1",
                f"{self.base_url}/{self.get_legislature(year)}/cri/{year_range}-ordinaire1",
                f"{self.base_url}/{self.get_legislature(year)}/cri/",
            ]
            
            for url in url_patterns:
                cri_info = {
                    'url': url,
                    'year': year,
                    'range': year_range,
                    'legislature': self.get_legislature(year)
                }
                
                results = self.scrape_cri_page(cri_info, keyword)
                all_results.extend(results)
                
                if results:
                    break  # Passer à l'année suivante si on a trouvé quelque chose
                
                time.sleep(0.5)  # Pause courte
        
        return all_results
    
    def analyze_pdf_simple(self, pdf_url, keyword="BUMIDOM"):
        """Analyse simple d'un PDF pour trouver le mot-clé"""
        
        try:
            # Télécharger seulement le début du PDF pour vérifier
            headers = {'Range': 'bytes=0-50000'}  # Premier 50KB
            response = self.session.get(pdf_url, headers=headers, timeout=15)
            
            if response.status_code in [200, 206]:  # 206 = Partial Content
                content = response.content
                
                # Convertir en texte (pour PDF textuels)
                try:
                    text = content.decode('utf-8', errors='ignore')
                    
                    # Rechercher le mot-clé
                    keyword_lower = keyword.lower()
                    text_lower = text.lower()
                    
                    if keyword_lower in text_lower:
                        # Compter les occurrences
                        occurrences = text_lower.count(keyword_lower)
                        
                        # Extraire un contexte
                        start_pos = text_lower.find(keyword_lower)
                        if start_pos != -1:
                            start = max(0, start_pos - 150)
                            end = min(len(text), start_pos + len(keyword) + 150)
                            context = text[start:end].replace('\n', ' ').strip()
                        else:
                            context = ""
                        
                        return {
                            'contains_keyword': True,
                            'occurrences': occurrences,
                            'context': context,
                            'error': None
                        }
                    else:
                        return {
                            'contains_keyword': False,
                            'occurrences': 0,
                            'context': "",
                            'error': None
                        }
                        
                except:
                    # PDF binaire ou encodé différemment
                    # Essayer de chercher dans les bytes
                    if keyword.lower().encode() in content.lower():
                        return {
                            'contains_keyword': True,
                            'occurrences': 1,  # Approximation
                            'context': "PDF binaire - mot-clé détecté dans les bytes",
                            'error': 'PDF binaire'
                        }
                    else:
                        return {
                            'contains_keyword': False,
                            'occurrences': 0,
                            'context': "",
                            'error': 'PDF binaire'
                        }
            else:
                return {
                    'contains_keyword': False,
                    'occurrences': 0,
                    'context': "",
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'contains_keyword': False,
                'occurrences': 0,
                'context': "",
                'error': str(e)[:100]
            }
    
    def get_pdf_preview(self, pdf_url):
        """Génère un aperçu PDF pour affichage"""
        try:
            response = self.session.get(pdf_url, timeout=15)
            if response.status_code == 200:
                b64_pdf = base64.b64encode(response.content).decode()
                pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500"></iframe>'
                return pdf_display
        except:
            return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        keyword = st.text_input("Mot-clé:", value="BUMIDOM")
        
        # Années spécifiques basées sur vos résultats
        default_years = [1966, 1968, 1970, 1971, 1976, 1982, 1985, 1986]
        selected_years = st.multiselect(
            "Années à scraper:",
            list(range(1963, 1987)),
            default=default_years
        )
        
        col1, col2 = st.columns(2)
        with col1:
            max_pdfs = st.slider("PDF max:", 10, 100, 30)
        with col2:
            auto_analyze = st.checkbox("Analyser automatiquement", value=True)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            search_btn = st.button("🔍 Scraper les CRI", use_container_width=True)
        with col_btn2:
            clear_btn = st.button("🧹 Réinitialiser", type="secondary", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **URLs trouvées:**
        - /cri/1971-1972-ordinaire1
        - /cri/1968-1969-ordinaire1  
        - /cri/1966-1967-ordinaire1
        - /cri/1982-1983-ordinaire1
        """)
    
    # État de session
    if 'pdf_results' not in st.session_state:
        st.session_state.pdf_results = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    
    if clear_btn:
        st.session_state.pdf_results = []
        st.session_state.analysis_results = []
        st.rerun()
    
    # Scraper principal
    if search_btn:
        if not selected_years:
            st.warning("Veuillez sélectionner au moins une année")
        else:
            scraper = CRIBUMIDOMScraper()
            
            with st.spinner(f"Scraping des CRI pour {len(selected_years)} années..."):
                # Recherche sur les années sélectionnées
                pdf_results = scraper.search_specific_years(selected_years, keyword)
                st.session_state.pdf_results = pdf_results[:max_pdfs]
                
                if pdf_results:
                    st.success(f"✅ {len(pdf_results)} PDF trouvés")
                    
                    # Analyse automatique si demandée
                    if auto_analyze and pdf_results:
                        with st.spinner("Analyse du contenu des PDF..."):
                            analysis_results = []
                            
                            for pdf in st.session_state.pdf_results:
                                analysis = scraper.analyze_pdf_simple(pdf['url'], keyword)
                                analysis_results.append({
                                    **pdf,
                                    **analysis
                                })
                            
                            st.session_state.analysis_results = analysis_results
                
                else:
                    st.warning("❌ Aucun PDF trouvé")
    
    # Affichage des résultats
    if st.session_state.pdf_results:
        st.subheader(f"📊 {len(st.session_state.pdf_results)} PDF trouvés")
        
        # Tableau des résultats
        df = pd.DataFrame(st.session_state.pdf_results)
        
        # Statistiques
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PDF total", len(df))
        with col2:
            st.metric("Années", df['year'].nunique())
        with col3:
            st.metric("Législatures", df['legislature'].nunique())
        with col4:
            if st.session_state.analysis_results:
                with_keyword = len([r for r in st.session_state.analysis_results if r.get('contains_keyword')])
                st.metric("Contient BUMIDOM", with_keyword)
        
        # Afficher les PDF avec analyse si disponible
        if st.session_state.analysis_results:
            st.subheader("📋 PDF analysés")
            
            # Filtrer ceux qui contiennent le mot-clé
            pdfs_with_keyword = [r for r in st.session_state.analysis_results if r.get('contains_keyword')]
            
            if pdfs_with_keyword:
                st.success(f"🎯 {len(pdfs_with_keyword)} PDF contiennent '{keyword}'")
                
                for idx, pdf in enumerate(pdfs_with_keyword):
                    with st.expander(f"📅 {pdf['year']} - {pdf['title'][:80]}... ({pdf['occurrences']} occ.)"):
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            st.markdown(f"**URL:** `{pdf['url']}`")
                            st.markdown(f"**Législature:** {pdf['legislature']}ème")
                            st.markdown(f"**Année:** {pdf['year']}")
                            st.markdown(f"**Occurrences:** {pdf['occurrences']}")
                            st.markdown(f"**Source:** {pdf.get('found_by', 'N/A')}")
                            
                            if pdf.get('context'):
                                st.markdown("**Contexte:**")
                                highlighted = re.sub(
                                    r'(' + re.escape(keyword) + ')',
                                    r'**\1**',
                                    pdf['context'],
                                    flags=re.IGNORECASE
                                )
                                st.markdown(f"> {highlighted}")
                        
                        with col_b:
                            st.markdown(f"[🌐 Ouvrir PDF]({pdf['url']})", unsafe_allow_html=True)
                            
                            # Prévisualisation
                            if st.button("👁️ Prévisualiser", key=f"preview_{idx}"):
                                scraper = CRIBUMIDOMScraper()
                                preview = scraper.get_pdf_preview(pdf['url'])
                                if preview:
                                    st.markdown(preview, unsafe_allow_html=True)
                                else:
                                    st.warning("Prévisualisation non disponible")
                
                # Export
                st.subheader("💾 Export")
                
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    # CSV des PDF avec mot-clé
                    df_keyword = pd.DataFrame(pdfs_with_keyword)
                    csv_data = df_keyword.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 PDF avec BUMIDOM",
                        data=csv_data,
                        file_name=f"bumidom_cri_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                with col_exp2:
                    # Tous les résultats
                    df_all = pd.DataFrame(st.session_state.analysis_results)
                    csv_all = df_all.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📊 Tous les résultats",
                        data=csv_all,
                        file_name=f"cri_complet_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            else:
                st.warning(f"Aucun PDF ne contient '{keyword}'")
        
        # Afficher tous les PDF trouvés
        st.subheader("📚 Tous les PDF trouvés")
        
        for idx, pdf in enumerate(st.session_state.pdf_results):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{pdf['title'][:100]}...**")
                st.caption(f"Année: {pdf['year']} | Législature: {pdf['legislature']}")
            
            with col2:
                st.markdown(f"[🔗 Lien]({pdf['url']})", unsafe_allow_html=True)
            
            with col3:
                if st.button("📥 Télécharger", key=f"dl_{idx}"):
                    try:
                        response = requests.get(pdf['url'])
                        st.download_button(
                            label="Cliquer pour télécharger",
                            data=response.content,
                            file_name=pdf['url'].split('/')[-1],
                            mime="application/pdf",
                            key=f"dld_{idx}"
                        )
                    except:
                        st.warning("Erreur téléchargement")
    
    else:
        # Écran d'accueil avec les URLs trouvées
        st.markdown("""
        ## 🎯 URLs de CRI trouvées
        
        Basé sur vos résultats, voici les patterns d'URLs identifiés:
        
        ### 📁 Structure des URLs:
        ```
        https://archives.assemblee-nationale.fr/cri/AAAA-AAAA-ordinaireX
        ```
        
        ### 📅 Exemples concrets:
        """)
        
        # Table des URLs trouvées
        urls_data = [
            {"Année": "1966-1967", "URL": "/cri/1966-1967-ordinaire1", "Législature": "3ème"},
            {"Année": "1968-1969", "URL": "/cri/1968-1969-ordinaire1", "Législature": "4ème"},
            {"Année": "1970-1971", "URL": "/cri/1970-1971-ordinaire1", "Législature": "4ème"},
            {"Année": "1971-1972", "URL": "/cri/1971-1972-ordinaire1", "Législature": "4ème"},
            {"Année": "1976-1977", "URL": "/cri/1976-1977-ordinaire2", "Législature": "5ème"},
            {"Année": "1982-1983", "URL": "/cri/1982-1983-ordinaire1", "Législature": "7ème"},
            {"Année": "1985-1986", "URL": "/cri/1985-1986-extraordinaire1", "Législature": "8ème"},
        ]
        
        df_urls = pd.DataFrame(urls_data)
        st.dataframe(df_urls, use_container_width=True)
        
        st.markdown("""
        ### 🚀 Comment utiliser:
        
        1. **Sélectionnez les années** dans la sidebar (1966, 1968, 1970, 1971, 1976, 1982, 1985 sont pré-sélectionnées)
        2. **Cliquez sur "🔍 Scraper les CRI"**
        3. **Attendez** 1-2 minutes pour le scraping
        4. **Explorez** les PDF trouvés
        
        ### 🔍 Ce que fait le scraper:
        
        - Accède directement aux URLs des Comptes Rendus Intégraux (CRI)
        - Cherche tous les liens PDF sur chaque page
        - Analyse le contenu pour trouver "BUMIDOM"
        - Extrait le contexte des mentions
        - Permet de télécharger et prévisualiser les PDF
        """)

# Installation
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Installation")
st.sidebar.code("pip install streamlit requests beautifulsoup4 pandas")

if __name__ == "__main__":
    main()
