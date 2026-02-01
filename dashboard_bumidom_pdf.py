import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime
import urllib.parse
import io

# Configuration
st.set_page_config(page_title="BUMIDOM - Archives JO 1963-1982", layout="wide")
st.title("📜 Recherche BUMIDOM dans les débats parlementaires (1963-1982)")
st.markdown("Accès aux archives du Journal Officiel de la 5ème République")

class JOArchiveSearcher:
    def __init__(self):
        self.jo_base_url = "https://www.assemblee-nationale.fr/histoire/debats-journal-officiel/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_jo_debates_links(self):
        """Récupère les liens vers les archives JO par législature"""
        
        # URLs spécifiques pour la période BUMIDOM
        jo_urls = {
            "2ème législature (1962-1967)": [
                "https://archives.assemblee-nationale.fr/2/cri/",
                "https://www.assemblee-nationale.fr/histoire/debats-journal-officiel/2.asp"
            ],
            "3ème législature (1967-1968)": [
                "https://archives.assemblee-nationale.fr/3/cri/",
                "https://www.assemblee-nationale.fr/histoire/debats-journal-officiel/3.asp"
            ],
            "4ème législature (1968-1973)": [
                "https://archives.assemblee-nationale.fr/4/cri/",
                "https://www.assemblee-nationale.fr/histoire/debats-journal-officiel/4.asp"
            ],
            "5ème législature (1973-1978)": [
                "https://archives.assemblee-nationale.fr/5/cri/",
                "https://www.assemblee-nationale.fr/histoire/debats-journal-officiel/5.asp"
            ],
            "6ème législature (1978-1981)": [
                "https://archives.assemblee-nationale.fr/6/cri/",
                "https://www.assemblee-nationale.fr/histoire/debats-journal-officiel/6.asp"
            ]
        }
        
        return jo_urls
    
    def search_gallica_bnf(self, keyword="BUMIDOM", years=None):
        """Recherche dans Gallica BnF (archives du Journal Officiel)"""
        
        if years is None:
            years = list(range(1963, 1983))
        
        results = []
        
        st.info(f"Recherche dans Gallica BnF pour les années {years[0]}-{years[-1]}")
        
        # URL de recherche Gallica pour le Journal Officiel
        for year in years:
            try:
                # Construction de l'URL de recherche Gallica
                search_url = self.build_gallica_search_url(year, keyword)
                
                st.write(f"🔍 {year}...")
                
                # Récupération de la page
                response = self.session.get(search_url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Recherche des résultats
                    result_items = soup.find_all(['a', 'div'], class_=re.compile(r'result|item', re.I))
                    
                    for item in result_items[:5]:  # Limiter aux 5 premiers
                        link = item.find('a', href=True)
                        if link:
                            title = link.get_text(strip=True)
                            url = link['href']
                            
                            # Vérifier si c'est un JO des débats
                            if any(x in title.lower() for x in ['débats', 'jo', 'journal officiel']):
                                # Vérifier la présence du mot-clé
                                if self.check_keyword_in_gallica(url, keyword):
                                    results.append({
                                        'année': year,
                                        'titre': title[:150],
                                        'url': url,
                                        'source': 'Gallica BnF',
                                        'législature': self.get_legislature_for_year(year)
                                    })
                                    st.success(f"  → Trouvé: {title[:80]}...")
                
                time.sleep(1)  # Pause pour respecter le serveur
                
            except Exception as e:
                st.warning(f"Erreur année {year}: {str(e)[:100]}")
        
        return results
    
    def build_gallica_search_url(self, year, keyword):
        """Construit l'URL de recherche Gallica"""
        # Recherche dans le Journal Officiel des débats parlementaires
        query = urllib.parse.quote(f'"{keyword}" "Journal Officiel" "Débats" {year}')
        return f"https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&version=1.2&query=text%20adj%20%22{query}%22&suggest=0"
    
    def check_keyword_in_gallica(self, url, keyword):
        """Vérifie la présence du mot-clé dans la page Gallica"""
        try:
            response = self.session.get(url, timeout=10)
            return keyword.lower() in response.text.lower()
        except:
            return False
    
    def get_legislature_for_year(self, year):
        """Détermine la législature"""
        if 1962 <= year <= 1967:
            return "2ème"
        elif 1968 <= year <= 1972:
            return "3ème"
        elif 1973 <= year <= 1977:
            return "4ème"
        elif 1978 <= year <= 1980:
            return "5ème"
        elif 1981 <= year <= 1982:
            return "6ème"
        return "Inconnue"
    
    def search_assemblee_questions(self, legislature, keyword="BUMIDOM"):
        """Recherche dans les questions écrites de l'Assemblée"""
        
        results = []
        
        # URL des questions pour chaque législature
        questions_urls = {
            "4": "https://archives.assemblee-nationale.fr/4/qst/",
            "5": "https://archives.assemblee-nationale.fr/5/qst/",
            "6": "https://archives.assemblee-nationale.fr/6/qst/"
        }
        
        leg_num = legislature[0] if legislature[0].isdigit() else None
        
        if leg_num in questions_urls:
            url = questions_urls[leg_num]
            
            try:
                st.write(f"🔎 Recherche dans les questions {legislature}...")
                
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Recherche des liens contenant le mot-clé
                keyword_pattern = re.compile(keyword, re.IGNORECASE)
                matching_links = soup.find_all('a', string=keyword_pattern)
                
                for link in matching_links[:10]:  # Limiter aux 10 premiers
                    href = link.get('href', '')
                    full_url = urllib.parse.urljoin(url, href)
                    
                    results.append({
                        'année': 'N/A',
                        'titre': link.get_text(strip=True),
                        'url': full_url,
                        'source': f'Questions {legislature}',
                        'législature': legislature
                    })
                
                if matching_links:
                    st.success(f"  → {len(matching_links)} question(s) trouvée(s)")
                
            except Exception as e:
                st.warning(f"Erreur questions {legislature}: {str(e)[:100]}")
        
        return results

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Stratégie de recherche")
        
        search_method = st.radio(
            "Méthode de recherche:",
            ["Gallica BnF (Journal Officiel)", 
             "Questions écrites AN",
             "Recherche avancée"]
        )
        
        keyword = st.text_input("Mot-clé principal:", value="BUMIDOM")
        
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input("Début:", 1963, 1982, 1963)
        with col2:
            end_year = st.number_input("Fin:", 1963, 1982, 1982)
        
        # Options avancées
        with st.expander("Options avancées"):
            variant_search = st.checkbox("Recherche par variantes", value=True)
            if variant_search:
                st.text_area("Variantes à chercher:", 
                           value="BUMIDOM\nBumidom\nBureau migrations DOM\nMigration outre-mer")
        
        search_button = st.button("🚀 Lancer la recherche", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Sources disponibles:**
        - Gallica BnF (Journal Officiel)
        - Questions écrites AN
        - Archives par législature
        """)
    
    # Initialisation
    searcher = JOArchiveSearcher()
    
    if search_button:
        all_results = []
        
        if search_method == "Gallica BnF (Journal Officiel)":
            with st.spinner(f"Recherche dans Gallica BnF ({start_year}-{end_year})..."):
                results = searcher.search_gallica_bnf(
                    keyword, 
                    list(range(start_year, end_year + 1))
                )
                all_results.extend(results)
        
        elif search_method == "Questions écrites AN":
            with st.spinner("Recherche dans les questions écrites..."):
                # Recherche dans les législatures pertinentes
                for leg in ["4ème législature", "5ème législature", "6ème législature"]:
                    results = searcher.search_assemblee_questions(leg, keyword)
                    all_results.extend(results)
        
        # Affichage des résultats
        if all_results:
            st.success(f"✅ {len(all_results)} résultat(s) trouvé(s)")
            
            # DataFrame
            df = pd.DataFrame(all_results)
            
            # Affichage par source
            st.subheader("📊 Résultats par source")
            source_counts = df['source'].value_counts()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", len(df))
            with col2:
                st.metric("Sources", len(source_counts))
            with col3:
                if not df.empty and 'année' in df.columns:
                    years = df[df['année'] != 'N/A']['année'].unique()
                    st.metric("Années", len(years))
            
            # Table des résultats
            st.subheader("📋 Liste des documents")
            for idx, result in enumerate(all_results):
                with st.expander(f"📄 {result['titre'][:100]}..."):
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        st.markdown(f"**Source:** {result['source']}")
                        if result['année'] != 'N/A':
                            st.markdown(f"**Année:** {result['année']}")
                        st.markdown(f"**Législature:** {result['législature']}")
                        st.markdown(f"**URL:** {result['url'][:100]}...")
                    
                    with col_b:
                        # Bouton pour ouvrir
                        st.markdown(f"[🌐 Ouvrir]({result['url']})", unsafe_allow_html=True)
            
            # Export
            st.subheader("💾 Export des résultats")
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Télécharger CSV",
                data=csv,
                file_name=f"bumidom_recherche_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("❌ Aucun résultat trouvé")
            
            # Guide de recherche manuelle
            st.subheader("🔍 Guide pour recherche manuelle")
            
            col_guide1, col_guide2 = st.columns(2)
            
            with col_guide1:
                st.markdown("""
                ### 1. Gallica BnF - Journal Officiel
                
                **Recherche directe:**
                1. Aller sur [Gallica BnF](https://gallica.bnf.fr)
                2. Chercher: **"BUMIDOM Journal Officiel Débats"**
                3. Filtrer par date: 1963-1982
                4. Consulter les résultats
                
                **URLs types:**
                - JO Débats 1975: `gallica.bnf.fr/ark:/.../f1.item`
                """)
            
            with col_guide2:
                st.markdown("""
                ### 2. Archives Assemblée Nationale
                
                **Questions écrites:**
                - [4ème lég. Questions](https://archives.assemblee-nationale.fr/4/qst/)
                - [5ème lég. Questions](https://archives.assemblee-nationale.fr/5/qst/)
                - [6ème lég. Questions](https://archives.assemblee-nationale.fr/6/qst/)
                
                **Termes alternatifs:**
                - Bureau migrations DOM
                - Migration outre-mer
                - Départements d'outre-mer
                """)
            
            # Liens directs
            st.subheader("🔗 Accès direct aux archives")
            
            jo_urls = searcher.get_jo_debates_links()
            for legislature, urls in jo_urls.items():
                with st.expander(f"📚 {legislature}"):
                    for url in urls:
                        st.markdown(f"- [{url.split('/')[-1]}]({url})")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 📋 Pourquoi le scraping direct ne fonctionne pas ?
        
        ### Problèmes identifiés:
        1. **Archives non normalisées**: Les URLs changent selon les législatures
        2. **Absence de PDF direct**: Les années 1963-1982 ne sont pas en PDF accessible
        3. **Protection anti-scraping**: Le site limite l'accès automatisé
        
        ### Solution recommandée:
        **Utiliser Gallica BnF** qui archive le Journal Officiel complet.
        
        ### Période BUMIDOM (1963-1982):
        """)
        
        # Timeline visuelle
        timeline_data = {
            "1963": "Création du BUMIDOM",
            "1963-1967": "2ème législature",
            "1968-1972": "3ème législature", 
            "1973-1977": "4ème législature",
            "1978-1981": "5ème législature",
            "1982": "Fin des activités"
        }
        
        for year, event in timeline_data.items():
            st.markdown(f"- **{year}**: {event}")
        
        # Méthodologie
        st.markdown("""
        ### 📊 Méthodologie de recherche:
        
        1. **Gallica BnF**: Journal Officiel des débats
        2. **Questions écrites**: Archives AN par législature  
        3. **Recherche manuelle**: Combinaison des deux
        """)

if __name__ == "__main__":
    main()
