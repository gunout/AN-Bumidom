import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import time
import re
import io
import fitz  # PyMuPDF
import numpy as np
from collections import Counter

# Configuration
st.set_page_config(page_title="Recherche BUMIDOM - Débats AN", layout="wide")
st.title("🔍 Recherche BUMIDOM dans les comptes rendus de débats")
st.markdown("Analyse des débats parlementaires de 1963 à 1982")

class DebateBUMIDOMSearcher:
    def __init__(self):
        self.base_url = "https://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_debate_pdf_urls(self, legislature, year):
        """Récupère les URLs des PDF de débats pour une législature et année donnée"""
        # Structure standard des archives de débats
        if legislature <= 13:
            base_cri_url = f"{self.base_url}/{legislature}/cri/"
        else:
            return []
        
        try:
            response = self.session.get(base_cri_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            pdf_urls = []
            # Chercher tous les liens PDF
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                # Filtrer les PDF de débats
                if (href.lower().endswith('.pdf') and 
                    ('cri' in href.lower() or 'compte' in text or 
                     str(year) in href or str(year) in text)):
                    
                    full_url = urljoin(base_cri_url, href)
                    
                    # Éviter les tables analytiques/nominatives
                    if not any(x in href.lower() for x in ['tanalytique', 'tnominative', 'tmatieres']):
                        pdf_urls.append({
                            'url': full_url,
                            'title': link.get_text(strip=True) or href,
                            'year': year,
                            'legislature': legislature
                        })
            
            return pdf_urls
            
        except Exception as e:
            st.warning(f"Erreur accès {base_cri_url}: {str(e)[:100]}")
            return []
    
    def analyze_pdf_content(self, pdf_url, keyword="BUMIDOM"):
        """Analyse le contenu d'un PDF pour trouver le mot-clé"""
        try:
            response = self.session.get(pdf_url, timeout=30)
            
            if response.status_code != 200:
                return None
            
            # CORRECTION : Ouvrir le PDF avec un context manager
            pdf_data = response.content
            with fitz.open(stream=pdf_data, filetype="pdf") as pdf_document:
                
                keyword_occurrences = []
                total_text = ""
                
                # Analyser chaque page (limité pour performance)
                for page_num in range(min(50, pdf_document.page_count)):
                    page = pdf_document[page_num]
                    text = page.get_text()
                    total_text += text + "\n"
                    
                    # Rechercher le mot-clé
                    matches = re.finditer(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE)
                    
                    for match in matches:
                        start = max(0, match.start() - 150)
                        end = min(len(text), match.end() + 150)
                        context = text[start:end].replace('\n', ' ').strip()
                        
                        keyword_occurrences.append({
                            'page': page_num + 1,
                            'context': context,
                            'full_match': match.group()
                        })
                
                # Vérifier aussi dans tout le texte (pour les mots coupés)
                if not keyword_occurrences:
                    all_matches = re.findall(r'(?i)\bbumidom\b', total_text)
                    if all_matches:
                        # Prendre un échantillon du texte pour contexte
                        sample_start = total_text.find('bumidom')
                        if sample_start != -1:
                            sample = total_text[max(0, sample_start-200):min(len(total_text), sample_start+200)]
                            keyword_occurrences.append({
                                'page': 1,
                                'context': sample.replace('\n', ' ').strip(),
                                'full_match': 'BUMIDOM'
                            })
            
            return {
                'found': len(keyword_occurrences) > 0,
                'total_occurrences': len(keyword_occurrences),
                'occurrences': keyword_occurrences,
                'text_sample': total_text[:1000] if total_text else ""
            }
            
        except Exception as e:
            st.warning(f"Erreur PDF {pdf_url}: {str(e)[:100]}")
            return None
    
    def search_year_debates(self, year, keyword="BUMIDOM"):
        """Recherche dans tous les débats d'une année spécifique"""
        results = []
        
        # Déterminer la législature pour cette année
        legislature_map = {
            **{y: 2 for y in range(1963, 1968)},  # 2ème législature
            **{y: 3 for y in range(1968, 1973)},  # 3ème législature
            **{y: 4 for y in range(1973, 1978)},  # 4ème législature
            **{y: 5 for y in range(1978, 1981)},  # 5ème législature
            **{y: 6 for y in range(1981, 1983)},  # 6ème législature
        }
        
        legislature = legislature_map.get(year)
        if not legislature:
            return results
        
        st.write(f"🔍 Recherche {year} (Législature {legislature})...")
        
        # Récupérer les URLs des débats
        pdf_urls = self.get_debate_pdf_urls(legislature, year)
        
        if not pdf_urls:
            st.info(f"  Aucun PDF de débat trouvé pour {year}")
            return results
        
        st.info(f"  {len(pdf_urls)} PDF(s) de débats à analyser")
        
        # Analyser chaque PDF
        for pdf_info in pdf_urls[:10]:  # Limiter à 10 PDF par année pour test
            analysis = self.analyze_pdf_content(pdf_info['url'], keyword)
            
            if analysis and analysis['found']:
                results.append({
                    'year': year,
                    'legislature': legislature,
                    'pdf_url': pdf_info['url'],
                    'title': pdf_info['title'],
                    'occurrences': analysis['total_occurrences'],
                    'contexts': [occ['context'] for occ in analysis['occurrences'][:3]],
                    'first_context': analysis['occurrences'][0]['context'] if analysis['occurrences'] else ""
                })
                
                st.success(f"    ✓ Trouvé dans: {pdf_info['title'][:50]}... ({analysis['total_occurrences']} occ.)")
            
            time.sleep(0.3)  # Pause
        
        return results

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Paramètres")
        
        keyword = st.text_input("Mot-clé:", value="BUMIDOM")
        
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input("Début:", 1963, 1982, 1963)
        with col2:
            end_year = st.number_input("Fin:", 1963, 1982, 1982)
        
        search_button = st.button("🚀 Lancer la recherche", type="primary")
        
        st.markdown("---")
        st.info("""
        **Période BUMIDOM:** 1963-1982
        **Sources:** Comptes rendus de débats
        """)
    
    # Initialisation
    searcher = DebateBUMIDOMSearcher()
    
    if search_button:
        all_results = []
        
        # Barre de progression
        years = list(range(start_year, end_year + 1))
        progress_bar = st.progress(0)
        
        for idx, year in enumerate(years):
            progress = (idx + 1) / len(years)
            progress_bar.progress(progress)
            
            # Recherche pour cette année
            year_results = searcher.search_year_debates(year, keyword)
            all_results.extend(year_results)
        
        progress_bar.empty()
        
        # Affichage des résultats
        if all_results:
            st.success(f"✅ {len(all_results)} document(s) trouvé(s) contenant '{keyword}'")
            
            # DataFrame
            df = pd.DataFrame(all_results)
            
            # Statistiques
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Documents", len(df))
            with col2:
                st.metric("Occurrences", df['occurrences'].sum())
            with col3:
                st.metric("Années couvertes", f"{df['year'].min()}-{df['year'].max()}")
            
            # Affichage détaillé
            for result in all_results:
                with st.expander(f"📅 {result['year']} - {result['title'][:80]}... ({result['occurrences']} occ.)"):
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        st.markdown(f"**Législature:** {result['legislature']}ème")
                        st.markdown(f"**URL:** [{result['title']}]({result['pdf_url']})")
                        
                        # Contexte
                        if result.get('contexts'):
                            st.markdown("**Contexte des occurrences:**")
                            for ctx in result['contexts'][:2]:
                                highlighted = re.sub(
                                    r'\b' + re.escape(keyword) + r'\b',
                                    lambda m: f"**{m.group()}**",
                                    ctx,
                                    flags=re.IGNORECASE
                                )
                                st.markdown(f"• *\"{highlighted}\"*")
                    
                    with col_b:
                        # Bouton pour voir le PDF
                        if st.button("👁️ Voir PDF", key=f"view_{result['pdf_url'][-20:]}"):
                            st.components.v1.iframe(result['pdf_url'], height=600)
            
            # Export
            st.markdown("### 💾 Export")
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Télécharger CSV",
                data=csv,
                file_name=f"debats_bumidom_{start_year}_{end_year}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning(f"❌ Aucun document trouvé contenant '{keyword}'")
            
            # Stratégies alternatives
            st.markdown("### 💡 Stratégies alternatives:")
            
            col_alt1, col_alt2 = st.columns(2)
            
            with col_alt1:
                st.markdown("""
                **1. Chercher dans les Questions:**
                - Questions écrites au gouvernement
                - Questions orales
                - URL pattern: `/qst/` dans les archives
                """)
                
                # Lien direct vers les questions
                st.markdown("[🔗 Questions 5ème législature](https://archives.assemblee-nationale.fr/5/qst/)")
                st.markdown("[🔗 Questions 6ème législature](https://archives.assemblee-nationale.fr/6/qst/)")
            
            with col_alt2:
                st.markdown("""
                **2. Termes alternatifs:**
                - Bureau migrations DOM
                - Migration outre-mer
                - Départements d'outre-mer
                - Transfert population
                """)
            
            # Lien direct vers les recherches manuelles
            st.markdown("### 🔗 Recherches manuelles recommandées:")
            st.markdown("""
            1. **[Débats 5ème législature (1973-1978)](https://archives.assemblee-nationale.fr/5/cri/)**
            2. **[Questions 5ème législature](https://archives.assemblee-nationale.fr/5/qst/)**
            3. **[Débats 6ème législature (1978-1981)](https://archives.assemblee-nationale.fr/6/cri/)**
            4. **[Recherche textuelle sur le site](https://www.assemblee-nationale.fr/recherche/query.asp)**
            """)
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 📋 Guide d'utilisation
        
        Ce dashboard recherche **BUMIDOM** dans les **comptes rendus de débats parlementaires**.
        
        ### Période cible: 1963-1982
        - **2ème législature** (1963-1967)
        - **3ème législature** (1968-1972)
        - **4ème législature** (1973-1977)
        - **5ème législature** (1978-1981)
        - **6ème législature** (1981-1982)
        
        ### Sources analysées:
        - Comptes rendus intégraux des séances
        - Débats parlementaires
        - Discussions en séance publique
        
        ### Note importante:
        Les débats des années 1960-1970 peuvent être:
        - Numérisés en format image
        - Nécessitant une OCR de bonne qualité
        - Parfois en plusieurs volumes
        """)

if __name__ == "__main__":
    main()
