import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin, quote, urlparse
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer': 'https://archives.assemblee-nationale.fr/'
        })
    
    def search_pdfs_google_cse(self, keyword="Bumidom", max_pages=10):
        """Utilise le moteur Google Custom Search intégré au site"""
        
        st.info(f"Recherche de '{keyword}' via Google CSE...")
        
        all_pdf_links = []
        
        # Le site utilise Google Custom Search Engine
        for page_num in range(0, max_pages):
            try:
                # Construction de l'URL Google CSE
                start_index = page_num * 10
                search_url = f"https://www.google.com/cse?cx=014917347718038151697:kltwr00yvbk&q={quote(keyword)}&start={start_index}"
                
                st.write(f"📄 Page {page_num + 1} (résultats {start_index + 1}-{start_index + 10})...")
                
                # Ajouter des headers spécifiques pour Google
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                
                response = requests.get(search_url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    st.warning(f"Erreur page {page_num + 1}: HTTP {response.status_code}")
                    
                    # Essayer une méthode alternative
                    return self.search_pdfs_alternative(keyword, max_pages)
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Rechercher tous les liens dans les résultats
                # Google CSE a généralement des divs avec class 'g' pour les résultats
                results = soup.find_all('div', class_='g')
                
                if not results:
                    # Essayer une autre structure
                    results = soup.find_all('div', class_=re.compile(r'result|item', re.I))
                
                for result in results:
                    # Chercher les liens dans chaque résultat
                    links = result.find_all('a', href=True)
                    
                    for link in links:
                        href = link['href']
                        
                        # Vérifier si c'est un lien PDF (soit finit par .pdf, soit contient pdf dans l'URL)
                        if ('.pdf' in href.lower() or 'pdf' in href.lower()) and 'archives.assemblee-nationale.fr' in href:
                            
                            # Nettoyer l'URL (enlever les paramètres Google)
                            if 'url=' in href:
                                # URL encodée dans le paramètre Google
                                match = re.search(r'url=([^&]+)', href)
                                if match:
                                    href = match.group(1)
                                    href = requests.utils.unquote(href)
                            
                            # Vérifier que c'est bien une URL de l'Assemblée Nationale
                            if 'assemblee-nationale.fr' in href:
                                # Extraire le titre
                                title_elem = link.find(['h3', 'div', 'span'])
                                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
                                
                                if not title or len(title) < 3:
                                    # Prendre le texte du lien
                                    title = link.get_text(strip=True)
                                    if not title:
                                        # Utiliser l'URL comme titre
                                        title = href.split('/')[-1]
                                
                                pdf_info = {
                                    'url': href,
                                    'title': title[:250],
                                    'page': page_num + 1,
                                    'position': len([p for p in all_pdf_links if p['page'] == page_num + 1]) + 1,
                                    'source': 'Google CSE'
                                }
                                
                                # Vérifier si ce PDF n'est pas déjà dans la liste
                                if not any(p['url'] == href for p in all_pdf_links):
                                    all_pdf_links.append(pdf_info)
                                    st.write(f"  → PDF trouvé: {title[:80]}...")
                
                # Vérifier s'il y a plus de pages
                next_link = soup.find('a', {'id': 'pnnext'})
                if not next_link and page_num < max_pages - 1:
                    # Chercher d'autres indicateurs de pagination
                    next_links = soup.find_all('a', string=re.compile(r'suivant|next|>\s*$', re.I))
                    if not next_links:
                        st.info(f"Dernière page atteinte: {page_num + 1}")
                        break
                
                time.sleep(2)  # Pause plus longue pour Google
                
            except Exception as e:
                st.error(f"Erreur page {page_num + 1}: {str(e)[:100]}")
                continue
        
        return all_pdf_links[:100]
    
    def search_pdfs_alternative(self, keyword="Bumidom", max_pages=10):
        """Méthode alternative de recherche"""
        
        st.info("Utilisation de la méthode alternative de recherche...")
        
        all_pdf_links = []
        
        # URLs spécifiques où chercher des PDF
        search_patterns = [
            f"https://archives.assemblee-nationale.fr/recherche?query={quote(keyword)}",
            f"https://www.assemblee-nationale.fr/recherche/query.asp?quoi={quote(keyword)}&type=pdf",
        ]
        
        for search_url in search_patterns:
            try:
                st.write(f"Essai avec: {search_url}")
                
                response = self.session.get(search_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Chercher tous les liens PDF
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for link in pdf_links[:50]:  # Limiter aux 50 premiers
                    href = link.get('href', '')
                    
                    if href:
                        # Compléter l'URL si nécessaire
                        if not href.startswith('http'):
                            href = urljoin(search_url, href)
                        
                        # Vérifier que c'est bien une URL AN
                        if 'assemblee-nationale.fr' in href:
                            title = link.get_text(strip=True)
                            if not title:
                                title = href.split('/')[-1]
                            
                            pdf_info = {
                                'url': href,
                                'title': title[:250],
                                'page': 1,
                                'position': len(all_pdf_links) + 1,
                                'source': 'Recherche alternative'
                            }
                            
                            if not any(p['url'] == href for p in all_pdf_links):
                                all_pdf_links.append(pdf_info)
                                st.write(f"  → PDF: {title[:80]}...")
                
                time.sleep(1)
                
            except Exception as e:
                st.warning(f"Erreur avec méthode alternative: {str(e)[:100]}")
        
        return all_pdf_links[:100]
    
    def search_pdfs_simple(self, keyword="Bumidom"):
        """Méthode simple pour tester rapidement"""
        
        st.info(f"Recherche simple de '{keyword}'...")
        
        # Liste d'URLs de PDF potentiels basée sur la structure connue
        pdf_urls = []
        
        # Générer des URLs basées sur la structure des archives
        for legislature in [4, 5, 6, 7, 8]:  # Législatures 4 à 8
            for year in range(1963, 1983):
                # Différents types de documents
                doc_types = ['cri', 'qst', 'rapports']
                
                for doc_type in doc_types:
                    # Essayer différents patterns d'URL
                    patterns = [
                        f"https://archives.assemblee-nationale.fr/{legislature}/{doc_type}/",
                        f"https://archives.assemblee-nationale.fr/{legislature}/{doc_type}/{year}/",
                        f"https://archives.assemblee-nationale.fr/{legislature}/{doc_type}/{year}-",
                    ]
                    
                    for base_url in patterns:
                        try:
                            response = self.session.get(base_url, timeout=10)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.content, 'html.parser')
                                
                                # Chercher des liens contenant le mot-clé
                                for link in soup.find_all('a', href=True, string=re.compile(keyword, re.I)):
                                    href = link['href']
                                    if '.pdf' in href.lower():
                                        full_url = urljoin(base_url, href)
                                        pdf_urls.append({
                                            'url': full_url,
                                            'title': link.get_text(strip=True),
                                            'page': 1,
                                            'position': len(pdf_urls) + 1,
                                            'source': f'Législature {legislature}'
                                        })
                                        st.write(f"  → Trouvé: {link.get_text(strip=True)[:80]}...")
                        
                        except:
                            continue
        
        return pdf_urls[:50]
    
    def scrape_pdf_content(self, pdf_info, keyword="Bumidom"):
        """Télécharge et analyse le contenu d'un PDF"""
        try:
            st.write(f"📥 Analyse: {pdf_info['title'][:50]}...")
            
            # Headers pour le téléchargement
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://archives.assemblee-nationale.fr/',
                'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            response = requests.get(pdf_info['url'], headers=headers, timeout=30, stream=True)
            
            if response.status_code != 200:
                return {
                    **pdf_info,
                    'error': f"HTTP {response.status_code}",
                    'content': '',
                    'keyword_count': 0,
                    'size_kb': 0,
                    'page_count': 0,
                    'analyzed': False
                }
            
            # Taille du fichier
            content = response.content
            size_kb = len(content) / 1024
            
            # Vérifier si c'est bien un PDF
            if not content.startswith(b'%PDF'):
                return {
                    **pdf_info,
                    'error': "Fichier non PDF",
                    'content': '',
                    'keyword_count': 0,
                    'size_kb': round(size_kb, 2),
                    'page_count': 0,
                    'analyzed': False
                }
            
            # Analyser le PDF
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf_doc:
                    page_count = pdf_doc.page_count
                    
                    # Extraire le texte (limité pour performance)
                    full_text = ""
                    max_pages = min(50, page_count)  # Analyser max 50 pages
                    
                    for page_num in range(max_pages):
                        page = pdf_doc[page_num]
                        text = page.get_text()
                        full_text += text + "\n"
                    
                    # Rechercher le mot-clé
                    keyword_lower = keyword.lower()
                    text_lower = full_text.lower()
                    
                    # Compter les occurrences
                    keyword_count = text_lower.count(keyword_lower)
                    
                    # Extraire le contexte des premières occurrences
                    contexts = []
                    if keyword_count > 0:
                        # Trouver les positions
                        start_pos = 0
                        found_count = 0
                        
                        while found_count < 3:  # 3 premiers contextes max
                            pos = text_lower.find(keyword_lower, start_pos)
                            if pos == -1:
                                break
                            
                            start = max(0, pos - 150)
                            end = min(len(full_text), pos + len(keyword) + 150)
                            context = full_text[start:end].replace('\n', ' ').strip()
                            contexts.append(context)
                            
                            start_pos = pos + 1
                            found_count += 1
                    
                    return {
                        **pdf_info,
                        'content': full_text[:3000],  # Stocker 3000 caractères max
                        'keyword_count': keyword_count,
                        'size_kb': round(size_kb, 2),
                        'page_count': page_count,
                        'contexts': contexts,
                        'analyzed': True,
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
                    'analyzed': False,
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
                'analyzed': False,
                'contexts': []
            }
    
    def batch_scrape_pdfs(self, pdf_links, keyword="Bumidom", max_pdfs=50):
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
            if pdf_data.get('analyzed') and pdf_data['keyword_count'] > 0:
                st.success(f"  ✓ {pdf_data['keyword_count']} occurrence(s) dans {pdf_data['title'][:60]}...")
            elif pdf_data.get('error'):
                st.warning(f"  ⚠️ {pdf_data['error']}")
            else:
                st.write(f"  ○ Aucune occurrence")
            
            time.sleep(0.3)  # Pause courte
        
        progress_bar.empty()
        return results

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Paramètres")
        
        keyword = st.text_input("Mot-clé de recherche:", value="Bumidom")
        
        col1, col2 = st.columns(2)
        with col1:
            search_method = st.selectbox(
                "Méthode de recherche",
                ["Google CSE (recommandé)", "Alternative", "Simple test"]
            )
        with col2:
            max_pdfs = st.number_input("PDF max à analyser", 10, 200, 50)
        
        st.markdown("---")
        
        # Boutons d'action
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            search_only = st.button("🔍 Rechercher PDF", use_container_width=True)
        
        with col_btn2:
            full_scrape = st.button("🚀 Scraper complet", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Méthodes disponibles:**
        1. **Google CSE** : Utilise le moteur intégré
        2. **Alternative** : Cherche dans différentes URLs
        3. **Simple test** : Pour tester rapidement
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
            if search_method == "Google CSE (recommandé)":
                pdf_links = scraper.search_pdfs_google_cse(keyword, 10)
            elif search_method == "Alternative":
                pdf_links = scraper.search_pdfs_alternative(keyword, 10)
            else:
                pdf_links = scraper.search_pdfs_simple(keyword)
            
            st.session_state.pdf_links = pdf_links
            
            if pdf_links:
                st.success(f"✅ {len(pdf_links)} PDF trouvés")
                
                # Afficher la liste
                df_links = pd.DataFrame(pdf_links)
                st.dataframe(df_links[['title', 'source', 'url']], use_container_width=True)
                
                # Statistiques
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("PDF trouvés", len(pdf_links))
                with col_stat2:
                    sources = df_links['source'].nunique()
                    st.metric("Sources", sources)
                with col_stat3:
                    st.metric("URLs uniques", df_links['url'].nunique())
            else:
                st.warning("Aucun PDF trouvé.")
                
                # Afficher des conseils
                with st.expander("💡 Conseils pour la recherche"):
                    st.markdown("""
                    1. **Essayez en majuscules** : BUMIDOM
                    2. **Termes alternatifs** :
                       - Bureau migrations DOM
                       - Migration outre-mer
                       - Départements d'outre-mer
                    3. **Cherchez directement** sur :
                       - [Archives AN](https://archives.assemblee-nationale.fr)
                       - [Recherche AN](https://www.assemblee-nationale.fr/recherche)
                    """)
    
    elif full_scrape:
        if not st.session_state.pdf_links:
            st.warning("Veuillez d'abord rechercher des PDF")
        else:
            with st.spinner(f"Scraping de {len(st.session_state.pdf_links[:max_pdfs])} PDF..."):
                pdf_data = scraper.batch_scrape_pdfs(
                    st.session_state.pdf_links, 
                    keyword, 
                    max_pdfs
                )
                st.session_state.pdf_data = pdf_data
            
            # Afficher les résultats
            if pdf_data:
                # Filtrer les PDF analysés avec succès
                analyzed_pdfs = [p for p in pdf_data if p.get('analyzed')]
                pdfs_with_keyword = [p for p in analyzed_pdfs if p['keyword_count'] > 0]
                
                st.success(f"""
                ✅ Analyse terminée:
                - {len(analyzed_pdfs)}/{len(pdf_data)} PDF analysés
                - {len(pdfs_with_keyword)} contiennent '{keyword}'
                """)
                
                if pdfs_with_keyword:
                    # Afficher les résultats détaillés
                    display_results(pdfs_with_keyword, keyword)
                else:
                    st.warning(f"Aucun PDF ne contient '{keyword}'")
                    
                    # Afficher quand même quelques PDF analysés
                    if analyzed_pdfs:
                        st.subheader("📋 PDF analysés (sans occurrence)")
                        for pdf in analyzed_pdfs[:5]:
                            st.write(f"- {pdf['title'][:80]}... ({pdf['page_count']} pages, {pdf['size_kb']} KB)")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 📋 Guide d'utilisation
        
        Ce scraper recherche **BUMIDOM** dans les archives de l'Assemblée Nationale.
        
        ### Étapes recommandées :
        1. **Cliquez sur "🔍 Rechercher PDF"** avec "Google CSE"
        2. **Puis "🚀 Scraper complet"** pour analyser le contenu
        3. **Explorez** les PDF avec occurrences
        
        ### Méthodes disponibles :
        
        **1. Google CSE (recommandé)**
        - Utilise le moteur de recherche intégré au site
        - Trouve les PDF via Google Custom Search
        - Meilleurs résultats
        
        **2. Méthode alternative**
        - Cherche dans différentes URLs connues
        - Bonne alternative si Google CSE échoue
        
        **3. Simple test**
        - Test rapide avec peu de PDF
        - Pour vérifier que le scraper fonctionne
        
        ### Note :
        - L'analyse de PDF peut prendre quelques minutes
        - Certains PDF peuvent être scannés (OCR nécessaire)
        - Le site peut limiter les accès rapides
        """)

def display_results(pdfs_with_keyword, keyword):
    """Affiche les résultats détaillés"""
    
    st.subheader(f"📊 {len(pdfs_with_keyword)} PDF avec occurrences de '{keyword}'")
    
    # Statistiques
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        total_occurrences = sum(p['keyword_count'] for p in pdfs_with_keyword)
        st.metric("Occurrences totales", total_occurrences)
    with col_stat2:
        avg_occurrences = total_occurrences / len(pdfs_with_keyword)
        st.metric("Moyenne par PDF", f"{avg_occurrences:.1f}")
    with col_stat3:
        total_pages = sum(p['page_count'] for p in pdfs_with_keyword)
        st.metric("Pages totales", total_pages)
    with col_stat4:
        total_size = sum(p['size_kb'] for p in pdfs_with_keyword)
        st.metric("Taille totale", f"{total_size/1024:.1f} MB")
    
    # Table des résultats
    st.subheader("📋 Liste détaillée")
    
    for idx, pdf in enumerate(pdfs_with_keyword):
        with st.expander(f"📄 {pdf['title'][:100]}... ({pdf['keyword_count']} occ.)"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**URL:** `{pdf['url']}`")
                st.markdown(f"**Source:** {pdf.get('source', 'N/A')}")
                st.markdown(f"**Pages:** {pdf['page_count']} | **Taille:** {pdf['size_kb']} KB")
                
                if pdf.get('contexts'):
                    st.markdown("**Contextes trouvés:**")
                    for i, context in enumerate(pdf['contexts'][:2]):
                        # Mettre en évidence le mot-clé
                        highlighted = re.sub(
                            r'(' + re.escape(keyword) + ')',
                            r'**\1**',
                            context,
                            flags=re.IGNORECASE
                        )
                        st.markdown(f"{i+1}. *\"{highlighted}\"*")
            
            with col2:
                # Boutons d'action
                st.markdown(f"[🌐 Ouvrir PDF]({pdf['url']})", unsafe_allow_html=True)
                
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
                        st.warning("Téléchargement échoué")
    
    # Export des données
    st.subheader("💾 Export des résultats")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        # CSV des métadonnées
        df_summary = pd.DataFrame(pdfs_with_keyword)[['title', 'keyword_count', 'url', 'page_count', 'size_kb', 'source']]
        csv_data = df_summary.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 CSV des résultats",
            data=csv_data,
            file_name=f"bumidom_results_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col_exp2:
        # JSON complet
        json_data = json.dumps(pdfs_with_keyword, ensure_ascii=False, indent=2)
        st.download_button(
            label="📈 JSON complet",
            data=json_data,
            file_name=f"bumidom_full_{time.strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    # Graphiques
    st.subheader("📈 Visualisations")
    
    if len(pdfs_with_keyword) > 1:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Graphique des occurrences
            df_chart = pd.DataFrame({
                'PDF': [p['title'][:30] + '...' for p in pdfs_with_keyword],
                'Occurrences': [p['keyword_count'] for p in pdfs_with_keyword]
            })
            st.bar_chart(df_chart.set_index('PDF'))
            st.caption("Occurrences par PDF")
        
        with col_chart2:
            # Relation taille/occurrences
            df_scatter = pd.DataFrame({
                'Taille (KB)': [p['size_kb'] for p in pdfs_with_keyword],
                'Occurrences': [p['keyword_count'] for p in pdfs_with_keyword],
                'Pages': [p['page_count'] for p in pdfs_with_keyword]
            })
            st.scatter_chart(df_scatter, x='Taille (KB)', y='Occurrences', size='Pages')
            st.caption("Taille vs Occurrences")

if __name__ == "__main__":
    main()
