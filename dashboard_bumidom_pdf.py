import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re
import io
import base64
from collections import Counter
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import time
import urllib.parse

# Configuration de la page
st.set_page_config(
    page_title="Analyse BUMIDOM - Archives AN",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: bold;
    }
    .section-title {
        color: #374151;
        border-left: 5px solid #3B82F6;
        padding-left: 15px;
        margin-top: 30px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    .metric-label {
        color: #6B7280;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .document-card {
        background: white;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #3B82F6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s;
    }
    .document-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .keyword-badge {
        display: inline-block;
        background: #DBEAFE;
        color: #1E40AF;
        padding: 4px 12px;
        border-radius: 20px;
        margin: 2px 5px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

class BUMIDOMAnalyzer:
    def __init__(self):
        self.base_url = "http://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        })
        self.data = None
        
    def search_bumidom_documents(self, max_results=50):
        """Recherche les documents relatifs au BUMIDOM"""
        
        # URLs cibles pour la recherche
        search_targets = [
            {"url": f"{self.base_url}/14/documents/index-dossier.asp", "legislature": "14"},
            {"url": f"{self.base_url}/13/documents/index-dossier.asp", "legislature": "13"},
            {"url": f"{self.base_url}/12/documents/index-dossier.asp", "legislature": "12"},
            {"url": f"{self.base_url}/11/documents/index-dossier.asp", "legislature": "11"},
            {"url": f"{self.base_url}/10/documents/index-dossier.asp", "legislature": "10"},
            {"url": f"{self.base_url}/9/documents/index-dossier.asp", "legislature": "9"},
            {"url": f"{self.base_url}/8/documents/index-dossier.asp", "legislature": "8"},
            {"url": f"{self.base_url}/14/debats/index.asp", "legislature": "14"},
            {"url": f"{self.base_url}/13/debats/index.asp", "legislature": "13"},
            {"url": f"{self.base_url}/12/debats/index.asp", "legislature": "12"},
        ]
        
        documents = []
        
        with st.spinner("🔍 Recherche des documents BUMIDOM..."):
            progress_bar = st.progress(0)
            
            for idx, target in enumerate(search_targets):
                try:
                    # Mise à jour de la progression
                    progress = (idx + 1) / len(search_targets)
                    progress_bar.progress(progress)
                    
                    # Récupération de la page
                    response = self.session.get(target["url"], timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Recherche de liens contenant BUMIDOM ou termes associés
                    search_terms = [
                        'bumidom', 'BUMIDOM', 'Bureau.*migration.*outre-mer',
                        'départements.*outre-mer.*migration', 'DOM.*migration',
                        'migration.*organisée.*outre-mer'
                    ]
                    
                    for term in search_terms:
                        pattern = re.compile(term, re.IGNORECASE)
                        links = soup.find_all('a', string=pattern)
                        
                        for link in links[:10]:  # Limiter par terme
                            doc_info = self.extract_document_info(link, target["legislature"])
                            if doc_info and doc_info not in documents:
                                documents.append(doc_info)
                    
                    # Recherche dans les URLs des liens
                    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    for link in pdf_links[:10]:
                        link_text = link.get_text(strip=True).lower()
                        if any(term in link_text for term in ['bumidom', 'migration', 'outre-mer', 'dom']):
                            doc_info = self.extract_document_info(link, target["legislature"])
                            if doc_info:
                                documents.append(doc_info)
                    
                    time.sleep(1)  # Respect du serveur
                    
                except Exception as e:
                    st.warning(f"Erreur avec {target['url']}: {str(e)[:100]}")
                    continue
        
        progress_bar.empty()
        return documents[:max_results]
    
    def extract_document_info(self, link_element, legislature):
        """Extrait les informations d'un document"""
        try:
            title = link_element.get_text(strip=True)
            url = link_element.get('href', '')
            
            # Compléter l'URL si nécessaire
            if url and not url.startswith('http'):
                if url.startswith('/'):
                    url = f"{self.base_url}{url}"
                else:
                    url = f"{self.base_url}/{legislature}/{url}"
            
            # Identifier le type de document
            doc_type = self.classify_document_type(title, url)
            
            # Extraire la date si présente
            date_match = re.search(r'\d{2}/\d{2}/\d{4}', title)
            date = date_match.group(0) if date_match else None
            
            # Extraire l'auteur si présent
            author_match = re.search(r'^(M\.|Mme|Mlle)\s+[\w\s\-]+', title)
            author = author_match.group(0) if author_match else None
            
            # Identifier les mots-clés
            keywords = self.extract_keywords(title)
            
            return {
                'titre': title,
                'url': url,
                'legislature': legislature,
                'type_document': doc_type,
                'date': date,
                'auteur': author,
                'mots_cles': keywords,
                'mentions_bumidom': self.count_bumidom_mentions(title),
                'date_extraction': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
        except Exception as e:
            return None
    
    def classify_document_type(self, title, url):
        """Classifie le type de document"""
        title_lower = title.lower()
        url_lower = str(url).lower()
        
        if 'question' in title_lower or 'qst' in url_lower:
            return 'Question écrite'
        elif 'débat' in title_lower or 'cri' in url_lower:
            return 'Débat parlementaire'
        elif 'rapport' in title_lower:
            return 'Rapport'
        elif 'amendement' in title_lower:
            return 'Amendement'
        elif 'loi' in title_lower:
            return 'Texte de loi'
        elif 'audition' in title_lower:
            return 'Audition'
        elif 'proposition' in title_lower:
            return 'Proposition'
        elif 'résolution' in title_lower:
            return 'Résolution'
        else:
            return 'Autre document'
    
    def extract_keywords(self, text):
        """Extrait les mots-clés pertinents"""
        text_lower = text.lower()
        keywords = []
        
        # Mots-clés liés au BUMIDOM
        bumidom_terms = [
            'bumidom', 'migration', 'outre-mer', 'dom', 'tom',
            'martinique', 'guadeloupe', 'guyane', 'réunion', 'mayotte',
            'départementalisation', 'transfert', 'population', 'émigration'
        ]
        
        # Mots-clés juridiques/politiques
        legal_terms = [
            'réparation', 'indemnisation', 'victime', 'mémoire',
            'reconnaissance', 'commission', 'enquête', 'droit',
            'justice', 'historique', 'responsabilité'
        ]
        
        for term in bumidom_terms + legal_terms:
            if term in text_lower:
                keywords.append(term)
        
        return list(set(keywords))
    
    def count_bumidom_mentions(self, text):
        """Compte les mentions de BUMIDOM"""
        text_lower = text.lower()
        return len(re.findall(r'bumidom', text_lower))
    
    def analyze_documents(self, documents):
        """Analyse les documents collectés"""
        if not documents:
            return None
        
        df = pd.DataFrame(documents)
        
        # Analyses supplémentaires
        df['annee'] = df['date'].apply(lambda x: x.split('/')[2] if x and '/' in x else None)
        
        return df
    
    def get_document_content(self, url):
        """Récupère le contenu d'un document (version simplifiée)"""
        try:
            response = self.session.get(url, timeout=10)
            
            # Si c'est un PDF
            if url.lower().endswith('.pdf'):
                return f"[PDF] {url}"
            
            # Sinon, extraire le texte HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Chercher le contenu principal
            content_selectors = [
                'div.content', 'div.texte', 'div.document',
                'div#content', 'div#texte', 'body'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0].get_text(separator='\n', strip=True)
                    break
            
            if not content:
                content = soup.get_text(separator='\n', strip=True)
            
            return content[:2000]  # Limiter pour l'affichage
            
        except Exception as e:
            return f"Erreur de récupération: {str(e)}"

def create_dashboard():
    """Crée le dashboard Streamlit"""
    
    # Initialisation
    analyzer = BUMIDOMAnalyzer()
    
    # Titre principal
    st.markdown('<h1 class="main-title">📊 ANALYSE BUMIDOM - Archives de l\'Assemblée Nationale</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Logo_Assemblee_nationale_%28France%29.svg/800px-Logo_Assemblee_nationale_%28France%29.svg.png", 
                 width=120)
        
        st.markdown("### ⚙️ Paramètres")
        
        max_docs = st.slider("Nombre maximum de documents", 10, 100, 30)
        
        search_option = st.radio(
            "Type de recherche:",
            ["Automatique (recherche BUMIDOM)", "Manuel (URLs spécifiques)"]
        )
        
        st.markdown("---")
        st.markdown("### 📅 Filtres")
        
        if st.session_state.get('df_documents') is not None:
            df = st.session_state.df_documents
            
            # Filtres interactifs
            legislatures = st.multiselect(
                "Législatures:",
                options=sorted(df['legislature'].unique()),
                default=sorted(df['legislature'].unique())[:3]
            )
            
            doc_types = st.multiselect(
                "Types de documents:",
                options=sorted(df['type_document'].unique()),
                default=sorted(df['type_document'].unique())
            )
            
            st.markdown("---")
        
        st.markdown("### ℹ️ À propos")
        st.info("""
        **BUMIDOM** : Bureau pour le développement des migrations intéressant 
        les départements d'outre-mer (1963-1982).
        
        Ce dashboard analyse les documents parlementaires relatifs au BUMIDOM 
        dans les archives de l'Assemblée Nationale.
        """)
    
    # Onglets principaux
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Tableau de bord", 
        "📄 Documents", 
        "📈 Analyses", 
        "🔍 Recherche", 
        "💾 Export"
    ])
    
    with tab1:
        display_dashboard_tab(analyzer, max_docs, search_option)
    
    with tab2:
        display_documents_tab()
    
    with tab3:
        display_analysis_tab()
    
    with tab4:
        display_search_tab(analyzer)
    
    with tab5:
        display_export_tab()

def display_dashboard_tab(analyzer, max_docs, search_option):
    """Affiche l'onglet Tableau de bord"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<h2 class="section-title">📈 Vue d\'ensemble</h2>', unsafe_allow_html=True)
        
        # Bouton de recherche
        if st.button("🔍 Lancer la recherche BUMIDOM", type="primary", use_container_width=True):
            with st.spinner("Recherche en cours..."):
                documents = analyzer.search_bumidom_documents(max_results=max_docs)
                
                if documents:
                    df = analyzer.analyze_documents(documents)
                    st.session_state.df_documents = df
                    st.success(f"✅ {len(documents)} documents trouvés")
                    
                    # Rafraîchir la page
                    st.rerun()
                else:
                    st.warning("⚠️ Aucun document trouvé. Utilisation des données de démonstration.")
                    st.session_state.df_documents = create_demo_data()
    
    with col2:
        st.markdown("### 📊 Métriques")
        
        if 'df_documents' in st.session_state:
            df = st.session_state.df_documents
            
            col_met1, col_met2 = st.columns(2)
            
            with col_met1:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Documents</div>
                </div>
                """.format(len(df)), unsafe_allow_html=True)
            
            with col_met2:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Législatures</div>
                </div>
                """.format(df['legislature'].nunique()), unsafe_allow_html=True)
            
            col_met3, col_met4 = st.columns(2)
            
            with col_met3:
                total_mentions = df['mentions_bumidom'].sum()
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Mentions</div>
                </div>
                """.format(total_mentions), unsafe_allow_html=True)
            
            with col_met4:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Types</div>
                </div>
                """.format(df['type_document'].nunique()), unsafe_allow_html=True)
    
    # Si des données existent, afficher les visualisations
    if 'df_documents' in st.session_state:
        df = st.session_state.df_documents
        
        # Graphiques
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Répartition par législature
            leg_counts = df['legislature'].value_counts().reset_index()
            leg_counts.columns = ['Législature', 'Nombre']
            
            fig1 = px.bar(
                leg_counts,
                x='Législature',
                y='Nombre',
                title='📊 Documents par législature',
                color='Nombre',
                color_continuous_scale='Blues'
            )
            fig1.update_layout(height=300)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_chart2:
            # Répartition par type
            type_counts = df['type_document'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Nombre']
            
            fig2 = px.pie(
                type_counts,
                values='Nombre',
                names='Type',
                title='📄 Répartition par type',
                hole=0.4
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Timeline
        st.markdown('<h3 class="section-title">📅 Chronologie des documents</h3>', unsafe_allow_html=True)
        
        if 'date' in df.columns and df['date'].notna().any():
            # Créer une timeline
            timeline_data = df.copy()
            timeline_data['date_dt'] = pd.to_datetime(timeline_data['date'], format='%d/%m/%Y', errors='coerce')
            timeline_data = timeline_data.dropna(subset=['date_dt'])
            
            if not timeline_data.empty:
                timeline_data = timeline_data.sort_values('date_dt')
                
                fig3 = px.scatter(
                    timeline_data,
                    x='date_dt',
                    y='type_document',
                    color='legislature',
                    size='mentions_bumidom',
                    hover_data=['titre'],
                    title='Évolution temporelle des documents',
                    labels={'date_dt': 'Date', 'type_document': 'Type'}
                )
                fig3.update_layout(height=400, xaxis_title="Date", yaxis_title="Type de document")
                st.plotly_chart(fig3, use_container_width=True)
        
        # Top documents
        st.markdown('<h3 class="section-title">🏆 Top documents BUMIDOM</h3>', unsafe_allow_html=True)
        
        top_docs = df.nlargest(5, 'mentions_bumidom')
        
        for idx, row in top_docs.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="document-card">
                    <h4>{row['titre'][:80]}...</h4>
                    <p><strong>Législature:</strong> {row['legislature']} | 
                    <strong>Type:</strong> {row['type_document']} | 
                    <strong>Mentions:</strong> {row['mentions_bumidom']}</p>
                    <p><strong>Date:</strong> {row['date'] if row['date'] else 'Non spécifiée'}</p>
                    <div>
                        {' '.join([f'<span class="keyword-badge">{kw}</span>' for kw in row['mots_cles'][:5]])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

def display_documents_tab():
    """Affiche l'onglet Documents"""
    
    st.markdown('<h2 class="section-title">📄 Documents BUMIDOM</h2>', unsafe_allow_html=True)
    
    if 'df_documents' not in st.session_state:
        st.info("Veuillez d'abord lancer une recherche dans l'onglet Tableau de bord.")
        return
    
    df = st.session_state.df_documents
    
    # Filtres avancés
    col_filt1, col_filt2, col_filt3 = st.columns(3)
    
    with col_filt1:
        search_query = st.text_input("🔎 Rechercher dans les titres:", placeholder="BUMIDOM, migration, outre-mer...")
    
    with col_filt2:
        min_mentions = st.number_input("Mentions minimum:", min_value=0, value=1, step=1)
    
    with col_filt3:
        sort_by = st.selectbox("Trier par:", ["Mentions (desc)", "Date récente", "Législature"])
    
    # Appliquer les filtres
    filtered_df = df.copy()
    
    if search_query:
        filtered_df = filtered_df[filtered_df['titre'].str.contains(search_query, case=False, na=False)]
    
    filtered_df = filtered_df[filtered_df['mentions_bumidom'] >= min_mentions]
    
    # Trier
    if sort_by == "Mentions (desc)":
        filtered_df = filtered_df.sort_values('mentions_bumidom', ascending=False)
    elif sort_by == "Date récente":
        filtered_df = filtered_df.sort_values('date', ascending=False)
    elif sort_by == "Législature":
        filtered_df = filtered_df.sort_values('legislature', ascending=False)
    
    # Afficher les documents
    st.info(f"📊 {len(filtered_df)} document(s) trouvé(s)")
    
    for idx, row in filtered_df.iterrows():
        with st.expander(f"{row['titre'][:100]}...", expanded=False):
            col_doc1, col_doc2 = st.columns([3, 1])
            
            with col_doc1:
                st.markdown(f"**📋 Titre complet:** {row['titre']}")
                
                col_meta1, col_meta2, col_meta3 = st.columns(3)
                with col_meta1:
                    st.metric("📅 Législature", row['legislature'])
                with col_meta2:
                    st.metric("📄 Type", row['type_document'])
                with col_meta3:
                    st.metric("🔍 Mentions", row['mentions_bumidom'])
                
                st.markdown(f"**📅 Date:** {row['date'] if row['date'] else 'Non spécifiée'}")
                
                if row['auteur']:
                    st.markdown(f"**✍️ Auteur:** {row['auteur']}")
                
                # Mots-clés
                if row['mots_cles']:
                    st.markdown("**🏷️ Mots-clés:**")
                    keywords_html = " ".join([f'<span class="keyword-badge">{kw}</span>' for kw in row['mots_cles']])
                    st.markdown(f"<div style='margin: 10px 0;'>{keywords_html}</div>", unsafe_allow_html=True)
            
            with col_doc2:
                st.markdown("**🔗 Actions**")
                
                if st.button("🌐 Ouvrir", key=f"open_{idx}", use_container_width=True):
                    st.markdown(f'<a href="{row["url"]}" target="_blank">Ouvrir le document</a>', unsafe_allow_html=True)
                
                if st.button("📋 Copier URL", key=f"copy_{idx}", use_container_width=True):
                    st.code(row['url'], language=None)
                
                # Prévisualisation (simplifiée)
                if st.button("👁️ Prévisualiser", key=f"preview_{idx}", use_container_width=True):
                    with st.spinner("Chargement..."):
                        # Ici, on pourrait implémenter une vraie prévisualisation
                        st.info("Prévisualisation disponible pour les documents HTML. Les PDF nécessitent un affichage externe.")

def display_analysis_tab():
    """Affiche l'onglet Analyses"""
    
    st.markdown('<h2 class="section-title">📈 Analyses avancées</h2>', unsafe_allow_html=True)
    
    if 'df_documents' not in st.session_state:
        st.info("Veuillez d'abord lancer une recherche dans l'onglet Tableau de bord.")
        return
    
    df = st.session_state.df_documents
    
    # Statistiques détaillées
    col_ana1, col_ana2 = st.columns(2)
    
    with col_ana1:
        st.subheader("📊 Distribution des mentions")
        
        fig_hist = px.histogram(
            df,
            x='mentions_bumidom',
            nbins=20,
            title='Distribution des mentions BUMIDOM',
            color_discrete_sequence=['#3B82F6']
        )
        fig_hist.update_layout(height=300, xaxis_title="Nombre de mentions", yaxis_title="Nombre de documents")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Statistiques descriptives
        st.subheader("📝 Statistiques descriptives")
        
        stats_df = pd.DataFrame({
            'Métrique': ['Moyenne', 'Médiane', 'Maximum', 'Minimum', 'Écart-type'],
            'Valeur': [
                df['mentions_bumidom'].mean(),
                df['mentions_bumidom'].median(),
                df['mentions_bumidom'].max(),
                df['mentions_bumidom'].min(),
                df['mentions_bumidom'].std()
            ]
        })
        
        stats_df['Valeur'] = stats_df['Valeur'].round(2)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    with col_ana2:
        st.subheader("📈 Évolution temporelle")
        
        if 'date' in df.columns and df['date'].notna().any():
            # Grouper par année
            df['annee'] = df['date'].apply(lambda x: x.split('/')[2] if x and '/' in x else None)
            yearly_data = df.dropna(subset=['annee']).groupby('annee').agg({
                'mentions_bumidom': 'sum',
                'titre': 'count'
            }).reset_index()
            
            yearly_data.columns = ['Année', 'Total mentions', 'Nombre documents']
            
            fig_line = px.line(
                yearly_data,
                x='Année',
                y='Total mentions',
                markers=True,
                title='Évolution des mentions BUMIDOM par année',
                line_shape='spline'
            )
            fig_line.update_layout(height=300)
            st.plotly_chart(fig_line, use_container_width=True)
        
        # Nuage de mots-clés
        st.subheader("☁️ Nuage de mots-clés")
        
        # Collecter tous les mots-clés
        all_keywords = []
        for keywords in df['mots_cles']:
            if isinstance(keywords, list):
                all_keywords.extend(keywords)
        
        if all_keywords:
            word_freq = Counter(all_keywords)
            
            # Générer le nuage de mots
            wordcloud = WordCloud(
                width=400,
                height=300,
                background_color='white',
                colormap='Blues_r',
                max_words=50
            ).generate_from_frequencies(word_freq)
            
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
            
            # Top 10 mots-clés
            top_keywords = pd.DataFrame(
                word_freq.most_common(10),
                columns=['Mot-clé', 'Fréquence']
            )
            
            st.dataframe(top_keywords, use_container_width=True, hide_index=True)
    
    # Analyse par législature
    st.markdown('<h3 class="section-title">📊 Analyse par législature</h3>', unsafe_allow_html=True)
    
    legislature_analysis = df.groupby('legislature').agg({
        'titre': 'count',
        'mentions_bumidom': ['sum', 'mean', 'max']
    }).round(2)
    
    legislature_analysis.columns = ['Documents', 'Mentions totales', 'Moyenne mentions', 'Max mentions']
    legislature_analysis = legislature_analysis.sort_values('Mentions totales', ascending=False)
    
    st.dataframe(legislature_analysis, use_container_width=True)
    
    # Graphique comparatif
    fig_comp = px.bar(
        legislature_analysis.reset_index(),
        x='legislature',
        y='Mentions totales',
        title='Mentions BUMIDOM par législature',
        color='Documents',
        color_continuous_scale='Viridis'
    )
    fig_comp.update_layout(height=400)
    st.plotly_chart(fig_comp, use_container_width=True)

def display_search_tab(analyzer):
    """Affiche l'onglet Recherche"""
    
    st.markdown('<h2 class="section-title">🔍 Recherche avancée</h2>', unsafe_allow_html=True)
    
    col_search1, col_search2 = st.columns([2, 1])
    
    with col_search1:
        st.subheader("Recherche par critères")
        
        search_criteria = st.text_area(
            "Termes de recherche (un par ligne):",
            value="bumidom\nmigration outre-mer\ndépartements d'outre-mer\nDOM\nréparation",
            height=150
        )
        
        search_terms = [term.strip() for term in search_criteria.split('\n') if term.strip()]
        
        col_search3, col_search4, col_search5 = st.columns(3)
        
        with col_search3:
            search_type = st.selectbox(
                "Type de recherche:",
                ["Titre seulement", "Titre et contenu", "URLs uniquement"]
            )
        
        with col_search4:
            min_length = st.number_input("Longueur min. titre:", min_value=0, value=10, step=5)
        
        with col_search5:
            exact_match = st.checkbox("Correspondance exacte")
    
    with col_search2:
        st.subheader("Paramètres")
        
        st.markdown("**📁 Sources:**")
        st.checkbox("Archives AN", value=True)
        st.checkbox("Questions écrites", value=True)
        st.checkbox("Débats", value=True)
        st.checkbox("Rapports", value=True)
        
        st.markdown("---")
        
        if st.button("🚀 Lancer la recherche", type="primary", use_container_width=True):
            # Ici, on pourrait implémenter une recherche plus sophistiquée
            st.info("Recherche avancée en cours de développement...")
    
    # Résultats de recherche simulés
    st.markdown("---")
    st.subheader("📋 Résultats de recherche")
    
    # Exemples de résultats
    example_results = [
        {
            "titre": "Question écrite n° 12345 sur les conséquences du BUMIDOM",
            "score": 95,
            "type": "Question écrite",
            "legislature": "14",
            "date": "15/03/2021",
            "matching_terms": ["bumidom", "conséquences"]
        },
        {
            "titre": "Débat sur la réparation des victimes du BUMIDOM",
            "score": 88,
            "type": "Débat parlementaire",
            "legislature": "13",
            "date": "22/06/2020",
            "matching_terms": ["bumidom", "réparation", "victimes"]
        },
        {
            "titre": "Rapport de la commission d'enquête sur le BUMIDOM",
            "score": 92,
            "type": "Rapport",
            "legislature": "12",
            "date": "10/11/2019",
            "matching_terms": ["bumidom", "commission", "enquête"]
        }
    ]
    
    for result in example_results:
        with st.expander(f"🔍 {result['titre']} (Score: {result['score']}%)"):
            col_res1, col_res2 = st.columns([3, 1])
            
            with col_res1:
                st.markdown(f"**Type:** {result['type']} | **Législature:** {result['legislature']} | **Date:** {result['date']}")
                st.markdown(f"**Termes correspondants:** {', '.join(result['matching_terms'])}")
            
            with col_res2:
                if st.button("📋 Détails", key=f"detail_{result['titre'][:20]}"):
                    st.info("Détails du document...")

def display_export_tab():
    """Affiche l'onglet Export"""
    
    st.markdown('<h2 class="section-title">💾 Export des données</h2>', unsafe_allow_html=True)
    
    if 'df_documents' not in st.session_state:
        st.info("Veuillez d'abord lancer une recherche dans l'onglet Tableau de bord.")
        return
    
    df = st.session_state.df_documents
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        st.subheader("📊 Export des données")
        
        # Format d'export
        export_format = st.radio(
            "Format d'export:",
            ["CSV (Excel)", "JSON", "Excel (XLSX)", "HTML"]
        )
        
        # Colonnes à exporter
        all_columns = df.columns.tolist()
        selected_columns = st.multiselect(
            "Colonnes à exporter:",
            all_columns,
            default=['titre', 'legislature', 'type_document', 'date', 'mentions_bumidom', 'mots_cles']
        )
        
        # Filtrer les données
        export_df = df[selected_columns] if selected_columns else df
        
        # Bouton d'export
        if st.button("📥 Exporter les données", type="primary", use_container_width=True):
            if export_format == "CSV (Excel)":
                csv = export_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="Télécharger CSV",
                    data=csv,
                    file_name="bumidom_documents.csv",
                    mime="text/csv"
                )
            
            elif export_format == "JSON":
                json_str = export_df.to_json(orient='records', force_ascii=False, indent=2)
                st.download_button(
                    label="Télécharger JSON",
                    data=json_str,
                    file_name="bumidom_documents.json",
                    mime="application/json"
                )
            
            elif export_format == "Excel (XLSX)":
                # Pour Excel, on utilise un buffer
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='BUMIDOM')
                output.seek(0)
                
                st.download_button(
                    label="Télécharger Excel",
                    data=output,
                    file_name="bumidom_documents.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            elif export_format == "HTML":
                html_str = export_df.to_html(index=False, classes='table table-striped')
                st.download_button(
                    label="Télécharger HTML",
                    data=html_str,
                    file_name="bumidom_documents.html",
                    mime="text/html"
                )
    
    with col_exp2:
        st.subheader("📈 Rapports d'analyse")
        
        # Types de rapports
        report_type = st.selectbox(
            "Type de rapport:",
            ["Rapport statistique", "Synthèse analytique", "Chronologie", "Fiches documentaires"]
        )
        
        # Options du rapport
        if report_type == "Rapport statistique":
            st.checkbox("Inclure les graphiques", value=True)
            st.checkbox("Inclure les statistiques descriptives", value=True)
            st.checkbox("Inclure l'analyse par législature", value=True)
        
        elif report_type == "Synthèse analytique":
            st.checkbox("Analyse thématique", value=True)
            st.checkbox("Évolution temporelle", value=True)
            st.checkbox("Recommandations", value=True)
        
        # Générer le rapport
        if st.button("📄 Générer le rapport", use_container_width=True):
            with st.spinner("Génération du rapport..."):
                # Ici, on générerait le rapport
                report_content = generate_sample_report(df, report_type)
                
                st.text_area("📋 Aperçu du rapport:", report_content, height=300)
                
                # Option de téléchargement
                st.download_button(
                    label="📥 Télécharger le rapport",
                    data=report_content,
                    file_name=f"rapport_bumidom_{report_type.lower().replace(' ', '_')}.txt",
                    mime="text/plain"
                )
        
        st.markdown("---")
        st.subheader("🔗 Liens utiles")
        
        st.markdown("""
        - [Archives de l'Assemblée Nationale](http://archives.assemblee-nationale.fr)
        - [Site officiel de l'AN](https://www.assemblee-nationale.fr)
        - [Base Sycomore (députés)](http://www.assemblee-nationale.fr/sycomore)
        - [Histoire de l'AN](http://www.assemblee-nationale.fr/histoire/)
        """)

def generate_sample_report(df, report_type):
    """Génère un rapport d'exemple"""
    
    if report_type == "Rapport statistique":
        return f"""
        RAPPORT STATISTIQUE - ANALYSE BUMIDOM
        =====================================
        
        Données analysées:
        - Nombre de documents: {len(df)}
        - Période couverte: {df['date'].min() if 'date' in df.columns else 'N/A'} à {df['date'].max() if 'date' in df.columns else 'N/A'}
        - Législatures couvertes: {', '.join(sorted(df['legislature'].unique()))}
        
        Statistiques principales:
        - Mentions totales BUMIDOM: {df['mentions_bumidom'].sum()}
        - Moyenne mentions par document: {df['mentions_bumidom'].mean():.2f}
        - Maximum mentions: {df['mentions_bumidom'].max()}
        
        Répartition par type de document:
        {df['type_document'].value_counts().to_string()}
        
        Répartition par législature:
        {df['legislature'].value_counts().sort_index().to_string()}
        
        Top 5 documents par mentions:
        {df.nlargest(5, 'mentions_bumidom')[['titre', 'mentions_bumidom', 'legislature']].to_string(index=False)}
        
        Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
    
    elif report_type == "Synthèse analytique":
        return f"""
        SYNTHÈSE ANALYTIQUE - BUMIDOM
        ==============================
        
        Analyse thématique:
        - Documents analysés: {len(df)}
        - Principaux thèmes identifiés:
          * Migration organisée
          * Réparation et indemnisation
          * Mémoire historique
          * Responsabilité étatique
        
        Évolution temporelle:
        - Première mention identifiée: {df['date'].min() if 'date' in df.columns else 'N/A'}
        - Dernière mention identifiée: {df['date'].max() if 'date' in df.columns else 'N/A'}
        - Pic d'activité parlementaire: À déterminer
        
        Analyse par législature:
        - Législature la plus active: {df.groupby('legislature')['mentions_bumidom'].sum().idxmax() if not df.empty else 'N/A'}
        - Évolution des préoccupations: Analyse en cours
        
        Recommandations:
        1. Approfondir la recherche dans les législatures {', '.join(sorted(df['legislature'].unique())[-3:])}
        2. Analyser spécifiquement les questions écrites
        3. Étudier les débats parlementaires complets
        4. Rechercher les documents d'archive non numérisés
        
        Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
    
    else:
        return "Rapport en cours de génération..."

def create_demo_data():
    """Crée des données de démonstration"""
    return pd.DataFrame({
        'titre': [
            'Question écrite n° 12345 sur le BUMIDOM et ses conséquences',
            'Débat parlementaire sur la réparation des victimes du BUMIDOM',
            'Rapport de la commission d\'enquête sur le BUMIDOM',
            'Question orale concernant le BUMIDOM',
            'Amendement n° 456 sur la reconnaissance du BUMIDOM',
            'Audition sur les migrations organisées vers l\'outre-mer',
            'Proposition de résolution relative au BUMIDOM',
            'Rapport d\'information sur le BUMIDOM',
            'Question écrite n° 67890 sur l\'indemnisation BUMIDOM',
            'Débat : Mémoire et réparation du BUMIDOM'
        ],
        'legislature': ['14', '14', '13', '13', '12', '12', '11', '11', '10', '10'],
        'type_document': ['Question écrite', 'Débat parlementaire', 'Rapport', 
                         'Question orale', 'Amendement', 'Audition', 
                         'Proposition', 'Rapport', 'Question écrite', 'Débat parlementaire'],
        'date': ['15/03/2021', '22/06/2020', '10/11/2019', '05/04/2018', 
                '18/09/2017', '30/01/2016', '12/07/2015', '08/12/2013', 
                '25/03/2012', '14/05/2011'],
        'mentions_bumidom': [5, 12, 8, 3, 2, 6, 4, 7, 5, 10],
        'mots_cles': [
            ['bumidom', 'migration', 'conséquences'],
            ['bumidom', 'réparation', 'victimes'],
            ['bumidom', 'commission', 'enquête'],
            ['bumidom', 'question', 'orale'],
            ['bumidom', 'amendement', 'reconnaissance'],
            ['migration', 'outre-mer', 'organisée'],
            ['bumidom', 'résolution', 'proposition'],
            ['bumidom', 'information', 'rapport'],
            ['bumidom', 'indemnisation', 'question'],
            ['bumidom', 'mémoire', 'réparation']
        ],
        'auteur': ['M. DUPONT', 'Mme MARTIN', None, 'M. DURAND', 
                  'Groupe Socialiste', None, 'M. LEROY', None, 'Mme PETIT', 'M. DUBOIS'],
        'url': ['http://example.com/doc1', 'http://example.com/doc2', 
               'http://example.com/doc3', 'http://example.com/doc4',
               'http://example.com/doc5', 'http://example.com/doc6',
               'http://example.com/doc7', 'http://example.com/doc8',
               'http://example.com/doc9', 'http://example.com/doc10']
    })

# Point d'entrée principal
if __name__ == "__main__":
    # Initialisation des données de session
    if 'df_documents' not in st.session_state:
        st.session_state.df_documents = create_demo_data()
    
    # Lancement du dashboard
    create_dashboard()
