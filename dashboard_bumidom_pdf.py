import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin, quote
import json
import base64
from io import BytesIO
import fitz  # PyMuPDF

# Configuration
st.set_page_config(
    page_title="Scraper PDF BUMIDOM - Archives AN", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Scraper des 100 PDF BUMIDOM - Archives AN")
st.markdown("Scraping des résultats de recherche interne du site archives.assemblee-nationale.fr")

class PDFBUMIDOMScraper:
    def __init__(self):
        self.base_url = "https://archives.assemblee-nationale.fr"
        self.search_url = "https://archives.assemblee-nationale.fr/recherche"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
    
    def search_pdfs(self, keyword="Bumidom", max_pages=10):
        """Effectue la recherche et extrait les liens PDF"""
        
        st.info(f"Recherche de '{keyword}' sur {max_pages} pages...")
        
        all_pdf_links = []
        
        for page_num in range(1, max_pages + 1):
            try:
                # Construire l'URL de recherche avec pagination
                params = {
                    'query': keyword,
                    'page': page_num,
                    'type': 'pdf'  # Filtrer uniquement les PDF
                }
                
                st.write(f"📄 Page {page_num}...")
                
                response = self.session.get(self.search_url, params=params, timeout=15)
                
                if response.status_code != 200:
                    st.warning(f"Erreur page {page_num}: HTTP {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extraire tous les liens PDF de la page
                pdf_elements = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for element in pdf_elements[:20]:  # Prendre plus pour être sûr
                    href = element.get('href', '')
                    if href:
                        # Nettoyer et compléter l'URL
                        if href.startswith('/'):
                            full_url = urljoin(self.base_url, href)
                        elif not href.startswith('http'):
                            full_url = urljoin(self.search_url, href)
                        else:
                            full_url = href
                        
                        # Extraire le titre
                        title = element.get_text(strip=True)
                        if not title or len(title) < 5:
                            # Essayer de trouver un titre ailleurs
                            parent = element.find_parent(['div', 'li', 'td'])
                            if parent:
                                title = parent.get_text(strip=True)[:200]
                        
                        if not title:
                            title = href.split('/')[-1]
                        
                        pdf_info = {
                            'url': full_url,
                            'title': title[:250],
                            'page': page_num,
                            'position': len([p for p in all_pdf_links if p['page'] == page_num]) + 1
                        }
                        
                        # Vérifier si ce PDF n'est pas déjà dans la liste
                        if not any(p['url'] == full_url for p in all_pdf_links):
                            all_pdf_links.append(pdf_info)
                            st.write(f"  → PDF {pdf_info['position']}: {title[:80]}...")
                
                # Vérifier s'il y a une pagination
                next_link = soup.find('a', string=re.compile(r'suivant|next', re.I))
                if not next_link and page_num < max_pages:
                    # Essayer une autre méthode pour la pagination
                    next_links = soup.find_all('a', href=re.compile(r'page=' + str(page_num + 1)))
                    if not next_links:
                        st.warning(f"Pas de lien vers la page {page_num + 1}, arrêt.")
                        break
                
                time.sleep(1)  # Pause pour respecter le serveur
                
            except Exception as e:
                st.error(f"Erreur page {page_num}: {str(e)[:100]}")
                continue
        
        return all_pdf_links[:100]  # Limiter à 100 maximum
    
    def scrape_pdf_content(self, pdf_info, keyword="Bumidom"):
        """Télécharge et analyse le contenu d'un PDF"""
        try:
            st.write(f"📥 Analyse: {pdf_info['title'][:50]}...")
            
            response = self.session.get(pdf_info['url'], timeout=30, stream=True)
            
            if response.status_code != 200:
                return {
                    **pdf_info,
                    'error': f"HTTP {response.status_code}",
                    'content': '',
                    'keyword_count': 0,
                    'size_kb': 0,
                    'page_count': 0
                }
            
            # Taille du fichier
            content = response.content
            size_kb = len(content) / 1024
            
            # Analyser le PDF
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf_doc:
                    page_count = pdf_doc.page_count
                    
                    # Extraire le texte
                    full_text = ""
                    for page_num in range(min(20, page_count)):  # Limiter aux 20 premières pages
                        page = pdf_doc[page_num]
                        full_text += page.get_text() + "\n"
                    
                    # Compter les occurrences du mot-clé
                    keyword_pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                    keyword_count = len(keyword_pattern.findall(full_text))
                    
                    # Extraire le contexte des premières occurrences
                    contexts = []
                    if keyword_count > 0:
                        matches = list(keyword_pattern.finditer(full_text))
                        for match in matches[:3]:  # 3 premiers contextes
                            start = max(0, match.start() - 150)
                            end = min(len(full_text), match.end() + 150)
                            context = full_text[start:end].replace('\n', ' ').strip()
                            contexts.append(context)
                    
                    return {
                        **pdf_info,
                        'content': full_text[:5000],  # Stocker les 5000 premiers caractères
                        'keyword_count': keyword_count,
                        'size_kb': round(size_kb, 2),
                        'page_count': page_count,
                        'contexts': contexts[:3],  # 3 premiers contextes
                        'error': None
                    }
                    
            except Exception as pdf_error:
                return {
                    **pdf_info,
                    'error': f"Erreur PDF: {str(pdf_error)[:100]}",
                    'content': '',
                    'keyword_count': 0,
                    'size_kb': round(size_kb, 2),
                    'page_count': 0,
                    'contexts': []
                }
                
        except Exception as e:
            return {
                **pdf_info,
                'error': f"Téléchargement: {str(e)[:100]}",
                'content': '',
                'keyword_count': 0,
                'size_kb': 0,
                'page_count': 0,
                'contexts': []
            }
    
    def batch_scrape_pdfs(self, pdf_links, keyword="Bumidom", max_pdfs=100):
        """Scrape un lot de PDF"""
        results = []
        
        st.info(f"Analyse de {len(pdf_links[:max_pdfs])} PDF...")
        
        progress_bar = st.progress(0)
        
        for idx, pdf_info in enumerate(pdf_links[:max_pdfs]):
            progress = (idx + 1) / min(len(pdf_links), max_pdfs)
            progress_bar.progress(progress)
            
            # Analyser le PDF
            pdf_data = self.scrape_pdf_content(pdf_info, keyword)
            results.append(pdf_data)
            
            # Afficher le résultat
            if pdf_data['keyword_count'] > 0:
                st.success(f"  ✓ {pdf_data['keyword_count']} occurrence(s) dans {pdf_data['title'][:60]}...")
            elif pdf_data.get('error'):
                st.warning(f"  ⚠️ Erreur: {pdf_data['error']}")
            else:
                st.write(f"  ○ Aucune occurrence trouvée")
            
            time.sleep(0.5)  # Pause entre les téléchargements
        
        progress_bar.empty()
        return results

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Paramètres")
        
        keyword = st.text_input("Mot-clé de recherche:", value="Bumidom")
        
        col1, col2 = st.columns(2)
        with col1:
            max_pages = st.number_input("Pages à scraper", 1, 20, 10)
        with col2:
            max_pdfs = st.number_input("PDF max à analyser", 10, 200, 100)
        
        st.markdown("---")
        
        # Boutons d'action
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            search_only = st.button("🔍 Rechercher PDF", use_container_width=True)
        
        with col_btn2:
            full_scrape = st.button("🚀 Scraper complet", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Fonctionnalités:**
        1. Recherche les PDF via le moteur interne
        2. Analyse le contenu des PDF
        3. Compte les occurrences de BUMIDOM
        4. Extrait des contextes
        """)
    
    # Initialisation
    scraper = PDFBUMIDOMScraper()
    
    # État de session
    if 'pdf_links' not in st.session_state:
        st.session_state.pdf_links = []
    if 'pdf_data' not in st.session_state:
        st.session_state.pdf_data = []
    
    # Actions
    if search_only:
        with st.spinner("Recherche des PDF en cours..."):
            pdf_links = scraper.search_pdfs(keyword, max_pages)
            st.session_state.pdf_links = pdf_links
            
            if pdf_links:
                st.success(f"✅ {len(pdf_links)} PDF trouvés")
                
                # Afficher la liste
                df_links = pd.DataFrame(pdf_links)
                st.dataframe(df_links[['title', 'page', 'position', 'url']], use_container_width=True)
                
                # Statistiques
                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    st.metric("PDF trouvés", len(pdf_links))
                with col_stat2:
                    pages = df_links['page'].nunique()
                    st.metric("Pages analysées", pages)
            else:
                st.warning("Aucun PDF trouvé. Essayez avec une orthographe différente.")
    
    elif full_scrape:
        if not st.session_state.pdf_links:
            # D'abord chercher les PDF
            with st.spinner("Recherche initiale des PDF..."):
                pdf_links = scraper.search_pdfs(keyword, max_pages)
                st.session_state.pdf_links = pdf_links
        
        if st.session_state.pdf_links:
            with st.spinner("Scraping et analyse des PDF en cours..."):
                pdf_data = scraper.batch_scrape_pdfs(
                    st.session_state.pdf_links, 
                    keyword, 
                    max_pdfs
                )
                st.session_state.pdf_data = pdf_data
            
            # Afficher les résultats
            if pdf_data:
                df = pd.DataFrame(pdf_data)
                
                # Filtrer les PDF avec des occurrences
                pdfs_with_keyword = [p for p in pdf_data if p['keyword_count'] > 0]
                
                if pdfs_with_keyword:
                    st.success(f"✅ {len(pdfs_with_keyword)} PDF contiennent '{keyword}'")
                    
                    # Statistiques
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("PDF analysés", len(pdf_data))
                    with col_stat2:
                        total_occurrences = sum(p['keyword_count'] for p in pdf_data)
                        st.metric("Occurrences totales", total_occurrences)
                    with col_stat3:
                        avg_pages = sum(p['page_count'] for p in pdf_data) / len(pdf_data)
                        st.metric("Pages moyennes", f"{avg_pages:.1f}")
                    
                    # Table des résultats
                    st.subheader("📋 PDF avec occurrences de BUMIDOM")
                    
                    for pdf in pdfs_with_keyword:
                        with st.expander(f"📄 {pdf['title'][:80]}... ({pdf['keyword_count']} occ.)"):
                            col_pdf1, col_pdf2 = st.columns([3, 1])
                            
                            with col_pdf1:
                                st.markdown(f"**URL:** [{pdf['url'][:100]}...]({pdf['url']})")
                                st.markdown(f"**Pages:** {pdf['page_count']} | **Taille:** {pdf['size_kb']} KB")
                                
                                if pdf.get('contexts'):
                                    st.markdown("**Contextes:**")
                                    for i, context in enumerate(pdf['contexts'][:2]):
                                        highlighted = re.sub(
                                            r'\b' + re.escape(keyword) + r'\b',
                                            lambda m: f"**{m.group()}**",
                                            context,
                                            flags=re.IGNORECASE
                                        )
                                        st.markdown(f"{i+1}. *\"{highlighted}\"*")
                            
                            with col_pdf2:
                                # Boutons d'action
                                if st.button("👁️ Prévisualiser", key=f"preview_{pdf['url'][-30:]}"):
                                    try:
                                        # Encoder le PDF en base64 pour l'affichage
                                        response = requests.get(pdf['url'])
                                        b64_pdf = base64.b64encode(response.content).decode()
                                        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>'
                                        st.markdown(pdf_display, unsafe_allow_html=True)
                                    except:
                                        st.warning("Prévisualisation non disponible")
                                
                                if st.button("📥 Télécharger", key=f"dl_{pdf['url'][-30:]}"):
                                    st.download_button(
                                        label="Cliquer pour télécharger",
                                        data=requests.get(pdf['url']).content,
                                        file_name=pdf['url'].split('/')[-1],
                                        mime="application/pdf"
                                    )
                    
                    # Export des données
                    st.subheader("💾 Export des résultats")
                    
                    col_exp1, col_exp2, col_exp3 = st.columns(3)
                    
                    with col_exp1:
                        # CSV des métadonnées
                        csv_data = pd.DataFrame(pdf_data).to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📊 CSV des métadonnées",
                            data=csv_data,
                            file_name=f"bumidom_metadata_{time.strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    
                    with col_exp2:
                        # JSON complet
                        json_data = json.dumps(pdf_data, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="📈 JSON complet",
                            data=json_data,
                            file_name=f"bumidom_data_{time.strftime('%Y%m%d')}.json",
                            mime="application/json"
                        )
                    
                    with col_exp3:
                        # PDF avec occurrences seulement
                        pdfs_with_occ = [p for p in pdf_data if p['keyword_count'] > 0]
                        if pdfs_with_occ:
                            summary_df = pd.DataFrame(pdfs_with_occ)[['title', 'keyword_count', 'url', 'page_count']]
                            summary_csv = summary_df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="🎯 PDF avec occurrences",
                                data=summary_csv,
                                file_name=f"bumidom_occurrences_{time.strftime('%Y%m%d')}.csv",
                                mime="text/csv"
                            )
                    
                    # Analyse statistique
                    st.subheader("📈 Analyse statistique")
                    
                    if pdfs_with_keyword:
                        col_ana1, col_ana2 = st.columns(2)
                        
                        with col_ana1:
                            # Distribution des occurrences
                            occurrence_counts = [p['keyword_count'] for p in pdfs_with_keyword]
                            occurrence_df = pd.DataFrame({
                                'PDF': [p['title'][:30] + '...' for p in pdfs_with_keyword],
                                'Occurrences': occurrence_counts
                            })
                            st.bar_chart(occurrence_df.set_index('PDF')['Occurrences'])
                            st.caption("Occurrences par PDF")
                        
                        with col_ana2:
                            # Taille vs occurrences
                            size_occ_df = pd.DataFrame({
                                'Taille (KB)': [p['size_kb'] for p in pdfs_with_keyword],
                                'Occurrences': [p['keyword_count'] for p in pdfs_with_keyword],
                                'Titre': [p['title'][:20] for p in pdfs_with_keyword]
                            })
                            st.scatter_chart(size_occ_df, x='Taille (KB)', y='Occurrences')
                            st.caption("Taille vs Occurrences")
                
                else:
                    st.warning(f"⚠️ Aucun des {len(pdf_data)} PDF analysés ne contient '{keyword}'")
                    
                    # Conseils
                    st.info("""
                    **Conseils pour améliorer la recherche:**
                    1. Essayez avec **"BUMIDOM"** (majuscules)
                    2. Cherchez **"Bureau des migrations"**
                    3. Essayez **"migration outre-mer"**
                    4. Cherchez dans les **rapports parlementaires**
                    """)
        else:
            st.warning("Veuillez d'abord rechercher des PDF")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 📋 Guide d'utilisation
        
        Ce scraper utilise le **moteur de recherche interne** de `archives.assemblee-nationale.fr`.
        
        ### Étapes :
        1. **Cliquez sur "🔍 Rechercher PDF"** pour trouver les PDF
        2. **Puis "🚀 Scraper complet"** pour analyser le contenu
        3. **Exportez** les résultats en CSV/JSON
        
        ### Ce que fait le scraper :
        - Recherche "Bumidom" sur le moteur interne
        - Extrait les 10 premières pages de résultats
        - Télécharge et analyse les PDF
        - Compte les occurrences du mot-clé
        - Extrait des contextes
        - Permet la prévisualisation
        
        ### Note importante :
        Le scraping peut être lent (100 PDF × analyse). 
        Prévoyez 5-10 minutes pour une analyse complète.
        """)
        
        # Aperçu de la structure de recherche
        with st.expander("🔍 Structure de la recherche"):
            st.markdown("""
            **URL de recherche exemple:**
            ```
            https://archives.assemblee-nationale.fr/recherche
            ?query=Bumidom
            &page=1
            &type=pdf
            ```
            
            **Pages suivantes:**
            ```
            &page=2
            &page=3
            ...
            &page=10
            ```
            """)

if __name__ == "__main__":
    main()
