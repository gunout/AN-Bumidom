import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import base64
from datetime import datetime
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re

class BUMIDOMPDFDashboard:
    def __init__(self):
        self.data = None
        self.load_data()
        self.pdf_dir = "pdf_documents"
    
    def load_data(self):
        """Charge les données analysées"""
        try:
            self.data = pd.read_csv('bumidom_pdf_analysis.csv')
            # Convertir les listes de strings en listes Python
            self.data['mots_cles_bumidom'] = self.data['mots_cles_bumidom'].apply(
                lambda x: eval(x) if isinstance(x, str) and x.startswith('[') else []
            )
        except:
            st.warning("Chargement des données de démonstration...")
            self.data = self.create_demo_data()
    
    def create_demo_data(self):
        """Crée des données de démonstration"""
        return pd.DataFrame({
            'titre': [
                'Question écrite sur le BUMIDOM - 15/03/2021',
                'Rapport sur les conséquences du BUMIDOM - 2020',
                'Audition Commission des Lois - BUMIDOM',
                'Débat parlementaire - Réparations BUMIDOM',
                'Amendement loi Mémoire BUMIDOM'
            ],
            'mentions_bumidom': [5, 12, 8, 15, 3],
            'nombre_pages': [2, 45, 28, 35, 5],
            'source': ['14ème législature', '13ème législature', 
                      'Commission Lois', 'Hémicycle', 'Texte de loi'],
            'mots_cles_bumidom': [
                ['bumidom', 'migration', 'outre-mer'],
                ['bumidom', 'victimes', 'réparation'],
                ['bumidom', 'commission', 'audition'],
                ['bumidom', 'débat', 'réparation'],
                ['bumidom', 'amendement', 'mémoire']
            ],
            'fichier_pdf': ['doc1.pdf', 'doc2.pdf', 'doc3.pdf', 'doc4.pdf', 'doc5.pdf'],
            'taille_ko': [150, 1200, 850, 950, 200]
        })
    
    def get_pdf_preview(self, filename):
        """Génère un aperçu PDF"""
        filepath = os.path.join(self.pdf_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
            return pdf_display
        return "<p>PDF non disponible</p>"
    
    def display_header(self):
        """Affiche l'en-tête"""
        st.title("📄 Dashboard BUMIDOM - Analyse de Documents PDF")
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #1e3a8a;'>Analyse des documents parlementaires PDF relatifs au BUMIDOM</h3>
        <p>Bureau pour le développement des migrations intéressant les départements d'outre-mer</p>
        </div>
        """, unsafe_allow_html=True)
    
    def display_summary_cards(self):
        """Affiche les cartes de résumé"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Documents", len(self.data))
        
        with col2:
            total_pages = self.data['nombre_pages'].sum()
            st.metric("📑 Pages totales", f"{total_pages:,}")
        
        with col3:
            total_mentions = self.data['mentions_bumidom'].sum()
            st.metric("🔍 Mentions BUMIDOM", total_mentions)
        
        with col4:
            avg_mentions = self.data['mentions_bumidom'].mean()
            st.metric("📈 Moyenne mentions", f"{avg_mentions:.1f}")
    
    def display_pdf_explorer(self):
        """Explorateur de PDF"""
        st.subheader("🔍 Explorateur de Documents PDF")
        
        tab1, tab2, tab3 = st.tabs(["📋 Liste des documents", "📊 Analyse visuelle", "🔎 Recherche avancée"])
        
        with tab1:
            self.display_document_table()
        
        with tab2:
            self.display_visual_analysis()
        
        with tab3:
            self.display_advanced_search()
    
    def display_document_table(self):
        """Affiche le tableau des documents"""
        # Sélection de colonnes à afficher
        display_cols = ['titre', 'mentions_bumidom', 'nombre_pages', 'source', 'taille_ko']
        
        if all(col in self.data.columns for col in display_cols):
            display_df = self.data[display_cols].copy()
            
            # Formater la taille
            display_df['taille_ko'] = display_df['taille_ko'].apply(lambda x: f"{x:.0f} Ko")
            
            # Afficher le tableau avec sélection
            selected_indices = st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "titre": st.column_config.TextColumn("Titre", width="large"),
                    "mentions_bumidom": st.column_config.NumberColumn("Mentions", format="%d"),
                    "nombre_pages": st.column_config.NumberColumn("Pages", format="%d"),
                    "source": st.column_config.TextColumn("Source"),
                    "taille_ko": st.column_config.TextColumn("Taille")
                }
            )
            
            # Afficher le PDF sélectionné
            if 'fichier_pdf' in self.data.columns:
                col_sel1, col_sel2 = st.columns([1, 2])
                
                with col_sel1:
                    selected_doc = st.selectbox(
                        "Sélectionner un document à visualiser:",
                        self.data['titre'].tolist()
                    )
                
                if selected_doc:
                    doc_idx = self.data[self.data['titre'] == selected_doc].index[0]
                    pdf_file = self.data.loc[doc_idx, 'fichier_pdf']
                    
                    with col_sel2:
                        st.markdown(f"**Document sélectionné:** {selected_doc}")
                        
                        if st.button("📄 Afficher le PDF", type="primary"):
                            pdf_display = self.get_pdf_preview(pdf_file)
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        
                        # Téléchargement
                        if st.button("⬇️ Télécharger le PDF"):
                            self.download_pdf(pdf_file)
    
    def download_pdf(self, filename):
        """Gère le téléchargement de PDF"""
        filepath = os.path.join(self.pdf_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                st.download_button(
                    label="Cliquer pour télécharger",
                    data=f,
                    file_name=filename,
                    mime="application/pdf"
                )
    
    def display_visual_analysis(self):
        """Affiche l'analyse visuelle"""
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            # Graphique des mentions
            fig1 = px.bar(
                self.data.sort_values('mentions_bumidom', ascending=True),
                x='mentions_bumidom',
                y='titre',
                orientation='h',
                title='Mentions BUMIDOM par document',
                color='mentions_bumidom',
                color_continuous_scale='Blues'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_v2:
            # Nuage de mots-clés
            st.subheader("☁️ Nuage de mots-clés")
            
            # Collecter tous les mots-clés
            all_keywords = []
            for keywords in self.data['mots_cles_bumidom']:
                if isinstance(keywords, list):
                    all_keywords.extend(keywords)
            
            if all_keywords:
                # Compter les occurrences
                word_freq = Counter(all_keywords)
                
                # Générer le nuage de mots
                wordcloud = WordCloud(
                    width=400,
                    height=300,
                    background_color='white',
                    colormap='Blues'
                ).generate_from_frequencies(word_freq)
                
                # Afficher
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
                
                # Liste des mots-clés fréquents
                st.caption("Mots-clés les plus fréquents:")
                for word, freq in word_freq.most_common(10):
                    st.write(f"**{word}**: {freq} occurrences")
    
    def display_advanced_search(self):
        """Recherche avancée dans les documents"""
        st.subheader("🔎 Recherche dans les documents")
        
        col_s1, col_s2 = st.columns([2, 1])
        
        with col_s1:
            search_query = st.text_input(
                "Rechercher un terme:",
                placeholder="Ex: réparation, victimes, migration..."
            )
        
        with col_s2:
            min_mentions = st.number_input(
                "Mentions BUMIDOM minimum:",
                min_value=0,
                value=1,
                step=1
            )
        
        # Filtrer les documents
        filtered_docs = self.data.copy()
        
        if search_query:
            mask = filtered_docs['titre'].str.contains(search_query, case=False, na=False)
            filtered_docs = filtered_docs[mask]
        
        if min_mentions > 0:
            filtered_docs = filtered_docs[filtered_docs['mentions_bumidom'] >= min_mentions]
        
        # Afficher les résultats
        if len(filtered_docs) > 0:
            st.success(f"{len(filtered_docs)} document(s) trouvé(s)")
            
            for idx, row in filtered_docs.iterrows():
                with st.expander(f"📄 {row['titre']}"):
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.metric("Mentions BUMIDOM", row['mentions_bumidom'])
                        st.write(f"**Pages:** {row['nombre_pages']}")
                    
                    with col_info2:
                        st.write(f"**Source:** {row['source']}")
                        st.write(f"**Taille:** {row['taille_ko']:.0f} Ko")
                    
                    # Mots-clés
                    if isinstance(row['mots_cles_bumidom'], list):
                        st.write("**Mots-clés:**", ", ".join(row['mots_cles_bumidom']))
                    
                    # Boutons d'action
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("👁️ Aperçu", key=f"preview_{idx}"):
                            if 'fichier_pdf' in row:
                                pdf_display = self.get_pdf_preview(row['fichier_pdf'])
                                st.markdown(pdf_display, unsafe_allow_html=True)
                    
                    with col_btn2:
                        if st.button("⬇️ Télécharger", key=f"dl_{idx}"):
                            if 'fichier_pdf' in row:
                                self.download_pdf(row['fichier_pdf'])
        else:
            st.warning("Aucun document ne correspond aux critères de recherche.")
    
    def display_statistics(self):
        """Affiche les statistiques détaillées"""
        st.subheader("📈 Statistiques avancées")
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            # Distribution des pages
            fig_pages = px.histogram(
                self.data,
                x='nombre_pages',
                title='Distribution du nombre de pages',
                nbins=10,
                color_discrete_sequence=['#3b82f6']
            )
            fig_pages.update_layout(height=300)
            st.plotly_chart(fig_pages, use_container_width=True)
        
        with col_stat2:
            # Relation pages-mentions
            fig_scatter = px.scatter(
                self.data,
                x='nombre_pages',
                y='mentions_bumidom',
                size='taille_ko',
                color='source',
                title='Pages vs Mentions BUMIDOM',
                hover_name='titre'
            )
            fig_scatter.update_layout(height=300)
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col_stat3:
            # Top documents
            top_docs = self.data.nlargest(5, 'mentions_bumidom')
            st.write("**Top 5 documents (mentions):**")
            for idx, row in top_docs.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                    <b>{row['titre'][:50]}...</b><br>
                    <small>Mentions: {row['mentions_bumidom']} | Pages: {row['nombre_pages']}</small>
                    </div>
                    """, unsafe_allow_html=True)
    
    def display_export_panel(self):
        """Panneau d'export"""
        st.subheader("📤 Export des données")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            # Export CSV
            if st.button("📊 Exporter les données CSV", use_container_width=True):
                csv = self.data.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="Télécharger CSV",
                    data=csv,
                    file_name="bumidom_documents_complet.csv",
                    mime="text/csv"
                )
        
        with col_exp2:
            # Export statistiques
            if st.button("📈 Générer rapport", use_container_width=True):
                self.generate_report()
        
        with col_exp3:
            # Tous les PDFs
            if st.button("📦 Tous les PDFs (ZIP)", use_container_width=True):
                self.create_zip_archive()
    
    def generate_report(self):
        """Génère un rapport statistique"""
        report = f"""
        RAPPORT D'ANALYSE BUMIDOM
        =========================
        Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        STATISTIQUES GÉNÉRALES:
        -----------------------
        • Documents analysés: {len(self.data)}
        • Pages totales: {self.data['nombre_pages'].sum():,}
        • Mentions BUMIDOM totales: {self.data['mentions_bumidom'].sum()}
        • Moyenne mentions/document: {self.data['mentions_bumidom'].mean():.1f}
        • Document avec le plus de mentions: {self.data.loc[self.data['mentions_bumidom'].idxmax(), 'titre']}
        
        DISTRIBUTION PAR SOURCE:
        ------------------------
        """
        
        if 'source' in self.data.columns:
            source_stats = self.data['source'].value_counts()
            for source, count in source_stats.items():
                report += f"• {source}: {count} documents\n"
        
        st.text_area("Rapport généré:", report, height=300)
    
    def create_zip_archive(self):
        """Crée une archive ZIP de tous les PDFs"""
        import zipfile
        
        zip_filename = "bumidom_pdfs.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for filename in os.listdir(self.pdf_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(self.pdf_dir, filename)
                    zipf.write(filepath, filename)
        
        with open(zip_filename, "rb") as f:
            st.download_button(
                "📥 Télécharger l'archive ZIP",
                data=f,
                file_name=zip_filename,
                mime="application/zip"
            )

# Configuration de l'application Streamlit
def main():
    # Configuration de la page
    st.set_page_config(
        page_title="Analyse BUMIDOM - PDF",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS personnalisé
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e3a8a;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialisation du dashboard
    dashboard = BUMIDOMPDFDashboard()
    
    # Sidebar
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Logo_Assemblee_nationale_%28France%29.svg/1200px-Logo_Assemblee_nationale_%28France%29.svg.png", 
                width=150)
        st.title("Navigation")
        
        st.markdown("---")
        
        menu_option = st.selectbox(
            "Sélectionner une section:",
            ["🏠 Vue d'ensemble", "🔍 Explorateur PDF", "📈 Statistiques", "⚙️ Export"]
        )
        
        st.markdown("---")
        
        st.markdown("### Filtres")
        if 'source' in dashboard.data.columns:
            sources = st.multiselect(
                "Filtrer par source:",
                options=dashboard.data['source'].unique(),
                default=dashboard.data['source'].unique()[:3]
            )
            if sources:
                dashboard.data = dashboard.data[dashboard.data['source'].isin(sources)]
        
        st.markdown("---")
        st.info(f"**{len(dashboard.data)} documents chargés**")
    
    # Contenu principal basé sur la sélection
    if menu_option == "🏠 Vue d'ensemble":
        dashboard.display_header()
        dashboard.display_summary_cards()
        st.markdown("---")
        
        col_main1, col_main2 = st.columns([3, 2])
        
        with col_main1:
            st.subheader("Documents récents")
            dashboard.display_document_table()
        
        with col_main2:
            st.subheader("Aperçu rapide")
            selected_doc = st.selectbox(
                "Choisir un document:",
                dashboard.data['titre'].tolist()
            )
            if selected_doc:
                doc_idx = dashboard.data[dashboard.data['titre'] == selected_doc].index[0]
                if 'fichier_pdf' in dashboard.data.columns:
                    pdf_file = dashboard.data.loc[doc_idx, 'fichier_pdf']
                    pdf_display = dashboard.get_pdf_preview(pdf_file)
                    st.markdown(pdf_display, unsafe_allow_html=True)
    
    elif menu_option == "🔍 Explorateur PDF":
        dashboard.display_header()
        dashboard.display_pdf_explorer()
    
    elif menu_option == "📈 Statistiques":
        dashboard.display_header()
        dashboard.display_summary_cards()
        dashboard.display_statistics()
    
    elif menu_option == "⚙️ Export":
        dashboard.display_header()
        dashboard.display_export_panel()

if __name__ == "__main__":
    main()
