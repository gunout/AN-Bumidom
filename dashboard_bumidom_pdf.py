import streamlit as st
import requests
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import time

# ==================== CONFIGURATION ====================
st.set_page_config(page_title="Dashboard API Google CSE", layout="wide")
st.title("🔍 Dashboard API - Archives Assemblée Nationale")
st.markdown("**Accès direct à l'endpoint de la Recherche Personnalisée Google**")

# ==================== FONCTIONS PRINCIPALES ====================

def construire_url_api(base_url, parametres):
    """Construit une URL API à partir des paramètres"""
    # Extraire les paramètres de base
    params_dict = {
        'cx': parametres.get('cx', '014917347718038151697:kltwr00yvbk'),
        'q': parametres.get('q', 'bumidom'),
        'hl': parametres.get('hl', 'fr'),
        'num': parametres.get('num', 10),  # Résultats par page
        'start': parametres.get('start', 1),  # Index de début
        'source': parametres.get('source', 'gcsc'),
        'output': parametres.get('output', 'json'),  # Format de sortie
    }
    
    # Ajouter d'autres paramètres optionnels
    parametres_optionnels = ['adsafe', 'fexp', 'client', 'r', 'sct', 'sc_status', 
                            'ivt', 'type', 'oe', 'ie', 'format', 'ad', 'nocache',
                            'v', 'bsl', 'pac', 'u_his', 'u_tz', 'dt', 'u_w', 'u_h',
                            'biw', 'bih', 'psw', 'psh', 'frm', 'uio', 'drt', 'jsid',
                            'jsv', 'rurl', 'referer']
    
    for param in parametres_optionnels:
        if param in parametres:
            params_dict[param] = parametres[param]
    
    # Construire l'URL
    query_string = '&'.join([f'{k}={v}' for k, v in params_dict.items()])
    return f"{base_url}?{query_string}"

def appeler_api_google_cse(url_api):
    """Appelle l'API Google CSE et retourne les données"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*',
            'Referer': 'https://archives.assemblee-nationale.fr/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        st.info(f"🌐 Appel de l'API: {url_api[:100]}...")
        
        response = requests.get(url_api, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Essayer de parser comme JSON
            try:
                data = response.json()
                return {'success': True, 'data': data, 'raw': response.text}
            except json.JSONDecodeError:
                # Si ce n'est pas du JSON, retourner le texte brut
                return {'success': True, 'data': None, 'raw': response.text}
        else:
            return {'success': False, 'error': f"HTTP {response.status_code}", 'raw': response.text}
            
    except Exception as e:
        return {'success': False, 'error': str(e), 'raw': None}

def parser_reponse_api(reponse, page_num=1):
    """Parse la réponse de l'API en données structurées"""
    resultats = []
    
    if not reponse['success'] or not reponse['data']:
        st.warning("Réponse API vide ou invalide")
        return resultats
    
    data = reponse['data']
    
    # Vérifier différents formats de réponse
    if 'results' in data:
        items = data['results']
    elif 'items' in data:
        items = data['items']
    elif 'ads' in data:  # Pour les annonces
        items = data['ads']
    elif isinstance(data, list):
        items = data
    else:
        # Essayer de trouver des résultats dans la structure
        items = []
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict) and any(k in value[0] for k in ['title', 'link', 'url']):
                    items = value
                    break
    
    st.info(f"📊 {len(items)} éléments trouvés dans la réponse")
    
    for i, item in enumerate(items):
        try:
            # Extraire les informations selon la structure
            titre = item.get('title', item.get('titre', item.get('name', f'Document {i+1}')))
            url = item.get('link', item.get('url', item.get('href', '')))
            description = item.get('snippet', item.get('description', item.get('summary', '')))
            
            # Métadonnées supplémentaires
            metadonnees = {}
            if 'pagemap' in item:
                metadonnees = item['pagemap']
            
            # Détecter le type de document
            type_doc = "Document"
            if '.pdf' in url.lower():
                type_doc = "PDF"
            elif 'archives.assemblee-nationale.fr' in url:
                if '/cri/' in url:
                    type_doc = "Compte rendu"
                elif 'journal' in url.lower():
                    type_doc = "Journal Officiel"
            
            # Extraire la législature depuis l'URL
            legislature = ""
            if '/cri/' in url:
                leg_match = re.search(r'^\/(\d+)\/cri', url)
                if leg_match:
                    legislature = leg_match.group(1)
            
            # Extraire les années
            annee_match = re.search(r'/(\d{4})-(\d{4})', url)
            if annee_match:
                periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
            else:
                periode = "Inconnue"
            
            resultats.append({
                'id': f"P{page_num:02d}R{i+1:02d}",
                'titre': titre[:150] + "..." if len(titre) > 150 else titre,
                'url': url,
                'description': description[:200] + "..." if len(description) > 200 else description,
                'type': type_doc,
                'legislature': legislature,
                'periode': periode,
                'page': page_num,
                'position': i + 1,
                'score': item.get('score', 100 - i),
                'metadonnees': json.dumps(metadonnees) if metadonnees else '',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            st.warning(f"Erreur sur l'élément {i+1}: {str(e)}")
            continue
    
    return resultats

def scraper_paginations(termes_recherche, pages_total=10):
    """Scrape plusieurs pages de résultats"""
    tous_resultats = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page in range(1, pages_total + 1):
        status_text.text(f"📄 Page {page}/{pages_total}")
        
        # Calculer le start index (Google utilise start=1 pour page 1)
        start_index = (page - 1) * 10 + 1
        
        # Construire les paramètres
        params = {
            'q': termes_recherche,
            'start': start_index,
            'num': 10,
            'output': 'json'
        }
        
        # Construire l'URL API
        url_api = construire_url_api(
            "https://syndicatedsearch.goog/cse_v2/ads",
            params
        )
        
        # Appeler l'API
        reponse = appeler_api_google_cse(url_api)
        
        if reponse['success']:
            resultats_page = parser_reponse_api(reponse, page)
            tous_resultats.extend(resultats_page)
            st.success(f"✅ Page {page}: {len(resultats_page)} résultats")
        else:
            st.error(f"❌ Page {page}: {reponse.get('error', 'Erreur inconnue')}")
            break
        
        # Mettre à jour la progression
        progress_bar.progress(page / pages_total)
        
        # Pause pour éviter le rate limiting
        time.sleep(0.5)
    
    progress_bar.empty()
    status_text.empty()
    
    return tous_resultats

# ==================== INTERFACE STREAMLIT ====================

# Import regex pour l'analyse
import re

# Initialisation du state
if 'donnees_scrapees' not in st.session_state:
    st.session_state.donnees_scrapees = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration API")
    
    # URL de base
    url_base = st.text_input(
        "URL API de base",
        value="https://syndicatedsearch.goog/cse_v2/ads",
        help="Endpoint principal de l'API Google CSE"
    )
    
    # Paramètres principaux
    st.subheader("Paramètres de recherche")
    terme_recherche = st.text_input("Terme de recherche", "bumidom")
    nombre_pages = st.slider("Nombre de pages", 1, 10, 10)
    
    # Paramètres avancés
    with st.expander("⚙️ Paramètres avancés"):
        cx_id = st.text_input("CX ID", "014917347718038151697:kltwr00yvbk")
        format_sortie = st.selectbox("Format de sortie", ["json", "xml", "html"])
        langue = st.text_input("Langue (hl)", "fr")
    
    # Bouton d'action
    st.divider()
    
    if st.button("🚀 Lancer le scraping API", type="primary", use_container_width=True):
        with st.spinner("Scraping des pages via l'API..."):
            resultats = scraper_paginations(terme_recherche, nombre_pages)
            
            if resultats:
                st.session_state.donnees_scrapees = resultats
                st.success(f"✅ {len(resultats)} résultats scrapés!")
            else:
                st.error("❌ Aucun résultat trouvé")
    
    # Afficher les statistiques si des données existent
    if st.session_state.donnees_scrapees:
        st.divider()
        st.subheader("📊 Statistiques")
        total = len(st.session_state.donnees_scrapees)
        pages = len(set(r['page'] for r in st.session_state.donnees_scrapees))
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total)
        with col2:
            st.metric("Pages", pages)

# Contenu principal
if st.session_state.donnees_scrapees:
    donnees = st.session_state.donnees_scrapees
    df = pd.DataFrame(donnees)
    
    # ==================== VUE D'ENSEMBLE ====================
    st.header("📈 Vue d'ensemble")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents", len(df))
    with col2:
        st.metric("Pages API", df['page'].nunique())
    with col3:
        st.metric("Types", df['type'].nunique())
    with col4:
        pdf_count = df[df['type'] == 'PDF'].shape[0]
        st.metric("Documents PDF", pdf_count)
    
    # ==================== TABLEAU DES RÉSULTATS ====================
    st.header("📄 Résultats API")
    
    # Filtres
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pages = sorted(df['page'].unique())
            pages_selection = st.multiselect("Pages", pages, default=pages)
        
        with col2:
            types = sorted(df['type'].unique())
            types_selection = st.multiselect("Types", types, default=types)
        
        with col3:
            legislatures = sorted([l for l in df['legislature'].unique() if l])
            leg_selection = st.multiselect("Législatures", legislatures, default=legislatures)
    
    # Appliquer les filtres
    df_filtre = df[
        (df['page'].isin(pages_selection)) &
        (df['type'].isin(types_selection)) &
        (df['legislature'].isin(leg_selection) | (df['legislature'] == ''))
    ]
    
    # Afficher le tableau
    st.dataframe(
        df_filtre[['id', 'titre', 'type', 'page', 'legislature', 'periode', 'score']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "type": st.column_config.TextColumn("Type"),
            "page": st.column_config.NumberColumn("Page"),
            "legislature": st.column_config.TextColumn("Législature"),
            "periode": st.column_config.TextColumn("Période"),
            "score": st.column_config.NumberColumn("Score", format="%d")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.header("📊 Analyses")
    
    tab1, tab2, tab3 = st.tabs(["📅 Chronologie", "📊 Distribution", "🎯 Scores"])
    
    with tab1:
        # Graphique par période
        if 'periode' in df_filtre.columns and not df_filtre.empty:
            period_counts = df_filtre['periode'].value_counts()
            if len(period_counts) > 0:
                fig = px.bar(
                    x=period_counts.index,
                    y=period_counts.values,
                    title="Documents par période",
                    labels={'x': 'Période', 'y': 'Nombre'},
                    color=period_counts.values,
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution par type
            type_counts = df_filtre['type'].value_counts()
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Distribution par type",
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution par page
            page_counts = df_filtre['page'].value_counts().sort_index()
            fig = px.bar(
                x=page_counts.index.astype(str),
                y=page_counts.values,
                title="Résultats par page API",
                labels={'x': 'Page', 'y': 'Nombre'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Analyse des scores
        if 'score' in df_filtre.columns:
            fig = px.histogram(
                df_filtre,
                x='score',
                nbins=20,
                title="Distribution des scores",
                labels={'score': 'Score de pertinence'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # ==================== DÉTAILS DES DOCUMENTS ====================
    st.header("🔍 Détails par document")
    
    if not df_filtre.empty:
        # Sélection d'un document
        doc_id = st.selectbox(
            "Choisir un document",
            df_filtre['id'].tolist(),
            format_func=lambda x: f"{x} - {df_filtre[df_filtre['id'] == x]['titre'].iloc[0][:50]}..."
        )
        
        if doc_id:
            doc = df_filtre[df_filtre['id'] == doc_id].iloc[0]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {doc['titre']}")
                
                # Métadonnées
                st.markdown("**📋 Informations:**")
                
                meta_cols = st.columns(4)
                with meta_cols[0]:
                    st.metric("Page", doc['page'])
                with meta_cols[1]:
                    st.metric("Score", doc['score'])
                with meta_cols[2]:
                    st.metric("Type", doc['type'])
                with meta_cols[3]:
                    st.metric("Législature", doc['legislature'] or "N/A")
                
                # Description
                if doc['description']:
                    st.markdown("**📝 Description:**")
                    st.info(doc['description'])
                
                # URL
                if doc['url']:
                    st.markdown("**🔗 URL:**")
                    st.code(doc['url'])
                    
                    # Bouton pour ouvrir
                    st.markdown(
                        f'<a href="{doc["url"]}" target="_blank">'
                        '<button style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">'
                        '📄 Ouvrir le document</button></a>',
                        unsafe_allow_html=True
                    )
            
            with col2:
                # Informations techniques
                st.markdown("**⚙️ Techniques:**")
                st.metric("Position", doc['position'])
                st.metric("Période", doc['periode'])
                
                # Métadonnées brutes
                if doc['metadonnees'] and doc['metadonnees'] != '{}':
                    with st.expander("Métadonnées"):
                        try:
                            meta = json.loads(doc['metadonnees'])
                            st.json(meta)
                        except:
                            st.text(doc['metadonnees'])
    
    # ==================== EXPORT ====================
    st.header("💾 Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 CSV complet",
            data=csv,
            file_name=f"api_google_cse_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON
        json_data = json.dumps(donnees, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON structuré",
            data=json_data,
            file_name=f"api_google_cse_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Export URLs seulement
        urls = [d['url'] for d in donnees if d['url']]
        urls_text = "\n".join(urls)
        st.download_button(
            label="📄 Liste des URLs",
            data=urls_text.encode('utf-8'),
            file_name=f"urls_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("🔍 Dashboard API Google CSE")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 À propos
        Ce dashboard interroge directement l'**API Google CSE** utilisée par 
        le site des archives de l'Assemblée Nationale.
        
        ### ✅ Fonctionnalités
        - **Accès direct** à l'API syndicatedsearch.goog
        - **Scraping paginé** (10 pages max)
        - **Analyse automatique** des résultats
        - **Visualisations interactives**
        - **Export multi-formats**
        
        ### 🔗 URL API découverte
        Vous avez trouvé l'endpoint réel :
        `syndicatedsearch.goog/cse_v2/ads`
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Comment l'utiliser
        1. **Configurez** les paramètres dans la sidebar
        2. **Lancez** le scraping API
        3. **Explorez** les résultats via les tableaux
        4. **Analysez** avec les visualisations
        5. **Exportez** les données
        
        ### ⚙️ Paramètres clés
        - **CX**: 014917347718038151697:kltwr00yvbk
        - **Query**: Votre terme de recherche
        - **Pages**: 1 à 10
        - **Format**: JSON (recommandé)
        """)
    
    # Détails techniques
    with st.expander("🔧 Détails techniques de l'URL", expanded=False):
        st.markdown("""
        ### Analyse de votre URL API:
        
        **Endpoint principal:**
        ```
        https://syndicatedsearch.goog/cse_v2/ads
        ```
        
        **Paramètres importants:**
        - `cx=014917347718038151697:kltwr00yvbk` → ID du CSE
        - `q=bumidom` → Terme de recherche
        - `hl=fr` → Langue française
        - `source=gcsc` → Source Google CSE
        - `output=uds_ads_only` → Format de sortie
        
        **Paramètres de pagination:**
        - `start=1` → Index de début (à ajuster pour la pagination)
        - `num=10` → Nombre de résultats par page
        
        **Pour scraper 10 pages:**
        ```
        Page 1: start=1
        Page 2: start=11
        Page 3: start=21
        ...
        Page 10: start=91
        ```
        """)

# ==================== PIED DE PAGE ====================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard API Google CSE • Endpoint: syndicatedsearch.goog/cse_v2/ads • 
    CX: 014917347718038151697:kltwr00yvbk • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
