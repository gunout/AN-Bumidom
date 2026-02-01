import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin
import base64
from datetime import datetime

# Configuration
st.set_page_config(
    page_title="Scraper BUMIDOM - URLs Directes", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Scraper BUMIDOM - URLs Directes Trouvées")
st.markdown("Utilisation des URLs exactes trouvées dans vos résultats")

class DirectURLScraper:
    def __init__(self):
        self.base_url = "https://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def get_direct_urls_from_your_results(self):
        """URLs exactes basées sur vos résultats"""
        
        # URLs EXACTES trouvées dans vos résultats
        direct_urls = [
            # Format: /cri/ANNEE-ANNEE-ordinaireNUMERO
            {
                'url': f"{self.base_url}/cri/1971-1972-ordinaire1",
                'year': 1971,
                'description': "CRI 1971-1972 ordinaire1 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1968-1969-ordinaire1", 
                'year': 1968,
                'description': "CRI 1968-1969 ordinaire1 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1966-1967-ordinaire1",
                'year': 1966,
                'description': "CRI 1966-1967 ordinaire1 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1982-1983-ordinaire1",
                'year': 1982,
                'description': "CRI 1982-1983 ordinaire1 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1976-1977-ordinaire2",
                'year': 1976,
                'description': "CRI 1976-1977 ordinaire2 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1970-1971-ordinaire1",
                'year': 1970,
                'description': "CRI 1970-1971 ordinaire1 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1985-1986-extraordinaire1",
                'year': 1985,
                'description': "CRI 1985-1986 extraordinaire1 - Mention BUMIDOM trouvée"
            },
            {
                'url': f"{self.base_url}/cri/1970-1971-ordinaire2",
                'year': 1970,
                'description': "CRI 1970-1971 ordinaire2 - Mention BUMIDOM trouvée"
            },
        ]
        
        return direct_urls
    
    def scrape_direct_url(self, url_info, keyword="BUMIDOM"):
        """Scrape une URL directe spécifique"""
        
        results = []
        
        try:
            st.write(f"🔍 {url_info['year']} - {url_info['description'][:50]}...")
            
            response = self.session.get(url_info['url'], timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # OPTION 1: Chercher des liens PDF directs
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                if pdf_links:
                    st.success(f"  → {len(pdf_links)} PDF trouvé(s) sur la page")
                    
                    for link in pdf_links:
                        href = link.get('href', '')
                        if href:
                            # Compléter l'URL
                            if not href.startswith('http'):
                                href = urljoin(url_info['url'], href)
                            
                            title = link.get_text(strip=True)
                            if not title:
                                title = href.split('/')[-1]
                            
                            pdf_info = {
                                'url': href,
                                'title': title[:200],
                                'source_url': url_info['url'],
                                'year': url_info['year'],
                                'description': url_info['description'],
                                'type': 'pdf_direct'
                            }
                            
                            results.append(pdf_info)
                
                # OPTION 2: Si pas de PDF directs, vérifier si la page EST un PDF
                elif 'pdf' in response.headers.get('content-type', '').lower():
                    # La page elle-même est un PDF
                    pdf_info = {
                        'url': url_info['url'],
                        'title': f"CRI {url_info['year']}",
                        'source_url': url_info['url'],
                        'year': url_info['year'],
                        'description': url_info['description'],
                        'type': 'page_is_pdf'
                    }
                    results.append(pdf_info)
                    st.success("  → La page est elle-même un PDF")
                
                # OPTION 3: Chercher dans le contenu HTML
                else:
                    # Extraire tout le texte
                    all_text = soup.get_text()
                    
                    # Vérifier si le mot-clé est dans la page
                    if keyword.lower() in all_text.lower():
                        # Chercher des liens vers d'autres ressources
                        all_links = soup.find_all('a', href=True)
                        
                        for link in all_links[:20]:  # Limiter aux 20 premiers
                            href = link.get('href', '')
                            if href and ('pdf' in href.lower() or 'cri' in href.lower()):
                                if not href.startswith('http'):
                                    href = urljoin(url_info['url'], href)
                                
                                title = link.get_text(strip=True)
                                if not title:
                                    title = f"Document {url_info['year']}"
                                
                                pdf_info = {
                                    'url': href,
                                    'title': title[:200],
                                    'source_url': url_info['url'],
                                    'year': url_info['year'],
                                    'description': url_info['description'],
                                    'type': 'html_link'
                                }
                                
                                results.append(pdf_info)
                        
                        if results:
                            st.success(f"  → {len(results)} liens trouvés dans le HTML")
                    
                    else:
                        st.warning("  → Mot-clé non trouvé sur la page")
                
                return results
                
            elif response.status_code == 403:
                st.error(f"  ❌ Accès interdit (403) - Protection anti-bot")
                return []
                
            elif response.status_code == 404:
                st.warning(f"  ⚠️ Page non trouvée (404)")
                
                # Essayer des variantes
                return self.try_url_variations(url_info)
                
            else:
                st.warning(f"  ⚠️ Erreur HTTP {response.status_code}")
                return []
                
        except Exception as e:
            st.error(f"  ❌ Erreur: {str(e)[:100]}")
            return []
    
    def try_url_variations(self, url_info):
        """Essaye différentes variations d'URL"""
        
        variations = []
        base_path = url_info['url'].replace(self.base_url, "")
        
        # Variation 1: Ajouter .pdf à la fin
        variations.append(f"{url_info['url']}.pdf")
        
        # Variation 2: Changer l'ordre des paramètres
        if 'ordinaire' in base_path:
            variations.append(url_info['url'].replace('ordinaire', 'extraordinaire'))
        
        # Variation 3: Essayer avec numéro de législature
        legislature = self.get_legislature(url_info['year'])
        if legislature:
            variations.append(f"{self.base_url}/{legislature}{base_path}")
        
        for variation in variations:
            try:
                st.write(f"  ↳ Essai variation: {variation.split('/')[-1]}")
                
                response = self.session.get(variation, timeout=10)
                if response.status_code == 200:
                    st.success(f"    → Variation fonctionnelle trouvée!")
                    
                    return [{
                        'url': variation,
                        'title': f"CRI {url_info['year']} (variation)",
                        'source_url': url_info['url'],
                        'year': url_info['year'],
                        'description': f"Variation de {url_info['description']}",
                        'type': 'url_variation'
                    }]
                    
            except:
                continue
        
        return []
    
    def get_legislature(self, year):
        """Retourne la législature pour une année"""
        if 1962 <= year <= 1967:
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
        else:
            return None
    
    def analyze_pdf_content(self, pdf_info, keyword="BUMIDOM"):
        """Analyse le contenu d'un PDF"""
        
        try:
            st.write(f"📊 Analyse: {pdf_info['title'][:50]}...")
            
            # Télécharger le PDF
            response = self.session.get(pdf_info['url'], timeout=20, stream=True)
            
            if response.status_code == 200:
                content = response.content
                
                # OPTION 1: Vérifier si c'est un PDF valide
                if content.startswith(b'%PDF'):
                    
                    # Pour les PDF textuels simples
                    try:
                        # Essayer de décoder en texte
                        text = content.decode('utf-8', errors='ignore')
                        
                        # Rechercher le mot-clé
                        keyword_lower = keyword.lower()
                        text_lower = text.lower()
                        
                        if keyword_lower in text_lower:
                            # Compter les occurrences
                            occurrences = text_lower.count(keyword_lower)
                            
                            # Extraire le contexte
                            contexts = []
                            start_idx = 0
                            
                            for _ in range(min(3, occurrences)):  # 3 premiers contextes max
                                pos = text_lower.find(keyword_lower, start_idx)
                                if pos != -1:
                                    start = max(0, pos - 150)
                                    end = min(len(text), pos + len(keyword) + 150)
                                    context = text[start:end].replace('\n', ' ').strip()
                                    contexts.append(context)
                                    start_idx = pos + 1
                            
                            return {
                                **pdf_info,
                                'contains_keyword': True,
                                'occurrences': occurrences,
                                'contexts': contexts,
                                'file_type': 'pdf_text',
                                'error': None
                            }
                        else:
                            return {
                                **pdf_info,
                                'contains_keyword': False,
                                'occurrences': 0,
                                'contexts': [],
                                'file_type': 'pdf_text',
                                'error': None
                            }
                            
                    except:
                        # PDF binaire - chercher dans les bytes
                        if keyword.lower().encode() in content.lower():
                            return {
                                **pdf_info,
                                'contains_keyword': True,
                                'occurrences': 1,  # Approximation
                                'contexts': ["PDF binaire - mot-clé détecté"],
                                'file_type': 'pdf_binary',
                                'error': None
                            }
                        else:
                            return {
                                **pdf_info,
                                'contains_keyword': False,
                                'occurrences': 0,
                                'contexts': [],
                                'file_type': 'pdf_binary',
                                'error': 'PDF binaire (OCR nécessaire)'
                            }
                
                else:
                    # Pas un PDF valide
                    return {
                        **pdf_info,
                        'contains_keyword': False,
                        'occurrences': 0,
                        'contexts': [],
                        'file_type': 'not_pdf',
                        'error': 'Fichier non PDF'
                    }
                    
            else:
                return {
                    **pdf_info,
                    'contains_keyword': False,
                    'occurrences': 0,
                    'contexts': [],
                    'file_type': 'error',
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                **pdf_info,
                'contains_keyword': False,
                'occurrences': 0,
                'contexts': [],
                'file_type': 'error',
                'error': str(e)[:100]
            }
    
    def get_preview_html(self, pdf_url):
        """Génère du HTML pour prévisualiser un PDF"""
        try:
            response = self.session.get(pdf_url, timeout=15)
            if response.status_code == 200:
                b64_pdf = base64.b64encode(response.content).decode()
                return f'''
                <iframe src="data:application/pdf;base64,{b64_pdf}" 
                        width="100%" 
                        height="600"
                        style="border: 1px solid #ccc; border-radius: 5px;">
                </iframe>
                '''
        except:
            return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        keyword = st.text_input("Mot-clé:", value="BUMIDOM")
        
        st.markdown("### 📅 URLs disponibles")
        
        # URLs basées sur vos résultats
        urls_info = [
            {"id": 1, "année": "1971-1972", "type": "ordinaire1", "description": "Mention BUMIDOM confirmée"},
            {"id": 2, "année": "1968-1969", "type": "ordinaire1", "description": "Mention BUMIDOM confirmée"},
            {"id": 3, "année": "1966-1967", "type": "ordinaire1", "description": "Mention BUMIDOM confirmée"},
            {"id": 4, "année": "1982-1983", "type": "ordinaire1", "description": "Mention BUMIDOM confirmée"},
            {"id": 5, "année": "1976-1977", "type": "ordinaire2", "description": "Mention BUMIDOM confirmée"},
            {"id": 6, "année": "1970-1971", "type": "ordinaire1", "description": "Mention BUMIDOM confirmée"},
            {"id": 7, "année": "1985-1986", "type": "extraordinaire1", "description": "Mention BUMIDOM confirmée"},
            {"id": 8, "année": "1970-1971", "type": "ordinaire2", "description": "Mention BUMIDOM confirmée"},
        ]
        
        selected_ids = st.multiselect(
            "Sélectionner les URLs à scraper:",
            [f"{u['id']}. {u['année']} ({u['type']})" for u in urls_info],
            default=[f"{u['id']}. {u['année']} ({u['type']})" for u in urls_info[:4]]
        )
        
        col1, col2 = st.columns(2)
        with col1:
            auto_analyze = st.checkbox("Analyser contenu", value=True)
        with col2:
            show_preview = st.checkbox("Aperçu PDF", value=False)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            scrape_btn = st.button("🚀 Lancer le scraping", type="primary", use_container_width=True)
        with col_btn2:
            clear_btn = st.button("🧹 Réinitialiser", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **URLs format:**
        ```
        /cri/AAAA-AAAA-typeNUMERO
        ```
        Ex: /cri/1971-1972-ordinaire1
        """)
    
    # État de session
    if 'scraping_results' not in st.session_state:
        st.session_state.scraping_results = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    
    if clear_btn:
        st.session_state.scraping_results = []
        st.session_state.analysis_results = []
        st.rerun()
    
    # Scraping principal
    if scrape_btn:
        scraper = DirectURLScraper()
        
        # Récupérer les URLs directes
        all_urls = scraper.get_direct_urls_from_your_results()
        
        # Filtrer selon la sélection
        selected_urls = []
        if selected_ids:
            for url_info in all_urls:
                year_str = str(url_info['year'])
                for selected in selected_ids:
                    if year_str in selected:
                        selected_urls.append(url_info)
                        break
        else:
            selected_urls = all_urls[:4]  # Par défaut, les 4 premières
        
        st.info(f"Scraping de {len(selected_urls)} URLs directes...")
        
        all_pdfs = []
        
        for url_info in selected_urls:
            pdfs = scraper.scrape_direct_url(url_info, keyword)
            all_pdfs.extend(pdfs)
            time.sleep(0.5)  # Pause entre les requêtes
        
        st.session_state.scraping_results = all_pdfs
        
        if all_pdfs:
            st.success(f"✅ {len(all_pdfs)} documents trouvés")
            
            # Analyse automatique
            if auto_analyze and all_pdfs:
                with st.spinner("Analyse du contenu..."):
                    analyzed = []
                    
                    for pdf in all_pdfs:
                        analysis = scraper.analyze_pdf_content(pdf, keyword)
                        analyzed.append(analysis)
                    
                    st.session_state.analysis_results = analyzed
        
        else:
            st.warning("❌ Aucun document trouvé")
    
    # Affichage des résultats
    if st.session_state.scraping_results:
        st.subheader(f"📊 Résultats: {len(st.session_state.scraping_results)} documents")
        
        # Tableau récapitulatif
        df = pd.DataFrame(st.session_state.scraping_results)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Documents", len(df))
        with col2:
            st.metric("Années", df['year'].nunique())
        with col3:
            if st.session_state.analysis_results:
                with_keyword = len([r for r in st.session_state.analysis_results 
                                  if r.get('contains_keyword')])
                st.metric("Contient BUMIDOM", with_keyword)
        
        # Afficher les documents avec analyse
        if st.session_state.analysis_results:
            st.subheader("🔍 Documents analysés")
            
            # Séparer par présence du mot-clé
            with_keyword = [r for r in st.session_state.analysis_results 
                          if r.get('contains_keyword')]
            without_keyword = [r for r in st.session_state.analysis_results 
                             if not r.get('contains_keyword')]
            
            if with_keyword:
                st.success(f"🎯 {len(with_keyword)} documents contiennent '{keyword}'")
                
                for doc in with_keyword:
                    with st.expander(f"📅 {doc['year']} - {doc['title'][:80]}... ({doc['occurrences']} occ.)"):
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            st.markdown(f"**URL:** `{doc['url']}`")
                            st.markdown(f"**Type:** {doc.get('type', 'N/A')}")
                            st.markdown(f"**Source:** {doc.get('description', 'N/A')}")
                            st.markdown(f"**Occurrences:** {doc['occurrences']}")
                            
                            if doc.get('contexts'):
                                st.markdown("**Contextes trouvés:**")
                                for i, context in enumerate(doc['contexts'][:2]):
                                    highlighted = re.sub(
                                        r'(' + re.escape(keyword) + ')',
                                        r'**\1**',
                                        context,
                                        flags=re.IGNORECASE
                                    )
                                    st.markdown(f"{i+1}. *\"{highlighted}\"*")
                        
                        with col_b:
                            st.markdown(f"[🔗 Ouvrir]({doc['url']})", unsafe_allow_html=True)
                            
                            if show_preview:
                                if st.button("👁️ Aperçu", key=f"prev_{doc['url'][-20:]}"):
                                    preview = scraper.get_preview_html(doc['url'])
                                    if preview:
                                        st.markdown(preview, unsafe_allow_html=True)
                                    else:
                                        st.warning("Aperçu non disponible")
            
            # Documents sans mot-clé
            if without_keyword and len(without_keyword) < 10:  # Limiter l'affichage
                with st.expander(f"📄 {len(without_keyword)} documents sans '{keyword}'"):
                    for doc in without_keyword[:5]:
                        st.markdown(f"- {doc['title'][:80]}... ({doc.get('error', 'N/A')})")
        
        # Tous les documents trouvés
        st.subheader("📚 Tous les documents trouvés")
        
        for idx, doc in enumerate(st.session_state.scraping_results):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"**{doc['title']}**")
                st.caption(f"Année: {doc['year']} | Type: {doc.get('type', 'N/A')}")
            
            with col2:
                st.markdown(f"[📥 Télécharger]({doc['url']})", unsafe_allow_html=True)
        
        # Export
        st.subheader("💾 Export des données")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # Données brutes
            csv_raw = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📊 Données brutes (CSV)",
                data=csv_raw,
                file_name=f"bumidom_raw_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col_exp2:
            # Analyses
            if st.session_state.analysis_results:
                df_analysis = pd.DataFrame(st.session_state.analysis_results)
                csv_analysis = df_analysis.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="🔬 Analyses (CSV)",
                    data=csv_analysis,
                    file_name=f"bumidom_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    else:
        # Écran d'accueil avec manuel de scraping
        st.markdown("""
        ## 🎯 Manuel de Scraping Direct
        
        ### Problème identifié:
        Les URLs génériques échouent (403/404), mais vos résultats montrent des URLs **spécifiques** qui fonctionnent.
        
        ### URLs confirmées fonctionnelles:
        """)
        
        # Table des URLs
        urls_table = pd.DataFrame([
            {"URL": "/cri/1971-1972-ordinaire1", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1968-1969-ordinaire1", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1966-1967-ordinaire1", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1982-1983-ordinaire1", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1976-1977-ordinaire2", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1970-1971-ordinaire1", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1985-1986-extraordinaire1", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
            {"URL": "/cri/1970-1971-ordinaire2", "Statut": "✅ Confirmé", "Mention BUMIDOM": "Oui"},
        ])
        
        st.dataframe(urls_table, use_container_width=True)
        
        st.markdown("""
        ### 🚀 Comment utiliser:
        
        1. **Sélectionnez les URLs** dans la sidebar (4 pré-sélectionnées)
        2. **Cliquez sur "🚀 Lancer le scraping"**
        3. **Explorez** les documents trouvés
        4. **Analysez** le contenu pour BUMIDOM
        5. **Exportez** les résultats
        
        ### 🔧 Ce que fait ce scraper:
        
        - Accède aux **URLs exactes** que vous avez trouvées
        - Cherche des **PDF directs** sur chaque page
        - Vérifie si la page **est elle-même un PDF**
        - **Analyse le contenu** pour trouver BUMIDOM
        - **Extrait le contexte** des mentions
        - **Prévient les erreurs** 403/404 avec des variantes
        
        ### ⏱️ Temps estimé: 30-60 secondes
        """)

# Footer avec installation
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Installation")
st.sidebar.code("pip install streamlit requests beautifulsoup4 pandas")

if __name__ == "__main__":
    main()
