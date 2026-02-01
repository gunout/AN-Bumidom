import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
import re
import io
import fitz  # PyMuPDF pour l'analyse des PDF
from collections import defaultdict

# Configuration de la page
st.set_page_config(
    page_title="Recherche BUMIDOM - Archives AN", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Recherche avancée BUMIDOM dans les archives parlementaires")
st.markdown("Analyse des archives de la 4ème à la dernière législature")

class BUMIDOMArchiveSearcher:
    def __init__(self):
        self.base_url = "https://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.results = []
        
    def get_legislature_archive_urls(self, start_leg=4, end_leg=16):
        """Récupère les URLs des archives pour chaque législature"""
        legislature_urls = {}
        
        # URLs connues des archives par législature
        for leg in range(start_leg, end_leg + 1):
            if leg == 0:
                url = f"{self.base_url}/0/cri/"
                legislature_urls["Gouvernement provisoire"] = url
            elif leg <= 13:
                url = f"{self.base_url}/{leg}/cri/"
                legislature_urls[f"{leg}e législature"] = url
            else:
                # Pour les législatures 14+, l'URL est différente
                url = f"https://www.assemblee-nationale.fr/dyn/{leg}/comptes-rendus/seances"
                legislature_urls[f"{leg}e législature"] = url
        
        return legislature_urls
    
    def search_in_pdf_content(self, pdf_url, keyword="BUMIDOM"):
        """Analyse le contenu d'un PDF pour trouver le mot-clé"""
        try:
            # Télécharger le PDF
            response = self.session.get(pdf_url, timeout=30)
            
            if response.status_code != 200:
                return None
            
            # Ouvrir le PDF avec PyMuPDF
            pdf_document = fitz.open(stream=response.content, filetype="pdf")
            
            keyword_occurrences = []
            context_texts = []
            
            # Analyser chaque page
            for page_num in range(min(10, pdf_document.page_count)):  # Limiter aux 10 premières pages
                page = pdf_document[page_num]
                text = page.get_text()
                
                # Rechercher le mot-clé
                if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                    # Trouver toutes les occurrences
                    matches = re.finditer(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE)
                    
                    for match in matches:
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end].replace('\n', ' ').strip()
                        
                        keyword_occurrences.append({
                            'page': page_num + 1,
                            'position': match.start(),
                            'context': context
                        })
            
            pdf_document.close()
            
            return {
                'found': len(keyword_occurrences) > 0,
                'total_occurrences': len(keyword_occurrences),
                'occurrences': keyword_occurrences,
                'page_count': pdf_document.page_count
            }
            
        except Exception as e:
            st.warning(f"Erreur d'analyse PDF {pdf_url}: {str(e)[:100]}")
            return None
    
    def search_debates_by_year(self, legislature, year, keyword="BUMIDOM"):
        """Recherche dans les débats d'une année spécifique"""
        results = []
        
        # Construire l'URL des débats pour l'année
        if legislature.isdigit():
            leg_num = int(re.search(r'\d+', legislature).group())
            if leg_num <= 13:
                base_debates_url = f"{self.base_url}/{leg_num}/cri/"
                
                # Essayer différents formats de dates
                date_patterns = [
                    f"{year}-",
                    f"{year}",
                    f"{year % 100:02d}"  # Format 2 chiffres
                ]
                
                # Récupérer la page d'index des débats
                try:
                    response = self.session.get(base_debates_url)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Chercher tous les liens PDF
                    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    
                    for link in pdf_links[:50]:  # Limiter pour les tests
                        pdf_url = link.get('href', '')
                        if not pdf_url.startswith('http'):
                            pdf_url = urljoin(base_debates_url, pdf_url)
                        
                        # Vérifier si c'est un débat de l'année recherchée
                        if any(pattern in pdf_url.lower() for pattern in date_patterns):
                            # Analyser le contenu du PDF
                            analysis = self.search_in_pdf_content(pdf_url, keyword)
                            
                            if analysis and analysis['found']:
                                results.append({
                                    'legislature': legislature,
                                    'year': year,
                                    'pdf_url': pdf_url,
                                    'title': link.get_text(strip=True),
                                    'occurrences': analysis['total_occurrences'],
                                    'contexts': [occ['context'] for occ in analysis['occurrences'][:3]],  # 3 premiers contextes
                                    'page_count': analysis.get('page_count', 0)
                                })
                                
                                time.sleep(0.5)  # Pause pour respecter le serveur
                                
                except Exception as e:
                    st.warning(f"Erreur pour {legislature} {year}: {str(e)[:100]}")
        
        return results
    
    def comprehensive_search(self, start_year=1959, end_year=2023, keyword="BUMIDOM"):
        """Recherche complète sur plusieurs années"""
        all_results = []
        
        # Période d'activité du BUMIDOM: 1963-1982
        bumidom_active_years = list(range(1963, 1983))
        
        # Ajouter quelques années avant/après pour contexte
        search_years = list(range(max(1959, start_year), min(2000, end_year) + 1))
        
        st.info(f"Recherche de '{keyword}' sur {len(search_years)} années ({search_years[0]}-{search_years[-1]})")
        
        progress_bar = st.progress(0)
        
        for idx, year in enumerate(search_years):
            # Mettre à jour la barre de progression
            progress = (idx + 1) / len(search_years)
            progress_bar.progress(progress)
            
            # Déterminer la législature pour cette année
            legislature = self.get_legislature_for_year(year)
            
            if legislature:
                st.write(f"🔍 {year} ({legislature})...")
                
                # Rechercher dans les débats de cette année
                year_results = self.search_debates_by_year(legislature, year, keyword)
                
                if year_results:
                    all_results.extend(year_results)
                    st.success(f"  → {len(year_results)} document(s) trouvé(s)")
            
            time.sleep(0.3)  # Pause entre les années
        
        progress_bar.empty()
        return all_results
    
    def get_legislature_for_year(self, year):
        """Détermine la législature correspondant à une année"""
        # Correspondance approximative année -> législature (Cinquième République)
        if 1959 <= year <= 1962:
            return "1"  # 1ère législature
        elif 1963 <= year <= 1967:
            return "2"  # 2ème législature
        elif 1968 <= year <= 1972:
            return "3"  # 3ème législature
        elif 1973 <= year <= 1977:
            return "4"  # 4ème législature
        elif 1978 <= year <= 1980:
            return "5"  # 5ème législature
        elif 1981 <= year <= 1985:
            return "6"  # 6ème législature
        elif 1986 <= year <= 1987:
            return "7"  # 7ème législature
        elif 1988 <= year <= 1992:
            return "8"  # 8ème législature
        elif 1993 <= year <= 1997:
            return "9"  # 9ème législature
        elif 1998 <= year <= 2001:
            return "10"  # 10ème législature
        elif 2002 <= year <= 2006:
            return "11"  # 11ème législature
        elif 2007 <= year <= 2011:
            return "12"  # 12ème législature
        elif 2012 <= year <= 2016:
            return "13"  # 13ème législature
        elif 2017 <= year <= 2021:
            return "14"  # 14ème législature
        elif 2022 <= year <= 2023:
            return "15"  # 15ème législature
        else:
            return None

def main():
    """Interface principale du dashboard"""
    
    # Sidebar avec les paramètres
    with st.sidebar:
        st.header("⚙️ Paramètres de recherche")
        
        keyword = st.text_input("Mot-clé principal:", value="BUMIDOM")
        
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input("Année début:", min_value=1959, max_value=2023, value=1963, step=1)
        with col2:
            end_year = st.number_input("Année fin:", min_value=1959, max_value=2023, value=1982, step=1)
        
        search_button = st.button("🚀 Lancer la recherche approfondie", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### ℹ️ À propos")
        st.info("""
        Cette recherche analyse le contenu des PDF des débats parlementaires.
        
        **Période BUMIDOM:** 1963-1982
        **Méthode:** Analyse textuelle des PDF
        """)
    
    # Initialisation du chercheur
    searcher = BUMIDOMArchiveSearcher()
    
    if search_button:
        with st.spinner(f"Recherche de '{keyword}' en cours (1963-1982)..."):
            results = searcher.comprehensive_search(start_year, end_year, keyword)
        
        # Afficher les résultats
        if results:
            st.success(f"✅ {len(results)} document(s) trouvé(s) contenant '{keyword}'")
            
            # Créer un DataFrame pour l'affichage
            df = pd.DataFrame(results)
            
            # Afficher les statistiques
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Documents trouvés", len(df))
            with col_stat2:
                st.metric("Occurrences totales", df['occurrences'].sum())
            with col_stat3:
                st.metric("Période couverte", f"{df['year'].min()}-{df['year'].max()}")
            
            # Onglets pour différents types d'affichage
            tab1, tab2, tab3 = st.tabs(["📋 Liste des documents", "📊 Statistiques", "🔍 Extraits"])
            
            with tab1:
                # Afficher la liste des documents
                for idx, doc in enumerate(results[:20]):  # Limiter à 20 pour l'affichage
                    with st.expander(f"📄 {doc['year']} - {doc['title'][:80]}... ({doc['occurrences']} occurrences)"):
                        col_doc1, col_doc2 = st.columns([3, 1])
                        
                        with col_doc1:
                            st.markdown(f"**Législature:** {doc['legislature']}e")
                            st.markdown(f"**Année:** {doc['year']}")
                            st.markdown(f"**Occurrences:** {doc['occurrences']}")
                            st.markdown(f"**Pages:** {doc.get('page_count', 'N/A')}")
                            
                            # Afficher les contextes
                            if doc.get('contexts'):
                                st.markdown("**Extraits:**")
                                for context in doc['contexts'][:2]:  # 2 premiers contextes
                                    highlighted = re.sub(
                                        r'\b' + re.escape(keyword) + r'\b',
                                        lambda m: f"**{m.group()}**",
                                        context,
                                        flags=re.IGNORECASE
                                    )
                                    st.markdown(f"• *\"{highlighted}\"*")
                        
                        with col_doc2:
                            # Bouton pour ouvrir le PDF
                            st.markdown(f"[🌐 Ouvrir le PDF]({doc['pdf_url']})", unsafe_allow_html=True)
                            
                            # Bouton pour analyser plus en détail
                            if st.button("🔍 Analyser", key=f"analyze_{idx}"):
                                with st.spinner("Analyse détaillée..."):
                                    detailed = searcher.search_in_pdf_content(doc['pdf_url'], keyword)
                                    if detailed:
                                        st.json(detailed)
            
            with tab2:
                # Statistiques par année
                if 'year' in df.columns:
                    year_stats = df.groupby('year').agg({
                        'occurrences': 'sum',
                        'title': 'count'
                    }).reset_index()
                    
                    year_stats.columns = ['Année', 'Occurrences totales', 'Nombre de documents']
                    
                    # Graphique
                    fig = px.bar(
                        year_stats,
                        x='Année',
                        y='Occurrences totales',
                        title=f"Occurrences de '{keyword}' par année",
                        color='Nombre de documents',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Table des statistiques
                    st.dataframe(year_stats.sort_values('Occurrences totales', ascending=False))
            
            with tab3:
                # Afficher tous les contextes
                all_contexts = []
                for doc in results:
                    if 'contexts' in doc:
                        for context in doc['contexts']:
                            all_contexts.append({
                                'année': doc['year'],
                                'contexte': context,
                                'occurrences': doc['occurrences']
                            })
                
                if all_contexts:
                    for ctx in all_contexts[:10]:  # Limiter à 10 contextes
                        st.markdown(f"**{ctx['année']}** (document avec {ctx['occurrences']} occurrences):")
                        highlighted = re.sub(
                            r'\b' + re.escape(keyword) + r'\b',
                            lambda m: f"**{m.group()}**",
                            ctx['contexte'],
                            flags=re.IGNORECASE
                        )
                        st.markdown(f"> {highlighted}")
                        st.markdown("---")
            
            # Options d'export
            st.markdown("### 💾 Export des résultats")
            col_exp1, col_exp2 = st.columns(2)
            
            with col_exp1:
                # Export CSV
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Télécharger CSV",
                    data=csv,
                    file_name=f"bumidom_recherche_{start_year}_{end_year}.csv",
                    mime="text/csv"
                )
            
            with col_exp2:
                # Export JSON
                json_str = df.to_json(orient='records', force_ascii=False, indent=2)
                st.download_button(
                    label="📊 Télécharger JSON",
                    data=json_str,
                    file_name=f"bumidom_recherche_{start_year}_{end_year}.json",
                    mime="application/json"
                )
        
        else:
            st.warning(f"❌ Aucun document contenant '{keyword}' trouvé pour la période {start_year}-{end_year}")
            
            # Suggestions
            st.markdown("### 💡 Suggestions pour améliorer la recherche:")
            st.markdown("""
            1. **Élargir la période de recherche** (le BUMIDOM a été créé en 1963, mais des débats ont pu avoir lieu après)
            2. **Essayer des variantes orthographiques** (BUMIDOM, Bumidom, B.U.M.I.D.O.M.)
            3. **Rechercher des termes associés**:
               - "migration outre-mer"
               - "départements d'outre-mer"
               - "DOM"
               - "transfert population"
            4. **Consulter directement les archives**:
               - [Archives AN - 5ème législature](https://archives.assemblee-nationale.fr/5/cri/)
               - [Archives AN - 6ème législature](https://archives.assemblee-nationale.fr/6/cri/)
            """)
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 📋 Guide d'utilisation
        
        Ce dashboard permet de rechercher le terme **"BUMIDOM"** dans les archives parlementaires de la 5ème République.
        
        ### Méthodologie:
        1. **Analyse du contenu des PDF** des comptes rendus de débats
        2. **Recherche textuelle** dans les documents (pas seulement dans les noms de fichiers)
        3. **Extraction du contexte** autour des occurrences trouvées
        
        ### Période recommandée:
        - **Début:** 1963 (création du BUMIDOM)
        - **Fin:** 1982 (fin des activités principales)
        
        ### Limitations connues:
        - Certains PDF plus anciens peuvent être scannés (OCR nécessaire)
        - La recherche peut être lente (analyse de nombreux documents)
        - Certaines archives peuvent ne pas être disponibles en ligne
        """)
        
        # Afficher les URLs des archives par législature
        st.markdown("### 📚 Accès direct aux archives:")
        searcher = BUMIDOMArchiveSearcher()
        urls = searcher.get_legislature_archive_urls(4, 8)  # 4ème à 8ème législature
        
        for leg, url in urls.items():
            st.markdown(f"- [{leg}]({url})")

if __name__ == "__main__":
    main()
