import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import urllib.parse
from typing import Dict, List, Optional

# Configuration de la page
st.set_page_config(
    page_title="Google CSE API - Archives AN",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titre principal
st.title("🔍 API Google CSE - Archives Assemblée Nationale")
st.markdown("**Accès direct à l'API Google Custom Search Engine**")

# ==================== CONFIGURATION GOOGLE CSE ====================

# Configuration trouvée dans le fichier JS
GOOGLE_CSE_CONFIG = {
    'cx': '014917347718038151697:kltwr00yvbk',  # Custom Search Engine ID
    'base_url': 'https://cse.google.com',
    'api_endpoint': 'https://www.googleapis.com/customsearch/v1',
    'results_per_page': 10,
    'max_pages': 10,  # Maximum 10 pages (100 résultats)
    'language': 'fr'
}

# ==================== FONCTIONS API GOOGLE CSE ====================

def extract_cse_info_from_js(js_content: str) -> Dict:
    """Extrait les informations de configuration depuis le JS"""
    config = {}
    
    try:
        # Extraire le CX (Custom Search Engine ID)
        cx_match = re.search(r'cx["\']?\s*:\s*["\']([^"\']+)["\']', js_content)
        if cx_match:
            config['cx'] = cx_match.group(1)
            st.success(f"✅ CSE ID trouvé: {config['cx']}")
        
        # Extraire d'autres paramètres
        param_patterns = {
            'hl': r'hl["\']?\s*:\s*["\']([^"\']+)["\']',  # langue
            'safe': r'safe["\']?\s*:\s*["\']([^"\']+)["\']',  # safe search
            'num': r'num["\']?\s*:\s*(\d+)',  # résultats par page
        }
        
        for key, pattern in param_patterns.items():
            match = re.search(pattern, js_content)
            if match:
                config[key] = match.group(1)
        
    except Exception as e:
        st.warning(f"⚠️ Impossible d'extraire la config JS: {e}")
    
    return config

def call_google_cse_api(
    query: str,
    api_key: str,
    cx: str,
    start_index: int = 1,
    num_results: int = 10,
    lang: str = 'fr'
) -> Optional[Dict]:
    """
    Appelle l'API Google Custom Search Engine
    """
    try:
        params = {
            'key': api_key,
            'cx': cx,
            'q': query,
            'start': start_index,
            'num': num_results,
            'hl': lang,
            'lr': f'lang_{lang}',
            'safe': 'active',  # Filtrage safe activé
            'filter': '1',  # Active les filtres de duplication
            'sort': ''  # Pas de tri spécifique
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://archives.assemblee-nationale.fr/'
        }
        
        response = requests.get(
            GOOGLE_CSE_CONFIG['api_endpoint'],
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ Erreur API: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Erreur réseau: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Erreur inattendue: {e}")
        return None

def parse_cse_results(api_response: Dict, page_num: int = 1) -> List[Dict]:
    """
    Parse les résultats de l'API Google CSE
    """
    results = []
    
    if 'items' not in api_response:
        st.warning("⚠️ Aucun 'items' dans la réponse API")
        return results
    
    total_results = api_response.get('searchInformation', {}).get('totalResults', '0')
    st.info(f"📊 Page {page_num}: {len(api_response['items'])} résultats (Total: {total_results})")
    
    for i, item in enumerate(api_response['items']):
        try:
            # Informations de base
            title = item.get('title', 'Sans titre')
            link = item.get('link', '')
            snippet = item.get('snippet', '')
            display_link = item.get('displayLink', '')
            
            # Extraire les métadonnées du pagemap si disponibles
            pagemap = item.get('pagemap', {})
            
            # Détecter le format
            file_format = "Webpage"
            if '.pdf' in link.lower():
                file_format = "PDF/Adobe Acrobat"
            
            # Extraire les années depuis l'URL
            years = extract_years_from_url(link)
            
            # Extraire la législature
            legislature = extract_legislature_from_data(title, link, pagemap)
            
            # Type de document
            doc_type = classify_document_type(title, snippet, link)
            
            # Score de pertinence (fourni par Google)
            score = 100 - i  # Score basé sur la position (meilleur en premier)
            
            # Informations de pagination
            start_index = api_response.get('queries', {}).get('request', [{}])[0].get('startIndex', 1)
            position_globale = start_index + i - 1
            
            results.append({
                'id': f"P{page_num:02d}R{i+1:02d}",
                'titre': title,
                'url': link,
                'url_display': display_link,
                'description': snippet,
                'format': file_format,
                'annee_debut': years.get('debut', ''),
                'annee_fin': years.get('fin', ''),
                'periode': years.get('periode', ''),
                'legislature': legislature,
                'type_document': doc_type,
                'page_api': page_num,
                'position_page': i + 1,
                'position_globale': position_globale,
                'score_google': score,
                'metadonnees': json.dumps(pagemap, ensure_ascii=False) if pagemap else '',
                'date_extraction': datetime.now().isoformat(),
                'est_pdf': '.pdf' in link.lower()
            })
            
        except Exception as e:
            st.warning(f"⚠️ Erreur sur résultat {i+1}: {e}")
            continue
    
    return results

def extract_years_from_url(url: str) -> Dict:
    """Extrait les années depuis l'URL"""
    try:
        # Pattern pour les archives AN: /4/cri/1971-1972-ordinaire1/024.pdf
        match = re.search(r'/(\d{4})-(\d{4})', url)
        if match:
            return {
                'debut': match.group(1),
                'fin': match.group(2),
                'periode': f"{match.group(1)}-{match.group(2)}"
            }
        
        # Pattern alternatif
        match2 = re.search(r'/(\d{4})[/\.\-]', url)
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

def extract_legislature_from_data(title: str, url: str, pagemap: Dict) -> str:
    """Extrait le numéro de législature"""
    try:
        # Depuis l'URL: /4/cri/...
        match = re.search(r'^/(\d+)/cri', url)
        if match:
            return match.group(1)
        
        # Depuis le titre
        match2 = re.search(r'(\d+)[°\'\s]*(?:L|l)égislature', title)
        if match2:
            return match2.group(1)
            
        # Depuis les métadonnées
        if 'metatags' in pagemap:
            for meta in pagemap['metatags']:
                if 'legislature' in str(meta).lower():
                    leg_match = re.search(r'(\d+)', str(meta))
                    if leg_match:
                        return leg_match.group(1)
                        
    except:
        pass
    
    return ""

def classify_document_type(title: str, snippet: str, url: str) -> str:
    """Classifie le type de document"""
    text = f"{title} {snippet}".lower()
    
    if 'compte rendu' in text or 'c.r.i' in text or 'cri' in url.lower():
        return 'Compte rendu'
    elif 'journal officiel' in text or 'j.o' in text:
        return 'Journal Officiel'
    elif 'constitution' in text:
        return 'Constitution'
    elif 'débat' in text:
        return 'Débat parlementaire'
    elif 'question' in text:
        return 'Question'
    elif 'budget' in text or 'finance' in text:
        return 'Budget/Finance'
    elif 'loi' in text:
        return 'Loi'
    elif 'rapport' in text:
        return 'Rapport'
    elif '.pdf' in url.lower():
        return 'Document PDF'
    else:
        return 'Autre'

def fetch_all_pages_via_api(
    query: str,
    api_key: str,
    cx: str,
    total_pages: int = 10
) -> List[Dict]:
    """
    Récupère toutes les pages via l'API Google CSE
    """
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page in range(1, total_pages + 1):
        status_text.text(f"📡 Appel API page {page}/{total_pages}...")
        
        start_index = (page - 1) * GOOGLE_CSE_CONFIG['results_per_page'] + 1
        
        try:
            api_response = call_google_cse_api(
                query=query,
                api_key=api_key,
                cx=cx,
                start_index=start_index,
                num_results=GOOGLE_CSE_CONFIG['results_per_page']
            )
            
            if api_response and 'items' in api_response:
                page_results = parse_cse_results(api_response, page)
                all_results.extend(page_results)
                
                st.success(f"✅ Page {page}: {len(page_results)} résultats")
                
                # Vérifier s'il y a encore des résultats
                total_estimated = int(api_response.get('searchInformation', {}).get('totalResults', '0'))
                if len(all_results) >= total_estimated:
                    st.info(f"ℹ️ Tous les {total_estimated} résultats récupérés")
                    break
            else:
                st.warning(f"⚠️ Page {page}: Réponse API vide")
                break
                
        except Exception as e:
            st.error(f"❌ Erreur page {page}: {e}")
            break
        
        # Mise à jour progression
        progress_bar.progress(page / total_pages)
        
        # Pause pour respecter les limites de rate limiting
        time.sleep(1)
    
    progress_bar.empty()
    status_text.empty()
    
    return all_results

# ==================== INTERFACE STREAMLIT ====================

# Initialisation session state
if 'api_results' not in st.session_state:
    st.session_state.api_results = None
if 'api_config' not in st.session_state:
    st.session_state.api_config = GOOGLE_CSE_CONFIG

# Sidebar
with st.sidebar:
    st.header("🔧 Configuration API")
    
    # Section 1: Clé API Google
    st.subheader("1. Clé API Google")
    api_key = st.text_input(
        "Clé API Google",
        type="password",
        help="Obtenez une clé sur https://console.cloud.google.com/apis/credentials"
    )
    
    # Section 2: Paramètres CSE
    st.subheader("2. Paramètres CSE")
    
    # Charger la config depuis le JS
    js_url = "https://www.google.com/cse/static/element/f71e4ed980f4c082/cse_element__fr.js"
    if st.button("🔄 Charger config depuis JS", type="secondary"):
        try:
            response = requests.get(js_url, timeout=10)
            if response.status_code == 200:
                config = extract_cse_info_from_js(response.text)
                st.session_state.api_config.update(config)
                st.success("✅ Configuration JS chargée!")
            else:
                st.error("❌ Impossible de charger le JS")
        except Exception as e:
            st.error(f"❌ Erreur: {e}")
    
    cx = st.text_input(
        "CSE ID (cx)",
        value=st.session_state.api_config.get('cx', ''),
        help="ID du moteur de recherche personnalisé"
    )
    
    # Section 3: Paramètres de recherche
    st.subheader("3. Paramètres de recherche")
    
    query = st.text_input("Terme de recherche", "BUMIDOM")
    total_pages = st.slider("Nombre de pages", 1, 10, 10)
    results_per_page = st.selectbox("Résultats par page", [10, 20], index=0)
    
    # Section 4: Bouton d'action
    st.divider()
    
    if st.button("🚀 Lancer la recherche API", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ Veuillez entrer une clé API Google")
        elif not cx:
            st.error("❌ Veuillez entrer un CSE ID")
        else:
            with st.spinner("Interrogation de l'API Google CSE..."):
                GOOGLE_CSE_CONFIG['results_per_page'] = results_per_page
                
                results = fetch_all_pages_via_api(
                    query=query,
                    api_key=api_key,
                    cx=cx,
                    total_pages=total_pages
                )
                
                if results:
                    st.session_state.api_results = results
                    st.success(f"✅ {len(results)} résultats récupérés via API!")
                else:
                    st.error("❌ Aucun résultat récupéré")
    
    st.divider()
    
    # Informations techniques
    if st.session_state.api_results:
        st.subheader("📊 Statistiques")
        total = len(st.session_state.api_results)
        pdf_count = sum(1 for r in st.session_state.api_results if r['est_pdf'])
        st.metric("Total", total)
        st.metric("PDF", pdf_count)
        st.metric("Pages", total_pages)

# Contenu principal
if st.session_state.api_results:
    data = st.session_state.api_results
    df = pd.DataFrame(data)
    
    # ==================== VUE D'ENSEMBLE ====================
    st.header("📈 Résultats API Google CSE")
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(df))
    with col2:
        st.metric("Documents PDF", df['est_pdf'].sum())
    with col3:
        st.metric("Périodes uniques", df['periode'].nunique())
    with col4:
        avg_score = df['score_google'].mean() if not df.empty else 0
        st.metric("Score moyen", f"{avg_score:.1f}")
    
    # ==================== TABLEAU DES RÉSULTATS ====================
    st.header("📄 Données brutes API")
    
    # Afficher les données brutes
    with st.expander("📋 Voir les données JSON brutes", expanded=False):
        if data:
            st.json(data[:2])  # Montrer seulement les 2 premiers pour exemple
    
    # Tableau filtré
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_types = st.multiselect(
                "Type de document",
                df['type_document'].unique(),
                default=df['type_document'].unique()
            )
        
        with col2:
            selected_periods = st.multiselect(
                "Période",
                df['periode'].unique(),
                default=df['periode'].unique()
            )
        
        with col3:
            min_score = st.slider("Score minimum", 0, 100, 0)
    
    # Appliquer les filtres
    filtered_df = df[
        (df['type_document'].isin(selected_types)) &
        (df['periode'].isin(selected_periods)) &
        (df['score_google'] >= min_score)
    ]
    
    # Afficher le tableau
    st.dataframe(
        filtered_df[[
            'id', 'titre', 'type_document', 'periode', 'legislature',
            'score_google', 'page_api', 'est_pdf', 'url_display'
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "type_document": st.column_config.TextColumn("Type"),
            "periode": st.column_config.TextColumn("Période"),
            "legislature": st.column_config.TextColumn("Législature"),
            "score_google": st.column_config.NumberColumn("Score", format="%d"),
            "page_api": st.column_config.NumberColumn("Page"),
            "est_pdf": st.column_config.CheckboxColumn("PDF"),
            "url_display": st.column_config.LinkColumn("URL")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.header("📊 Analyses")
    
    tab1, tab2, tab3 = st.tabs(["📅 Chronologie", "📊 Distribution", "🎯 Scores"])
    
    with tab1:
        if not filtered_df.empty and 'periode' in filtered_df.columns:
            # Nettoyer les périodes
            clean_df = filtered_df[filtered_df['periode'] != 'Inconnue'].copy()
            if not clean_df.empty:
                # Extraire l'année de début pour le tri
                clean_df['annee_num'] = clean_df['periode'].str.extract(r'(\d{4})')[0]
                clean_df = clean_df.dropna(subset=['annee_num'])
                clean_df['annee_num'] = clean_df['annee_num'].astype(int)
                clean_df = clean_df.sort_values('annee_num')
                
                period_counts = clean_df['periode'].value_counts().loc[clean_df['periode'].unique()]
                
                fig = px.bar(
                    x=period_counts.index,
                    y=period_counts.values,
                    title="Documents par période historique",
                    labels={'x': 'Période', 'y': 'Nombre'},
                    color=period_counts.values,
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution par type
            if not filtered_df.empty:
                type_counts = filtered_df['type_document'].value_counts()
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="Types de documents",
                    hole=0.3
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution par page
            if not filtered_df.empty:
                page_counts = filtered_df['page_api'].value_counts().sort_index()
                fig = px.bar(
                    x=page_counts.index,
                    y=page_counts.values,
                    title="Résultats par page API",
                    labels={'x': 'Page', 'y': 'Nombre'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Analyse des scores
        if not filtered_df.empty:
            fig = px.histogram(
                filtered_df,
                x='score_google',
                nbins=20,
                title="Distribution des scores Google",
                labels={'score_google': 'Score de pertinence'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Correlation score vs position
            fig2 = px.scatter(
                filtered_df,
                x='position_globale',
                y='score_google',
                color='type_document',
                title="Score vs Position globale",
                labels={'position_globale': 'Position', 'score_google': 'Score'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # ==================== DÉTAILS DES DOCUMENTS ====================
    st.header("🔍 Détails par document")
    
    # Sélectionner un document
    if not filtered_df.empty:
        selected_id = st.selectbox(
            "Sélectionner un document",
            filtered_df['id'].tolist(),
            format_func=lambda x: f"{x} - {filtered_df[filtered_df['id'] == x]['titre'].iloc[0][:50]}..."
        )
        
        if selected_id:
            doc = filtered_df[filtered_df['id'] == selected_id].iloc[0]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {doc['titre']}")
                
                # Métadonnées
                st.markdown("**📋 Métadonnées:**")
                metadata_cols = st.columns(4)
                with metadata_cols[0]:
                    st.metric("Période", doc['periode'])
                with metadata_cols[1]:
                    st.metric("Législature", doc['legislature'] or "N/A")
                with metadata_cols[2]:
                    st.metric("Type", doc['type_document'])
                with metadata_cols[3]:
                    st.metric("Score", f"{doc['score_google']}/100")
                
                # Description
                if doc['description']:
                    st.markdown("**📝 Description:**")
                    st.info(doc['description'])
                
                # URL
                st.markdown("**🔗 Liens:**")
                st.code(doc['url'], language=None)
                
                # Bouton d'accès direct
                if doc['url']:
                    st.markdown(f'<a href="{doc["url"]}" target="_blank"><button style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">📄 Ouvrir le document</button></a>', unsafe_allow_html=True)
            
            with col2:
                # Informations techniques
                st.markdown("**⚙️ Techniques:**")
                st.metric("Page API", doc['page_api'])
                st.metric("Position", doc['position_globale'])
                st.metric("Format", "PDF" if doc['est_pdf'] else "Web")
                
                # Affichage des métadonnées brutes
                if doc['metadonnees'] and doc['metadonnees'] != '{}':
                    with st.expander("📦 Métadonnées brutes"):
                        try:
                            metadata = json.loads(doc['metadonnees'])
                            st.json(metadata)
                        except:
                            st.text(doc['metadonnees'])
    
    # ==================== EXPORT DES DONNÉES ====================
    st.header("💾 Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 CSV complet",
            data=csv,
            file_name=f"google_cse_{query}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON
        export_data = {
            'metadata': {
                'query': query,
                'cx': cx,
                'date': datetime.now().isoformat(),
                'total_results': len(df),
                'pages': total_pages
            },
            'results': data
        }
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON structuré",
            data=json_str.encode('utf-8'),
            file_name=f"google_cse_{query}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Export URLs seulement
        pdf_urls = [doc['url'] for doc in data if doc['est_pdf']]
        urls_text = "\n".join(pdf_urls)
        st.download_button(
            label="📄 URLs PDF",
            data=urls_text.encode('utf-8'),
            file_name=f"pdf_urls_{query}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("🚀 Dashboard API Google CSE")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 À propos
        Ce dashboard utilise l'**API officielle Google Custom Search Engine**
        pour accéder directement aux résultats de recherche des archives.
        
        ### ✅ Avantages
        - **Données fraîches** en temps réel
        - **Structure propre** JSON
        - **Métadonnées complètes**
        - **Pas de scraping HTML**
        - **Limites élevées** (100 req/jour gratuit)
        
        ### 📊 Données disponibles
        - Titres et descriptions
        - URLs directes
        - Scores de pertinence
        - Métadonnées enrichies
        - Informations de pagination
        """)
    
    with col2:
        st.markdown("""
        ### 🔧 Configuration requise
        
        1. **Clé API Google**
           - Allez sur [Google Cloud Console](https://console.cloud.google.com)
           - Créez un projet
           - Activez "Custom Search API"
           - Créez des identifiants → Clé API
        
        2. **CSE ID**
           - Allez sur [cse.google.com](https://cse.google.com)
           - Créez un moteur de recherche
           - Configurez-le pour archives.assemblee-nationale.fr
           - Copiez le "Search engine ID"
        
        3. **Paramètres**
           - Entrez votre clé API
           - Entrez le CSE ID
           - Lancez la recherche
        """)
    
    # Guide détaillé
    with st.expander("📋 Guide étape par étape", expanded=False):
        st.markdown("""
        ### Étape 1: Créer un projet Google Cloud
        1. Allez sur [console.cloud.google.com](https://console.cloud.google.com)
        2. Cliquez sur "Nouveau projet"
        3. Nommez-le "Archives-AN-Scraper"
        4. Cliquez sur "Créer"
        
        ### Étape 2: Activer l'API Custom Search
        1. Dans le menu de gauche: **APIs & Services** → **Bibliothèque**
        2. Cherchez "Custom Search API"
        3. Cliquez sur "Activer"
        
        ### Étape 3: Créer une clé API
        1. **APIs & Services** → **Identifiants**
        2. Cliquez sur "Créer des identifiants" → "Clé API"
        3. Copiez la clé générée
        4. (Optionnel) Restreignez la clé à l'API Custom Search
        
        ### Étape 4: Créer un Custom Search Engine
        1. Allez sur [cse.google.com](https://cse.google.com)
        2. Cliquez sur "Add"
        3. Nom: "Archives Assemblée Nationale"
        4. Sites à rechercher: `archives.assemblee-nationale.fr/*`
        5. Langue: French
        6. Cliquez sur "Create"
        7. Copiez le "Search engine ID" (format: 012345678901234567890:abc123def456)
        
        ### Étape 5: Tester l'API
        Une fois configuré, vous pouvez tester avec:
        ```bash
        curl "https://www.googleapis.com/customsearch/v1?key=VOTRE_CLE&cx=VOTRE_CX&q=BUMIDOM"
        ```
        """)
    
    # Exemple de réponse API
    with st.expander("📄 Exemple de réponse API", expanded=False):
        st.json({
            "kind": "customsearch#search",
            "url": {
                "type": "application/json",
                "template": "https://www.googleapis.com/customsearch/v1?q={searchTerms}&num={count?}&start={startIndex?}&lr={language?}&safe={safe?}&cx={cx?}&cref={cref?}&sort={sort?}&filter={filter?}&gl={gl?}&cr={cr?}&googlehost={googleHost?}&c2coff={disableCnTwTranslation?}&hq={hq?}&hl={hl?}&siteSearch={siteSearch?}&siteSearchFilter={siteSearchFilter?}&exactTerms={exactTerms?}&excludeTerms={excludeTerms?}&linkSite={linkSite?}&orTerms={orTerms?}&relatedSite={relatedSite?}&dateRestrict={dateRestrict?}&lowRange={lowRange?}&highRange={highRange?}&searchType={searchType?}&fileType={fileType?}&rights={rights?}&imgSize={imgSize?}&imgType={imgType?}&imgColorType={imgColorType?}&imgDominantColor={imgDominantColor?}&alt=json"
            },
            "queries": {
                "request": [
                    {
                        "title": "Google Custom Search - BUMIDOM",
                        "totalResults": "131",
                        "count": 10,
                        "startIndex": 1,
                        "inputEncoding": "utf8",
                        "outputEncoding": "utf8",
                        "safe": "off",
                        "cx": "014917347718038151697:kltwr00yvbk"
                    }
                ]
            },
            "context": {
                "title": "Archives AN"
            },
            "searchInformation": {
                "searchTime": 0.262152,
                "formattedSearchTime": "0.26",
                "totalResults": "131",
                "formattedTotalResults": "131"
            },
            "items": [
                {
                    "kind": "customsearch#result",
                    "title": "JOURNAL OFFICIAL - Assemblée nationale - Archives",
                    "htmlTitle": "JOURNAL OFFICIAL - Assemblée nationale - Archives",
                    "link": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf",
                    "displayLink": "archives.assemblee-nationale.fr",
                    "snippet": "26 oct. 1971 ... Bumidom. Nous avons donc fait un effort très sérieux — je crois qu'il commence à porter ses fruits — pour l'information, comme on l'a...",
                    "htmlSnippet": "26 oct. 1971 \u003cb\u003e...\u003c/b\u003e \u003cb\u003eBumidom\u003c/b\u003e. Nous avons donc fait un effort très sérieux — je crois qu&#39;il commence à porter ses fruits — pour l&#39;information, comme on l&#39;a...",
                    "cacheId": "abc123",
                    "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1971-1972.../024.pdf",
                    "htmlFormattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1971-1972.../024.pdf",
                    "pagemap": {
                        "metatags": [
                            {
                                "dc.title": "JOURNAL OFFICIAL - Assemblée nationale - Archives",
                                "dc.format": "application/pdf"
                            }
                        ],
                        "cse_thumbnail": [
                            {
                                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSfqjYzwWbrBntmlpFWjaoFvYi7LrDVp5DG2RSIoqxZBRmF5KtvGm3yArc&s",
                                "width": "212",
                                "height": "238"
                            }
                        ]
                    }
                }
            ]
        })

# Pied de page
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Google Custom Search Engine API • cx: 014917347718038151697:kltwr00yvbk • 
    <a href="https://developers.google.com/custom-search/v1/overview" target="_blank">Documentation API</a> • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
