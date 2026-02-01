import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import fitz  # PyMuPDF pour les PDF
import io
import base64
import re
from datetime import datetime
import time
import urllib.parse
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import numpy as np
import json

# Configuration de la page
st.set_page_config(
    page_title="Analyse Premium PDF - Archives AN",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Premium
st.markdown("""
<style>
    .premium-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .metric-premium {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-left: 5px solid #764ba2;
        transition: transform 0.3s;
    }
    .metric-premium:hover {
        transform: translateY(-5px);
    }
    .pdf-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .premium-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 25px;
        font-weight: bold;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

class PremiumPDFScraper:
    """Scraper premium pour extraire les 100 PDF des archives"""
    
    def __init__(self):
        self.base_url = "https://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
        self.pdf_data = []
        
    def search_google_custom_search(self, query="BUMIDOM", num_pages=10):
        """Utilise la recherche Google intégrée pour trouver des PDF"""
        
        st.info(f"🔍 Recherche Google des PDF avec le terme: '{query}'")
        
        # Construction des URLs de recherche (simulation)
        search_urls = []
        for page in range(num_pages):
            # URL de recherche simulée basée sur la structure du site
            search_url = f"{self.base_url}/recherche?q={query}&type=pdf&start={page*10}"
            search_urls.append(search_url)
        
        pdf_links = []
        
        # Recherche dans les pages de résultats
        for url in search_urls:
            try:
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Trouver tous les liens PDF
                pdf_elements = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for element in pdf_elements:
                    pdf_url = element.get('href', '')
                    if pdf_url:
                        if not pdf_url.startswith('http'):
                            pdf_url = urllib.parse.urljoin(self.base_url, pdf_url)
                        
                        title = element.get_text(strip=True) or element.get('title', '') or "Document sans titre"
                        
                        pdf_links.append({
                            'url': pdf_url,
                            'title': title[:200],  # Limiter la longueur
                            'source_url': url,
                            'rank': len(pdf_links) + 1
                        })
                
                # Recherche spécifique BUMIDOM dans les textes
                bumidom_elements = soup.find_all(text=re.compile(r'bumidom|BUMIDOM', re.I))
                for element in bumidom_elements:
                    parent = element.parent
                    if parent.name == 'a' and parent.get('href', '').endswith('.pdf'):
                        pdf_url = parent.get('href')
                        if not pdf_url.startswith('http'):
                            pdf_url = urllib.parse.urljoin(self.base_url, pdf_url)
                        
                        pdf_links.append({
                            'url': pdf_url,
                            'title': f"BUMIDOM - {parent.get_text(strip=True)[:100]}",
                            'source_url': url,
                            'rank': len(pdf_links) + 1
                        })
                
                time.sleep(1)  # Respect du serveur
                
            except Exception as e:
                st.warning(f"Erreur page {url}: {str(e)[:100]}")
                continue
        
        return pdf_links[:100]  # Limiter à 100 PDF
    
    def scrape_pdf_content(self, pdf_info):
        """Télécharge et analyse un PDF"""
        try:
            st.write(f"📥 Téléchargement: {pdf_info['title'][:50]}...")
            
            response = self.session.get(pdf_info['url'], timeout=30)
            
            if response.status_code == 200:
                # Analyser le PDF
                pdf_document = fitz.open(stream=response.content, filetype="pdf")
                
                # Extraire le texte
                full_text = ""
                metadata = pdf_document.metadata
                
                # Limiter aux premières pages pour la performance
                for page_num in range(min(20, pdf_document.page_count)):
                    page = pdf_document[page_num]
                    full_text += page.get_text()
                
                # Analyse spécifique
                analysis = self.analyze_pdf_content(full_text, pdf_info['title'])
                
                pdf_data = {
                    'titre': pdf_info['title'],
                    'url': pdf_info['url'],
                    'pages': pdf_document.page_count,
                    'taille_mo': len(response.content) / (1024 * 1024),
                    'texte_complet': full_text[:5000],  # Limité pour stockage
                    **analysis,
                    'metadata': metadata,
                    'date_extraction': datetime.now().isoformat(),
                    'score_pertinence': self.calculate_relevance_score(full_text, pdf_info['title'])
                }
                
                pdf_document.close()
                return pdf_data
                
        except Exception as e:
            st.error(f"❌ Erreur PDF {pdf_info['url']}: {str(e)[:100]}")
        
        return None
    
    def analyze_pdf_content(self, text, title):
        """Analyse avancée du contenu PDF"""
        
        # Détection de termes clés
        keywords_bumidom = ['bumidom', 'migration', 'outre-mer', 'dom', 'réparation', 'victimes']
        keywords_found = []
        
        for keyword in keywords_bumidom:
            if re.search(keyword, text, re.IGNORECASE):
                keywords_found.append(keyword)
        
        # Comptage des occurrences
        text_lower = text.lower()
        bumidom_count = len(re.findall(r'bumidom', text_lower))
        
        # Extraction de dates
        dates = re.findall(r'\d{2}/\d{2}/\d{4}', text)
        
        # Détection de noms de députés
        deputes_pattern = r'(M\.|Mme|Monsieur|Madame)\s+[A-Z][a-zéèêëàâäôöûüç]+\s+[A-Z][a-zéèêëàâäôöûüç]+'
        deputes = re.findall(deputes_pattern, text)
        
        return {
            'mots_cles': keywords_found,
            'mentions_bumidom': bumidom_count,
            'dates_trouvees': dates[:10],  # Limiter à 10 dates
            'deputes_mentionnes': list(set(deputes))[:5],
            'longueur_texte': len(text),
            'mots_uniques': len(set(text.lower().split())),
            'densite_bumidom': bumidom_count / max(1, len(text.split()) / 1000)
        }
    
    def calculate_relevance_score(self, text, title):
        """Calcule un score de pertinence pour le classement"""
        score = 0
        
        # Score basé sur le titre
        if re.search(r'bumidom', title, re.IGNORECASE):
            score += 50
        
        # Score basé sur le contenu
        text_lower = text.lower()
        bumidom_matches = len(re.findall(r'bumidom', text_lower))
        score += min(bumidom_matches * 10, 100)
        
        # Score basé sur la longueur (documents plus longs souvent plus détaillés)
        score += min(len(text) / 100, 50)
        
        return min(score, 100)
    
    def batch_scrape_pdfs(self, query="BUMIDOM", num_pdfs=100):
        """Scrape un lot de PDF"""
        
        with st.spinner(f"🔍 Recherche de {num_pdfs} PDF..."):
            # Étape 1: Recherche
            pdf_links = self.search_google_custom_search(query, num_pages=10)
            
            if not pdf_links:
                st.error("Aucun PDF trouvé. Vérifiez la connexion ou les paramètres.")
                return []
            
            st.success(f"✅ {len(pdf_links)} PDF trouvés")
            
            # Étape 2: Téléchargement et analyse
            progress_bar = st.progress(0)
            all_pdf_data = []
            
            for idx, pdf_info in enumerate(pdf_links[:num_pdfs]):
                # Mise à jour de la progression
                progress = (idx + 1) / min(len(pdf_links), num_pdfs)
                progress_bar.progress(progress)
                
                # Analyse du PDF
                pdf_data = self.scrape_pdf_content(pdf_info)
                if pdf_data:
                    all_pdf_data.append(pdf_data)
                    st.write(f"✓ Analysé: {pdf_data['titre'][:60]}...")
                
                # Pause pour respecter le serveur
                time.sleep(0.5)
            
            progress_bar.empty()
            
            return all_pdf_data

class PremiumDashboard:
    """Dashboard premium avec fonctionnalités avancées"""
    
    def __init__(self):
        self.scraper = PremiumPDFScraper()
        self.pdf_data = []
        
    def display_premium_header(self):
        """En-tête premium du dashboard"""
        
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Logo_Assemblee_nationale_%28France%29.svg/800px-Logo_Assemblee_nationale_%28France%29.svg.png",
                    width=120)
        
        with col2:
            st.markdown("""
            <div class="premium-header">
                <h1>💰 ANALYSE PREMIUM BUMIDOM</h1>
                <h3>Archives de l'Assemblée Nationale - 100 PDF Analyse</h3>
                <p>Dashboard interactif avec scraping automatisé, analyse IA et visualisations avancées</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 2rem;">🚀</div>
                <div style="font-weight: bold; color: #764ba2;">VERSION PREMIUM</div>
                <div style="font-size: 0.8rem; color: #666;">Analyse complète</div>
            </div>
            """, unsafe_allow_html=True)
    
    def display_control_panel(self):
        """Panneau de contrôle premium"""
        
        st.sidebar.markdown("### 🎛️ PANEL DE CONTRÔLE PREMIUM")
        
        # Recherche
        search_query = st.sidebar.text_input(
            "🔍 Terme de recherche:",
            value="BUMIDOM migration outre-mer",
            help="Terme à rechercher dans les PDF"
        )
        
        num_pdfs = st.sidebar.slider(
            "📊 Nombre de PDF à analyser:",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
        
        # Options avancées
        st.sidebar.markdown("### ⚙️ OPTIONS AVANCÉES")
        
        col_opt1, col_opt2 = st.sidebar.columns(2)
        
        with col_opt1:
            extract_full_text = st.checkbox("📝 Texte complet", value=True)
            analyze_sentiment = st.checkbox("😊 Analyse sentiment", value=True)
        
        with col_opt2:
            extract_tables = st.checkbox("📊 Extraire tables", value=False)
            detect_entities = st.checkbox("👤 Détecter entités", value=True)
        
        # Bouton d'analyse
        if st.sidebar.button("🚀 Lancer l'analyse premium", type="primary", use_container_width=True):
            with st.spinner(f"Analyse de {num_pdfs} PDF en cours..."):
                self.pdf_data = self.scraper.batch_scrape_pdfs(search_query, num_pdfs)
                
                if self.pdf_data:
                    # Sauvegarde des données
                    self.save_analysis_data()
                    st.success(f"✅ Analyse terminée: {len(self.pdf_data)} PDF analysés")
                    st.rerun()
                else:
                    st.error("❌ Aucun PDF n'a pu être analysé")
        
        # Statistiques rapides
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 STATS RAPIDES")
        
        if self.pdf_data:
            df = pd.DataFrame(self.pdf_data)
            total_mentions = df['mentions_bumidom'].sum()
            avg_score = df['score_pertinence'].mean()
            
            st.sidebar.metric("📄 PDF Analysés", len(self.pdf_data))
            st.sidebar.metric("🔍 Mentions BUMIDOM", f"{total_mentions:,}")
            st.sidebar.metric("⭐ Score moyen", f"{avg_score:.1f}/100")
        
        return search_query, num_pdfs
    
    def display_premium_metrics(self):
        """Affiche les métriques premium"""
        
        if not self.pdf_data:
            return
        
        df = pd.DataFrame(self.pdf_data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-premium">
                <div style="font-size: 2.5rem; color: #764ba2;">{len(df)}</div>
                <div style="color: #666;">📄 PDF Analysés</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_pages = df['pages'].sum()
            st.markdown(f"""
            <div class="metric-premium">
                <div style="font-size: 2.5rem; color: #764ba2;">{total_pages:,}</div>
                <div style="color: #666;">📑 Pages totales</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_mentions = df['mentions_bumidom'].sum()
            st.markdown(f"""
            <div class="metric-premium">
                <div style="font-size: 2.5rem; color: #764ba2;">{total_mentions:,}</div>
                <div style="color: #666;">🔍 Mentions BUMIDOM</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_size = df['taille_mo'].sum()
            st.markdown(f"""
            <div class="metric-premium">
                <div style="font-size: 2.5rem; color: #764ba2;">{total_size:.1f}</div>
                <div style="color: #666;">💾 Mo de données</div>
            </div>
            """, unsafe_allow_html=True)
    
    def display_pdf_explorer(self):
        """Explorateur de PDF premium"""
        
        st.markdown("### 📚 EXPLORATEUR DE PDF PREMIUM")
        
        if not self.pdf_data:
            st.info("🎯 Lancez d'abord une analyse dans le panel de contrôle")
            return
        
        df = pd.DataFrame(self.pdf_data)
        
        # Filtres avancés
        col_filt1, col_filt2, col_filt3, col_filt4 = st.columns(4)
        
        with col_filt1:
            min_score = st.slider("Score minimum", 0, 100, 50)
        
        with col_filt2:
            min_mentions = st.number_input("Mentions min", 0, 100, 1)
        
        with col_filt3:
            min_pages = st.number_input("Pages min", 1, 1000, 5)
        
        with col_filt4:
            sort_by = st.selectbox("Trier par", 
                                  ["Score pertinence", "Mentions BUMIDOM", "Pages", "Taille"])
        
        # Appliquer les filtres
        filtered_df = df.copy()
        filtered_df = filtered_df[filtered_df['score_pertinence'] >= min_score]
        filtered_df = filtered_df[filtered_df['mentions_bumidom'] >= min_mentions]
        filtered_df = filtered_df[filtered_df['pages'] >= min_pages]
        
        # Trier
        if sort_by == "Score pertinence":
            filtered_df = filtered_df.sort_values('score_pertinence', ascending=False)
        elif sort_by == "Mentions BUMIDOM":
            filtered_df = filtered_df.sort_values('mentions_bumidom', ascending=False)
        elif sort_by == "Pages":
            filtered_df = filtered_df.sort_values('pages', ascending=False)
        elif sort_by == "Taille":
            filtered_df = filtered_df.sort_values('taille_mo', ascending=False)
        
        # Afficher les PDF
        for idx, row in filtered_df.iterrows():
            with st.expander(f"📄 {row['titre'][:80]}...", expanded=False):
                col_pdf1, col_pdf2 = st.columns([3, 1])
                
                with col_pdf1:
                    # Métriques du document
                    col_met1, col_met2, col_met3, col_met4 = st.columns(4)
                    
                    with col_met1:
                        st.metric("⭐ Score", f"{row['score_pertinence']:.1f}")
                    
                    with col_met2:
                        st.metric("🔍 Mentions", row['mentions_bumidom'])
                    
                    with col_met3:
                        st.metric("📑 Pages", row['pages'])
                    
                    with col_met4:
                        st.metric("💾 Taille", f"{row['taille_mo']:.1f} Mo")
                    
                    # Mots-clés
                    if row['mots_cles']:
                        st.write("**🏷️ Mots-clés:**", ", ".join(row['mots_cles']))
                    
                    # Extraits du texte
                    if 'texte_complet' in row and row['texte_complet']:
                        with st.expander("📝 Voir extrait du texte"):
                            st.text(row['texte_complet'][:1000])
                
                with col_pdf2:
                    # Actions
                    st.markdown("**🔗 Actions**")
                    
                    if st.button("🌐 Ouvrir PDF", key=f"open_{idx}"):
                        st.markdown(f'<a href="{row["url"]}" target="_blank">Ouvrir dans un nouvel onglet</a>', 
                                  unsafe_allow_html=True)
                    
                    if st.button("📥 Télécharger", key=f"dl_{idx}"):
                        self.download_pdf(row['url'], row['titre'])
                    
                    # Visualisation PDF
                    if st.button("👁️ Prévisualiser", key=f"preview_{idx}"):
                        self.display_pdf_preview(row['url'])
    
    def display_advanced_analytics(self):
        """Analyses avancées"""
        
        if not self.pdf_data:
            return
        
        df = pd.DataFrame(self.pdf_data)
        
        st.markdown("### 📊 ANALYTIQUES AVANCÉES")
        
        # Onglets d'analyse
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Distribution", 
            "🔍 Corrélations", 
            "📅 Évolution", 
            "☁️ Mots-clés"
        ])
        
        with tab1:
            # Histogramme des scores
            fig1 = px.histogram(
                df, 
                x='score_pertinence',
                nbins=20,
                title='Distribution des scores de pertinence',
                color_discrete_sequence=['#764ba2']
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Box plot des mentions
            fig2 = px.box(
                df,
                y='mentions_bumidom',
                title='Distribution des mentions BUMIDOM',
                points='all'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab2:
            # Scatter plot corrélations
            fig3 = px.scatter(
                df,
                x='pages',
                y='mentions_bumidom',
                size='taille_mo',
                color='score_pertinence',
                hover_name='titre',
                title='Corrélations: Pages vs Mentions',
                trendline='ols'
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            # Matrice de corrélation
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            corr_matrix = df[numeric_cols].corr()
            
            fig4 = px.imshow(
                corr_matrix,
                text_auto=True,
                title='Matrice de corrélation',
                color_continuous_scale='RdBu'
            )
            st.plotly_chart(fig4, use_container_width=True)
        
        with tab3:
            # Analyse temporelle (si dates disponibles)
            if any(df['dates_trouvees'].apply(lambda x: len(x) > 0)):
                # Extraire les années
                all_years = []
                for dates in df['dates_trouvees']:
                    for date_str in dates:
                        try:
                            year = date_str.split('/')[-1]
                            all_years.append(int(year))
                        except:
                            pass
                
                if all_years:
                    year_counts = pd.Series(all_years).value_counts().sort_index()
                    
                    fig5 = px.line(
                        x=year_counts.index,
                        y=year_counts.values,
                        title='Évolution temporelle des documents',
                        markers=True
                    )
                    fig5.update_layout(xaxis_title="Année", yaxis_title="Nombre de documents")
                    st.plotly_chart(fig5, use_container_width=True)
        
        with tab4:
            # Nuage de mots-clés
            all_keywords = []
            for keywords in df['mots_cles']:
                all_keywords.extend(keywords)
            
            if all_keywords:
                word_freq = Counter(all_keywords)
                
                # Word cloud
                wordcloud = WordCloud(
                    width=800,
                    height=400,
                    background_color='white',
                    colormap='viridis'
                ).generate_from_frequencies(word_freq)
                
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
                
                # Top mots-clés
                top_keywords = pd.DataFrame(
                    word_freq.most_common(20),
                    columns=['Mot-clé', 'Fréquence']
                )
                
                fig6 = px.bar(
                    top_keywords,
                    x='Fréquence',
                    y='Mot-clé',
                    orientation='h',
                    title='Top 20 mots-clés',
                    color='Fréquence'
                )
                st.plotly_chart(fig6, use_container_width=True)
    
    def display_ai_insights(self):
        """Insights générés par IA"""
        
        st.markdown("### 🤖 INSIGHTS IA PREMIUM")
        
        if not self.pdf_data:
            return
        
        df = pd.DataFrame(self.pdf_data)
        
        # Générer des insights automatiques
        insights = []
        
        # Insight 1: Top documents
        top_doc = df.loc[df['score_pertinence'].idxmax()]
        insights.append(f"📄 **Document le plus pertinent**: {top_doc['titre'][:60]}... (Score: {top_doc['score_pertinence']:.1f})")
        
        # Insight 2: Distribution
        avg_mentions = df['mentions_bumidom'].mean()
        insights.append(f"🔍 **Moyenne mentions BUMIDOM**: {avg_mentions:.1f} par document")
        
        # Insight 3: Corrélation
        correlation = df['pages'].corr(df['mentions_bumidom'])
        if abs(correlation) > 0.3:
            insights.append(f"📈 **Corrélation pages-mentions**: {'positive' if correlation > 0 else 'negative'} ({correlation:.2f})")
        
        # Insight 4: Mots-clés
        all_keywords = []
        for keywords in df['mots_cles']:
            all_keywords.extend(keywords)
        
        if all_keywords:
            most_common = Counter(all_keywords).most_common(1)[0]
            insights.append(f"🏷️ **Mot-clé dominant**: '{most_common[0]}' ({most_common[1]} occurrences)")
        
        # Afficher les insights
        for insight in insights:
            st.info(insight)
        
        # Recommandations
        st.markdown("#### 💡 RECOMMANDATIONS")
        
        col_rec1, col_rec2 = st.columns(2)
        
        with col_rec1:
            st.markdown("""
            **Pour approfondir:**
            1. Étudier les documents avec score > 80
            2. Analyser les débats parlementaires complets
            3. Rechercher les rapports d'enquête
            """)
        
        with col_rec2:
            st.markdown("""
            **Pour la monétisation:**
            1. Créer des rapports premium
            2. Offrir des analyses personnalisées
            3. Développer une API d'accès aux données
            """)
    
    def display_export_premium(self):
        """Section d'export premium"""
        
        st.markdown("### 💾 EXPORT PREMIUM")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            st.markdown("**📊 Données complètes**")
            
            if st.button("📥 CSV Premium", use_container_width=True):
                self.export_csv()
            
            if st.button("📈 Excel Avancé", use_container_width=True):
                self.export_excel()
        
        with col_exp2:
            st.markdown("**📄 Rapports**")
            
            if st.button("📋 Rapport d'analyse", use_container_width=True):
                self.generate_report()
            
            if st.button("📊 Dashboard PDF", use_container_width=True):
                self.export_dashboard_pdf()
        
        with col_exp3:
            st.markdown("**🔗 API & Intégration**")
            
            if st.button("🌐 JSON API", use_container_width=True):
                self.export_json()
            
            if st.button("🔄 Webhook", use_container_width=True):
                st.info("Configuration webhook disponible en version Entreprise")
    
    def save_analysis_data(self):
        """Sauvegarde les données d'analyse"""
        if self.pdf_data:
            df = pd.DataFrame(self.pdf_data)
            df.to_csv('pdf_analysis_premium.csv', index=False, encoding='utf-8-sig')
            df.to_json('pdf_analysis_premium.json', orient='records', force_ascii=False)
    
    def download_pdf(self, url, title):
        """Télécharge un PDF"""
        try:
            response = requests.get(url)
            filename = re.sub(r'[^\w\-_\. ]', '_', title[:50]) + '.pdf'
            
            st.download_button(
                label="Cliquer pour télécharger",
                data=response.content,
                file_name=filename,
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erreur téléchargement: {str(e)}")
    
    def display_pdf_preview(self, url):
        """Affiche un aperçu PDF"""
        try:
            response = requests.get(url)
            base64_pdf = base64.b64encode(response.content).decode('utf-8')
            
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except:
            st.warning("Aperçu non disponible pour ce PDF")
    
    def export_csv(self):
        """Export CSV"""
        if self.pdf_data:
            df = pd.DataFrame(self.pdf_data)
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            
            st.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name="bumidom_analysis_premium.csv",
                mime="text/csv"
            )
    
    def export_excel(self):
        """Export Excel"""
        if self.pdf_data:
            df = pd.DataFrame(self.pdf_data)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Analysis')
                
                # Ajouter des feuilles supplémentaires
                summary = df.describe()
                summary.to_excel(writer, sheet_name='Summary')
            
            output.seek(0)
            
            st.download_button(
                label="Télécharger Excel",
                data=output,
                file_name="bumidom_analysis_premium.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    def export_json(self):
        """Export JSON"""
        if self.pdf_data:
            json_str = json.dumps(self.pdf_data, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="Télécharger JSON",
                data=json_str,
                file_name="bumidom_analysis_premium.json",
                mime="application/json"
            )
    
    def generate_report(self):
        """Génère un rapport premium"""
        
        if not self.pdf_data:
            return
        
        df = pd.DataFrame(self.pdf_data)
        
        report = f"""
        RAPPORT PREMIUM D'ANALYSE BUMIDOM
        =================================
        
        Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        RÉSUMÉ EXÉCUTIF
        ---------------
        • Documents analysés: {len(df)}
        • Période couverte: Basée sur les dates extraites
        • Score moyen de pertinence: {df['score_pertinence'].mean():.1f}/100
        
        ANALYSE QUANTITATIVE
        --------------------
        1. Volume de données:
           - Pages totales: {df['pages'].sum():,}
           - Données textuelles: {df['longueur_texte'].sum() / 1000000:.1f} millions de caractères
           - Taille totale PDF: {df['taille_mo'].sum():.1f} Mo
        
        2. Répartition par score:
           - Excellent (80-100): {len(df[df['score_pertinence'] >= 80])} documents
           - Bon (60-79): {len(df[(df['score_pertinence'] >= 60) & (df['score_pertinence'] < 80)])} documents
           - Moyen (40-59): {len(df[(df['score_pertinence'] >= 40) & (df['score_pertinence'] < 60)])} documents
           - Faible (<40): {len(df[df['score_pertinence'] < 40])} documents
        
        3. Analyse thématique:
           - Mentions BUMIDOM totales: {df['mentions_bumidom'].sum():,}
           - Densité moyenne: {df['densite_bumidom'].mean():.3f} mentions/1000 mots
        
        DOCUMENTS CLÉS
        --------------
        """
        
        # Top 5 documents
        top_5 = df.nlargest(5, 'score_pertinence')
        for idx, row in top_5.iterrows():
            report += f"""
        {idx+1}. {row['titre'][:80]}...
           - Score: {row['score_pertinence']:.1f}
           - Mentions: {row['mentions_bumidom']}
           - Pages: {row['pages']}
           - Mots-clés: {', '.join(row['mots_cles'][:5])}
            """
        
        report += f"""
        
        RECOMMANDATIONS STRATÉGIQUES
        ----------------------------
        1. Prioriser l'analyse des {len(top_5)} documents top
        2. Approfondir les thèmes récurrents
        3. Établir une veille parlementaire continue
        
        MÉTHODOLOGIE
        ------------
        • Source: Archives de l'Assemblée Nationale
        • Outil: Dashboard Streamlit Premium
        • Période d'analyse: {datetime.now().strftime('%B %Y')}
        • Algorithmes: Recherche sémantique, analyse de pertinence, extraction de motifs
        
        --- FIN DU RAPPORT ---
        """
        
        st.download_button(
            label="📥 Télécharger le rapport",
            data=report,
            file_name="rapport_premium_bumidom.txt",
            mime="text/plain"
        )
    
    def export_dashboard_pdf(self):
        """Export du dashboard en PDF"""
        st.info("Fonctionnalité PDF export - Version Entreprise")
        st.markdown("""
        **Fonctionnalités PDF premium:**
        - Export des visualisations haute résolution
        - Mise en page professionnelle
        - Pieds de page et en-têtes personnalisés
        - Chiffrement et protection des documents
        """)
    
    def run_dashboard(self):
        """Exécute le dashboard complet"""
        
        # En-tête
        self.display_premium_header()
        
        # Panel de contrôle
        search_query, num_pdfs = self.display_control_panel()
        
        # Métriques
        self.display_premium_metrics()
        
        # Onglets principaux
        tab_main1, tab_main2, tab_main3, tab_main4 = st.tabs([
            "📚 Explorateur", 
            "📊 Analytiques", 
            "🤖 Insights IA", 
            "💾 Export"
        ])
        
        with tab_main1:
            self.display_pdf_explorer()
        
        with tab_main2:
            self.display_advanced_analytics()
        
        with tab_main3:
            self.display_ai_insights()
        
        with tab_main4:
            self.display_export_premium()

# Point d'entrée
if __name__ == "__main__":
    # Initialisation
    dashboard = PremiumDashboard()
    
    # Exécution
    dashboard.run_dashboard()
