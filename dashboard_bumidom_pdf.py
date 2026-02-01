import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import StringIO, BytesIO
import json
import html

# Configuration de la page
st.set_page_config(
    page_title="Archives AN - Dashboard 10 pages",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titre principal
st.title("📚 Dashboard Archives AN - 10 Pages de Résultats")
st.markdown("**Extraction et analyse des 10 pages de résultats Google CSE**")

# ==================== FONCTIONS D'EXTRACTION ====================

def parse_google_cse_html(html_content, page_number=1):
    """
    Parse le HTML de la Google CSE et extrait les résultats
    """
    results = []
    
    # Diviser le HTML en résultats individuels
    # Chaque résultat commence par <div class="gsc-webResult gsc-result">
    result_blocks = html_content.split('<div class="gsc-webResult gsc-result">')
    
    # Le premier élément est l'en-tête, on le saute
    for i, block in enumerate(result_blocks[1:], 1):
        try:
            # Titre
            title_match = re.search(r'<a[^>]*class="gs-title"[^>]*>(.*?)</a>', block, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                title = html.unescape(title)
            else:
                title = f"Document {i} - Page {page_number}"
            
            # URL (data-ctorig est l'URL directe)
            url_match = re.search(r'data-ctorig="([^"]+)"', block)
            url = url_match.group(1) if url_match else ""
            
            # URL visible
            visible_url_match = re.search(r'<div class="gs-visibleUrl[^"]*"[^>]*>([^<]+)</div>', block)
            visible_url = visible_url_match.group(1).strip() if visible_url_match else ""
            
            # Description/snippet
            snippet_match = re.search(r'<div class="gs-bidi-start-align gs-snippet"[^>]*>(.*?)</div>', block, re.DOTALL)
            if snippet_match:
                snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                snippet = html.unescape(snippet)
            else:
                snippet = ""
            
            # Format du fichier
            format_match = re.search(r'<span class="gs-fileFormatType">([^<]+)</span>', block)
            file_format = format_match.group(1).strip() if format_match else "PDF"
            
            # Extraire les années depuis l'URL
            years = extract_years_from_url(url)
            
            # Extraire la législature
            legislature = extract_legislature(title, url)
            
            # Type de document
            doc_type = classify_document_type(title, snippet)
            
            # Score de pertinence (basé sur la position)
            relevance_score = 100 - ((page_number - 1) * 10 + i - 1) * 2
            
            results.append({
                'id': f"P{page_number:02d}R{i:02d}",
                'titre': title,
                'url_pdf': url,
                'url_affichage': visible_url,
                'description': snippet,
                'format': file_format,
                'annee_debut': years.get('debut', ''),
                'annee_fin': years.get('fin', ''),
                'periode': years.get('periode', ''),
                'legislature': legislature,
                'type_document': doc_type,
                'page': page_number,
                'position_page': i,
                'score_pertinence': relevance_score,
                'date_extraction': datetime.now().isoformat(),
                'est_pdf': '.pdf' in url.lower()
            })
            
        except Exception as e:
            st.warning(f"Erreur résultat {i} page {page_number}: {e}")
            continue
    
    return results

def extract_years_from_url(url):
    """Extrait les années depuis l'URL du PDF"""
    try:
        # Pattern: /4/cri/1971-1972-ordinaire1/024.pdf
        match = re.search(r'/(\d{4})-(\d{4})', url)
        if match:
            return {
                'debut': match.group(1),
                'fin': match.group(2),
                'periode': f"{match.group(1)}-{match.group(2)}"
            }
        
        # Autres patterns possibles
        match2 = re.search(r'/(\d{4})[/\.]', url)
        if match2:
            year = match2.group(1)
            return {
                'debut': year,
                'fin': year,
                'periode': year
            }
            
    except:
        pass
    
    return {'debut': '', 'fin': '', 'periode': 'Inconnue'}

def extract_legislature(title, url):
    """Extrait le numéro de législature"""
    try:
        # Depuis l'URL: /4/cri/...
        match = re.search(r'^/(\d+)/cri', url)
        if match:
            return match.group(1)
        
        # Depuis le titre: "4° Législature" ou "4' Législature"
        match2 = re.search(r'(\d+)[°\']\s*[Ll]égislature', title)
        if match2:
            return match2.group(1)
            
    except:
        pass
    
    return ""

def classify_document_type(title, snippet):
    """Classifie le type de document"""
    title_lower = title.lower()
    snippet_lower = snippet.lower()
    
    if 'compte rendu' in title_lower or 'cri' in snippet_lower:
        return 'Compte rendu'
    elif 'journal officiel' in title_lower:
        return 'Journal Officiel'
    elif 'constitution' in title_lower:
        return 'Constitution'
    elif 'débat' in snippet_lower:
        return 'Débat parlementaire'
    elif 'question' in snippet_lower:
        return 'Question parlementaire'
    elif 'budget' in snippet_lower:
        return 'Budget'
    else:
        return 'Document PDF'

def extract_all_10_pages(html_pages):
    """
    Extrait les résultats des 10 pages
    html_pages: dict avec {page_num: html_content}
    """
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page_num in range(1, 11):
        status_text.text(f"📄 Traitement page {page_num}/10...")
        
        if page_num in html_pages:
            html_content = html_pages[page_num]
            page_results = parse_google_cse_html(html_content, page_num)
            all_results.extend(page_results)
            
            st.success(f"✅ Page {page_num}: {len(page_results)} résultats extraits")
        else:
            st.warning(f"⚠️ Page {page_num}: HTML non disponible")
        
        # Mise à jour progression
        progress_bar.progress(page_num / 10)
    
    progress_bar.empty()
    status_text.empty()
    
    return all_results

# ==================== INTERFACE STREAMLIT ====================

# Initialisation session state
if 'all_results' not in st.session_state:
    st.session_state.all_results = None
if 'html_pages' not in st.session_state:
    st.session_state.html_pages = {}

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.markdown("### 📋 Pages de résultats")
    
    # Interface pour coller le HTML de chaque page
    uploaded_files = st.file_uploader(
        "Téléversez des fichiers HTML",
        type=['html', 'txt'],
        accept_multiple_files=True,
        help="Téléversez les 10 fichiers HTML des pages de résultats"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            content = uploaded_file.getvalue().decode('utf-8')
            # Essayer de détecter le numéro de page
            page_match = re.search(r'gsc-cursor-current-page[^>]*>(\d+)<', content)
            if page_match:
                page_num = int(page_match.group(1))
                st.session_state.html_pages[page_num] = content
                st.success(f"Page {page_num} chargée")
            else:
                # Si on ne peut pas détecter, utiliser l'ordre d'upload
                next_page = max(st.session_state.html_pages.keys(), default=0) + 1
                st.session_state.html_pages[next_page] = content
                st.success(f"Page {next_page} ajoutée")
    
    st.divider()
    
    # Bouton pour extraire toutes les pages
    if st.button("🚀 Extraire les 10 pages", type="primary", use_container_width=True):
        if len(st.session_state.html_pages) >= 10:
            with st.spinner("Extraction des 10 pages en cours..."):
                results = extract_all_10_pages(st.session_state.html_pages)
                st.session_state.all_results = results
                st.success(f"✅ {len(results)} résultats extraits sur 10 pages")
        else:
            st.error(f"❌ Il manque des pages. Actuellement: {len(st.session_state.html_pages)}/10")
    
    st.divider()
    
    # Statistiques rapides
    if st.session_state.all_results:
        st.header("📊 Statistiques")
        total = len(st.session_state.all_results)
        pdf_count = sum(1 for r in st.session_state.all_results if r['est_pdf'])
        st.metric("Total résultats", total)
        st.metric("Documents PDF", pdf_count)
        st.metric("Pages traitées", len(st.session_state.html_pages))

# Contenu principal
if st.session_state.all_results:
    data = st.session_state.all_results
    df = pd.DataFrame(data)
    
    # ==================== VUE D'ENSEMBLE ====================
    st.header("📈 Vue d'ensemble - 10 Pages")
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total documents", len(df))
    with col2:
        years = df[df['periode'] != 'Inconnue']['periode'].nunique()
        st.metric("Périodes différentes", years)
    with col3:
        legislatures = df[df['legislature'] != '']['legislature'].nunique()
        st.metric("Législatures", legislatures)
    with col4:
        pdf_percent = (df['est_pdf'].sum() / len(df)) * 100
        st.metric("Pourcentage PDF", f"{pdf_percent:.1f}%")
    
    # ==================== TABLEAU DES RÉSULTATS ====================
    st.header("📄 Tous les résultats (10 pages)")
    
    # Filtres
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtre par page
            pages = sorted(df['page'].unique())
            selected_pages = st.multiselect("Pages", pages, default=pages)
        
        with col2:
            # Filtre par période
            periods = sorted(df['periode'].unique())
            selected_periods = st.multiselect("Périodes", periods, default=periods)
        
        with col3:
            # Filtre par type
            types = sorted(df['type_document'].unique())
            selected_types = st.multiselect("Types", types, default=types)
    
    # Appliquer les filtres
    filtered_df = df[
        (df['page'].isin(selected_pages)) &
        (df['periode'].isin(selected_periods)) &
        (df['type_document'].isin(selected_types))
    ]
    
    # Afficher le tableau
    st.dataframe(
        filtered_df[[
            'id', 'titre', 'page', 'periode', 'legislature', 
            'type_document', 'format', 'score_pertinence'
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "page": st.column_config.NumberColumn("Page", format="%d"),
            "periode": st.column_config.TextColumn("Période"),
            "legislature": st.column_config.TextColumn("Législature"),
            "type_document": st.column_config.TextColumn("Type"),
            "format": st.column_config.TextColumn("Format"),
            "score_pertinence": st.column_config.NumberColumn("Pertinence", format="%d")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.header("📊 Analyses visuelles")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Chronologie", "📊 Répartition", "📈 Pages", "🏛️ Législatures"])
    
    with tab1:
        # Graphique par période
        if not filtered_df.empty and 'periode' in filtered_df.columns:
            period_counts = filtered_df['periode'].value_counts().sort_index()
            fig = px.bar(
                x=period_counts.index,
                y=period_counts.values,
                title="Documents par période historique",
                labels={'x': 'Période', 'y': 'Nombre de documents'},
                color=period_counts.values,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Graphique par type de document
        if not filtered_df.empty and 'type_document' in filtered_df.columns:
            type_counts = filtered_df['type_document'].value_counts()
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Répartition par type de document",
                hole=0.3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Graphique par page
        if not filtered_df.empty and 'page' in filtered_df.columns:
            page_counts = filtered_df['page'].value_counts().sort_index()
            fig = px.line(
                x=page_counts.index,
                y=page_counts.values,
                title="Distribution des résultats par page",
                labels={'x': 'Numéro de page', 'y': 'Nombre de résultats'},
                markers=True,
                line_shape='spline'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Afficher aussi en barres
            fig2 = px.bar(
                x=page_counts.index,
                y=page_counts.values,
                title="Résultats par page (détail)",
                labels={'x': 'Page', 'y': 'Nombre'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab4:
        # Graphique par législature
        if not filtered_df.empty and 'legislature' in filtered_df.columns:
            leg_df = filtered_df[filtered_df['legislature'] != '']
            if not leg_df.empty:
                leg_counts = leg_df['legislature'].value_counts().sort_index()
                fig = px.bar(
                    x=leg_counts.index,
                    y=leg_counts.values,
                    title="Documents par législature",
                    labels={'x': 'Législature', 'y': 'Nombre de documents'},
                    color=leg_counts.values,
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune information de législature disponible")
    
    # ==================== DÉTAILS DES DOCUMENTS ====================
    st.header("🔍 Détails des documents")
    
    # Groupement par page pour l'affichage
    for page_num in sorted(filtered_df['page'].unique()):
        page_docs = filtered_df[filtered_df['page'] == page_num]
        
        with st.expander(f"📖 Page {page_num} - {len(page_docs)} documents", expanded=(page_num == 1)):
            for _, doc in page_docs.iterrows():
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**{doc['titre']}**")
                        st.caption(f"📅 Période: {doc['periode']} | 🏛️ Législature: {doc['legislature']} | 📄 Format: {doc['format']}")
                        if doc['description']:
                            st.info(doc['description'][:300] + ("..." if len(doc['description']) > 300 else ""))
                    
                    with col2:
                        # Bouton pour accéder au PDF
                        if doc['url_pdf']:
                            pdf_url = doc['url_pdf']
                            st.markdown(f"""
                            <a href="{pdf_url}" target="_blank">
                                <button style="
                                    background-color: #4CAF50;
                                    color: white;
                                    padding: 8px 16px;
                                    border: none;
                                    border-radius: 4px;
                                    cursor: pointer;
                                    width: 100%;
                                ">
                                    📄 Ouvrir PDF
                                </button>
                            </a>
                            """, unsafe_allow_html=True)
                        
                        # Score de pertinence
                        st.metric("Pertinence", f"{doc['score_pertinence']}/100")
                    
                    st.divider()
    
    # ==================== EXPORT DES DONNÉES ====================
    st.header("💾 Export des données")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 CSV complet",
            data=csv,
            file_name=f"archives_10_pages_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON
        json_data = df.to_json(orient='records', force_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON structuré",
            data=json_data,
            file_name=f"archives_10_pages_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Export PDF links only
        pdf_links = "\n".join([doc['url_pdf'] for doc in data if doc['est_pdf']])
        st.download_button(
            label="📄 Liste des PDF",
            data=pdf_links,
            file_name=f"liste_pdf_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col4:
        # Rapport de synthèse
        report = f"""
        RAPPORT SYNTHÈSE - ARCHIVES ASSEMBLÉE NATIONALE
        ==============================================
        
        Date d'extraction: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Nombre total de pages: 10
        Nombre total de documents: {len(df)}
        
        RÉPARTITION PAR PAGE:
        """
        
        for page in sorted(df['page'].unique()):
            count = len(df[df['page'] == page])
            report += f"\n- Page {page}: {count} documents"
        
        report += f"""
        
        RÉPARTITION PAR PÉRIODE (Top 5):
        """
        
        top_periods = df['periode'].value_counts().head(5)
        for period, count in top_periods.items():
            report += f"\n- {period}: {count} documents"
        
        report += f"""
        
        RÉPARTITION PAR LÉGISLATURE:
        """
        
        leg_counts = df[df['legislature'] != '']['legislature'].value_counts()
        for leg, count in leg_counts.items():
            report += f"\n- Législature {leg}: {count} documents"
        
        report += f"""
        
        DOCUMENTS PDF: {df['est_pdf'].sum()} sur {len(df)}
        """
        
        st.download_button(
            label="📋 Rapport synthèse",
            data=report.encode('utf-8'),
            file_name=f"rapport_synthese_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("📋 Instructions pour utiliser ce dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Objectif
        Ce dashboard extrait et analyse les **10 pages complètes** de résultats 
        de la recherche Google CSE sur les archives de l'Assemblée Nationale.
        
        ### 📊 Fonctionnalités
        - **Extraction complète** des 10 pages
        - **Analyse automatique** des métadonnées
        - **Visualisations interactives**
        - **Filtres avancés** par période, législature, type
        - **Export multi-formats** (CSV, JSON, PDF list)
        
        ### 🏛️ Données extraites
        - Titres complets des documents
        - URLs directes des PDF
        - Périodes historiques
        - Numéros de législature
        - Types de documents
        - Scores de pertinence
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Comment procéder
        
        1. **Récupérez les 10 pages HTML**
           - Ouvrez la pop-up de recherche sur le site
           - Pour chaque page (1 à 10):
           - Faites "Inspecter l'élément" sur la pop-up
           - Copiez le HTML complet de la div des résultats
        
        2. **Téléversez les fichiers HTML**
           - Utilisez le panneau de gauche
           - Téléversez 10 fichiers HTML (un par page)
           - Ou collez directement le HTML
        
        3. **Lancez l'extraction**
           - Cliquez sur "Extraire les 10 pages"
           - Le dashboard analysera tout automatiquement
        
        4. **Explorez les résultats**
           - Utilisez les filtres pour affiner
           - Consultez les visualisations
           - Exportez les données
        """)
    
    # Instructions détaillées
    with st.expander("🔧 Guide technique détaillé", expanded=False):
        st.markdown("""
        ### Comment récupérer le HTML des 10 pages:
        
        1. **Ouvrez le site** https://archives.assemblee-nationale.fr
        2. **Ouvrez la pop-up de recherche** (clic sur la loupe/champ recherche)
        3. **Tapez votre recherche** (ex: "BUMIDOM")
        4. **Ouvrez les Outils Développeurs** (F12)
        
        **Pour chaque page de 1 à 10:**
        
        1. **Sélectionnez la div principale** des résultats:
           ```html
           <div class="gsc-resultsbox-visible">
           ```
        
        2. **Copiez le HTML complet**:
           - Clic droit sur la div
           - "Copy" → "Copy outerHTML"
        
        3. **Sauvegardez dans un fichier**:
           - Page1.html, Page2.html, ..., Page10.html
        
        **Structure HTML attendue:**
        ```html
        <div class="gsc-resultsbox-visible">
          <div class="gsc-resultsRoot...">
            <div class="gsc-expansionArea">
              <!-- Résultats ici -->
              <div class="gsc-webResult gsc-result">...</div>
              <div class="gsc-webResult gsc-result">...</div>
              <!-- 10 résultats par page -->
            </div>
            <!-- Pagination ici -->
            <div class="gsc-cursor">
              <div class="gsc-cursor-page">1</div>
              <div class="gsc-cursor-page">2</div>
              ...
            </div>
          </div>
        </div>
        ```
        
        ### Alternative: Utilisation directe du HTML
        Vous pouvez aussi coller directement le HTML dans des fichiers texte 
        et les téléverser via l'interface.
        """)

# Pied de page
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard Archives Assemblée Nationale • 10 Pages Google CSE • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR', {
            year: 'numeric', month: 'long', day: 'numeric'
        });
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
