import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import urljoin, quote
import json

# Configuration de la page
st.set_page_config(
    page_title="Archives AN - Dashboard Google CSE",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titre principal
st.title("🔍 Dashboard Archives Assemblée Nationale")
st.markdown("**Extraction des résultats depuis la Recherche Personnalisée Google (CSE)**")

# Initialisation session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 0

# ==================== FONCTIONS DE SCRAPING ====================

def extract_google_cse_results(html_content, page_num=1):
    """
    Extrait les résultats depuis le HTML de la Google CSE popup
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # Trouver tous les résultats (div avec class gsc-webResult)
    result_divs = soup.find_all('div', class_='gsc-webResult')
    
    st.info(f"📊 {len(result_divs)} résultats trouvés sur la page {page_num}")
    
    for i, result in enumerate(result_divs):
        try:
            # Extraire le titre
            title_elem = result.find('a', class_='gs-title')
            title = title_elem.get_text(strip=True) if title_elem else "Sans titre"
            
            # Extraire l'URL
            url = title_elem.get('href', '') if title_elem else ""
            data_ctorig = title_elem.get('data-ctorig', '') if title_elem else ""
            final_url = data_ctorig if data_ctorig else url
            
            # Extraire l'URL visible
            visible_url_elem = result.find('div', class_='gs-visibleUrl')
            visible_url = visible_url_elem.get_text(strip=True) if visible_url_elem else ""
            
            # Extraire la description/snippet
            snippet_elem = result.find('div', class_='gs-snippet')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Extraire le format du fichier
            file_format_elem = result.find('div', class_='gs-fileFormat')
            file_format = file_format_elem.get_text(strip=True).replace('Format de fichier : ', '') if file_format_elem else ""
            
            # Extraire la date depuis l'URL ou le snippet
            date_match = re.search(r'/(\d{4})-(\d{4})/', final_url)
            year_range = f"{date_match.group(1)}-{date_match.group(2)}" if date_match else ""
            
            # Extraire la législature depuis le titre ou l'URL
            legislature_match = re.search(r'(\d+)[e°\']?\s*(?:L|l)égislature', title)
            legislature = legislature_match.group(1) if legislature_match else ""
            
            # Extraire le type de session
            session_type = "ordinaire"
            if 'extraordinaire' in final_url:
                session_type = "extraordinaire"
            
            results.append({
                'index': (page_num - 1) * 10 + i + 1,
                'titre': title,
                'url': final_url,
                'url_visible': visible_url,
                'description': snippet,
                'format': file_format,
                'periode': year_range,
                'legislature': legislature,
                'session': session_type,
                'page': page_num,
                'date_extraction': datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            
        except Exception as e:
            st.warning(f"Erreur sur le résultat {i+1}: {str(e)}")
            continue
    
    return results

def simulate_cse_request(search_term="Bumidom", page=1, results_per_page=10):
    """
    Simule une requête à la Google Custom Search Engine
    Note: En production, vous pourriez utiliser l'API Google CSE
    """
    
    # Paramètres de base Google CSE
    cse_id = "014917347718038151697:kltwr00yvbk"  # Trouvé dans le HTML
    base_url = "https://cse.google.com/cse"
    
    # Pour la simulation, on va parser le HTML fourni
    # En réalité, vous devriez faire une vraie requête à l'API
    
    # HEADERS pour simuler un navigateur
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://archives.assemblee-nationale.fr/'
    }
    
    try:
        # URL de l'API Google CSE (version publique)
        api_url = f"https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': 'YOUR_API_KEY',  # À configurer si vous avez une clé API
            'cx': cse_id,
            'q': search_term,
            'start': (page - 1) * results_per_page + 1,
            'num': results_per_page,
            'hl': 'fr'
        }
        
        # Pour cette démo, on va utiliser le HTML que vous avez fourni
        # En production, décommentez la ligne ci-dessous:
        # response = requests.get(api_url, params=params, headers=headers)
        
        # Pour l'instant, on utilise le HTML statique
        html_content = """[VOTRE HTML ICI - celui que vous avez fourni]"""
        
        return html_content
        
    except Exception as e:
        st.error(f"Erreur API: {str(e)}")
        return None

def scrape_all_pages(search_term, total_pages=10):
    """
    Scrape toutes les pages de résultats
    """
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page_num in range(1, total_pages + 1):
        status_text.text(f"📄 Scraping page {page_num}/{total_pages}...")
        
        try:
            # Simuler la requête
            html_content = simulate_cse_request(search_term, page_num)
            
            if html_content:
                page_results = extract_google_cse_results(html_content, page_num)
                all_results.extend(page_results)
                
                st.success(f"✅ Page {page_num}: {len(page_results)} résultats extraits")
            else:
                st.warning(f"Page {page_num}: Aucun contenu")
                
        except Exception as e:
            st.error(f"❌ Erreur page {page_num}: {str(e)}")
        
        # Mise à jour progression
        progress_bar.progress(page_num / total_pages)
        time.sleep(1)  # Pause pour éviter le rate limiting
    
    progress_bar.empty()
    status_text.empty()
    
    return all_results

# ==================== INTERFACE STREAMLIT ====================

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    search_term = st.text_input("Terme de recherche", "Bumidom")
    total_pages = st.slider("Nombre de pages à scraper", 1, 10, 10)
    
    # Options d'affichage
    st.subheader("Options d'affichage")
    show_preview = st.checkbox("Aperçu des PDF", value=True)
    group_by_year = st.checkbox("Grouper par année", value=True)
    
    # Bouton d'action principal
    if st.button("🚀 Lancer le scraping", type="primary", use_container_width=True):
        with st.spinner(f"Scraping de {total_pages} pages en cours..."):
            results = scrape_all_pages(search_term, total_pages)
            
            if results:
                st.session_state.scraped_data = results
                st.session_state.total_pages = total_pages
                st.success(f"✅ {len(results)} résultats scrapés avec succès!")
            else:
                st.error("❌ Aucun résultat trouvé")
    
    st.divider()
    
    # Informations techniques
    st.header("ℹ️ Informations")
    st.markdown("""
    **Source:** Google Custom Search Engine  
    **CSE ID:** 014917347718038151697:kltwr00yvbk  
    **Site:** Archives Assemblée Nationale  
    **Format:** PDF documents parlementaires
    """)

# Contenu principal
if st.session_state.scraped_data:
    data = st.session_state.scraped_data
    df = pd.DataFrame(data)
    
    # Métriques principales
    st.header("📈 Vue d'ensemble")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total résultats", len(df))
    with col2:
        unique_years = df['periode'].nunique()
        st.metric("Périodes couvertes", unique_years)
    with col3:
        pdf_count = df[df['format'].str.contains('PDF', na=False)].shape[0]
        st.metric("Documents PDF", pdf_count)
    with col4:
        legislatures = df['legislature'].nunique()
        st.metric("Législatures", legislatures)
    
    # Tableau des résultats
    st.header("📄 Résultats détaillés")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not df.empty and 'periode' in df.columns:
            periods = sorted(df['periode'].unique())
            selected_periods = st.multiselect("Filtrer par période", periods, default=periods)
            if selected_periods:
                df = df[df['periode'].isin(selected_periods)]
    
    with col2:
        if not df.empty and 'legislature' in df.columns:
            legislatures = sorted([l for l in df['legislature'].unique() if l])
            selected_leg = st.multiselect("Filtrer par législature", legislatures, default=legislatures)
            if selected_leg:
                df = df[df['legislature'].isin(selected_leg)]
    
    with col3:
        if not df.empty and 'page' in df.columns:
            pages = sorted(df['page'].unique())
            selected_pages = st.multiselect("Filtrer par page", pages, default=pages)
            if selected_pages:
                df = df[df['page'].isin(selected_pages)]
    
    # Afficher le tableau
    st.dataframe(
        df[['index', 'titre', 'periode', 'legislature', 'page', 'format']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "periode": st.column_config.TextColumn("Période"),
            "legislature": st.column_config.TextColumn("Législature"),
            "page": st.column_config.NumberColumn("Page"),
            "format": st.column_config.TextColumn("Format")
        }
    )
    
    # Visualisations
    st.header("📊 Analyses visuelles")
    
    tab1, tab2, tab3 = st.tabs(["📅 Par période", "🏛️ Par législature", "📈 Distribution"])
    
    with tab1:
        if not df.empty and 'periode' in df.columns:
            period_counts = df['periode'].value_counts().sort_index()
            fig = px.bar(
                x=period_counts.index,
                y=period_counts.values,
                title="Documents par période",
                labels={'x': 'Période', 'y': 'Nombre de documents'},
                color=period_counts.values,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if not df.empty and 'legislature' in df.columns:
            leg_counts = df['legislature'].value_counts()
            fig = px.pie(
                values=leg_counts.values,
                names=leg_counts.index,
                title="Répartition par législature",
                hole=0.3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        if not df.empty and 'page' in df.columns:
            page_dist = df['page'].value_counts().sort_index()
            fig = px.line(
                x=page_dist.index,
                y=page_dist.values,
                title="Distribution des résultats par page",
                labels={'x': 'Page de résultats', 'y': 'Nombre de résultats'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Détails des documents
    st.header("🔍 Détails des documents")
    
    for idx, row in df.iterrows():
        with st.expander(f"{row['titre']} ({row['periode']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**URL:** [{row['url_visible']}]({row['url']})")
                st.markdown(f"**Format:** {row['format']}")
                st.markdown(f"**Législature:** {row['legislature']}")
                st.markdown(f"**Session:** {row['session']}")
            
            with col2:
                st.markdown(f"**Page de résultats:** {row['page']}")
                st.markdown(f"**Index:** {row['index']}")
                st.markdown(f"**Date d'extraction:** {row['date_extraction']}")
            
            st.markdown("**Description:**")
            st.info(row['description'])
            
            # Bouton pour accéder au PDF
            if st.button(f"📄 Ouvrir le PDF {row['index']}", key=f"pdf_{row['index']}"):
                st.markdown(f'<a href="{row["url"]}" target="_blank">Ouvrir le document PDF</a>', unsafe_allow_html=True)
    
    # Export des données
    st.header("💾 Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name=f"archives_cse_{search_term}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON
        json_data = df.to_json(orient='records', force_ascii=False)
        st.download_button(
            label="📥 Télécharger JSON",
            data=json_data,
            file_name=f"archives_cse_{search_term}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Rapport HTML
        html_report = f"""
        <html>
        <head>
            <title>Rapport Archives AN - {search_term}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                .result {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
                .url {{ color: #0066cc; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <h1>Rapport Archives Assemblée Nationale</h1>
            <p><strong>Recherche:</strong> {search_term}</p>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p><strong>Nombre de résultats:</strong> {len(df)}</p>
            <hr>
        """
        
        for idx, row in df.iterrows():
            html_report += f"""
            <div class="result">
                <h3>{row['titre']}</h3>
                <p class="url"><a href="{row['url']}" target="_blank">{row['url_visible']}</a></p>
                <p><strong>Période:</strong> {row['periode']} | <strong>Législature:</strong> {row['legislature']}</p>
                <p>{row['description']}</p>
            </div>
            """
        
        html_report += "</body></html>"
        
        st.download_button(
            label="🌐 Télécharger HTML",
            data=html_report,
            file_name=f"rapport_{search_term}.html",
            mime="text/html",
            use_container_width=True
        )

else:
    # Écran d'accueil
    st.header("Bienvenue dans le dashboard de scraping Google CSE")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Fonctionnalités
        - **Scraping Google CSE** des archives
        - **Extraction des métadonnées** PDF
        - **Analyse par période** et législature
        - **Visualisations interactives**
        - **Export multi-formats**
        
        ### 📋 Données extraites
        - Titres des documents
        - URLs des PDF
        - Périodes couvertes
        - Législatures
        - Descriptions/snippets
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Comment utiliser
        1. **Configurez** la recherche dans la sidebar
        2. **Cliquez** sur "Lancer le scraping"
        3. **Explorez** les résultats via les onglets
        4. **Filtrez** par période/législature
        5. **Exportez** les données
        
        ### ⚠️ Notes importantes
        - Le scraping utilise la Google CSE du site
        - Les résultats sont limités à 10 pages
        - Certains PDF peuvent être volumineux
        - Respectez les conditions d'utilisation
        """)
    
    # Instructions détaillées
    with st.expander("🔧 Configuration avancée", expanded=False):
        st.markdown("""
        ### Pour utiliser l'API Google CSE officielle:
        
        1. **Créez un projet** sur Google Cloud Console
        2. **Activez l'API** Custom Search
        3. **Créez des identifiants** API
        4. **Configurez la CSE** sur [cse.google.com](https://cse.google.com)
        5. **Remplacez dans le code:**
        
        ```python
        # Dans simulate_cse_request():
        params = {
            'key': 'VOTRE_CLE_API',  # Votre clé API Google
            'cx': 'VOTRE_CSE_ID',     # Votre ID CSE
            'q': search_term,
            'start': (page - 1) * 10 + 1,
            'num': 10,
            'hl': 'fr'
        }
        
        response = requests.get('https://www.googleapis.com/customsearch/v1', 
                              params=params)
        data = response.json()
        ```
        
        ### Structure des résultats Google CSE:
        ```json
        {
          "items": [
            {
              "title": "Titre du document",
              "link": "https://.../document.pdf",
              "snippet": "Description...",
              "pagemap": {
                "metatags": [...],
                "cse_thumbnail": [...]
              }
            }
          ],
          "queries": {...},
          "searchInformation": {...}
        }
        ```
        """)

# Pied de page
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard Google CSE • Archives Assemblée Nationale • 
    Recherche personnalisée Google • 
    Données extraites: <span id='date'></span>
    <script>document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');</script>
    </div>
    """,
    unsafe_allow_html=True
)
