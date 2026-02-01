import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re
import os
import glob
from collections import Counter

# ==================== CONFIGURATION ====================
st.set_page_config(page_title="Dashboard Google CSE - 9 Fichiers JSON", layout="wide")
st.title("🔍 Dashboard Google CSE - Analyse des 9 Fichiers JSON")
st.markdown("**Analyse COMPLÈTE de tous les résultats des 9 fichiers JSON**")

# ==================== FONCTIONS PRINCIPALES ====================

def charger_fichiers_json(dossier="."):
    """Charge tous les fichiers JSON du dossier"""
    fichiers_json = []
    
    # Chercher tous les fichiers json(*).txt
    pattern = r'json\(\d+\)\.txt'
    fichiers = [f for f in os.listdir(dossier) if re.match(pattern, f)]
    
    # Si aucun fichier trouvé, essayer avec d'autres patterns
    if not fichiers:
        fichiers = glob.glob("json*.txt")
    
    # Trier par numéro
    def extraire_numero(fichier):
        match = re.search(r'json\(?(\d+)\)?', fichier)
        return int(match.group(1)) if match else 0
    
    fichiers.sort(key=extraire_numero)
    
    for fichier in fichiers:
        try:
            chemin = os.path.join(dossier, fichier)
            with open(chemin, 'r', encoding='utf-8') as f:
                contenu = f.read()
                fichiers_json.append({
                    'nom': fichier,
                    'chemin': chemin,
                    'contenu': contenu,
                    'taille': len(contenu)
                })
            st.success(f"✅ {fichier} chargé ({len(contenu)} caractères)")
        except Exception as e:
            st.error(f"❌ Erreur avec {fichier}: {e}")
    
    return fichiers_json

def extraire_json_du_contenu(contenu):
    """Extrait le JSON du contenu du fichier"""
    # Chercher le pattern google.search.cse.apiXXXX({
    pattern = r'google\.search\.cse\.api\d+\(\s*({.*})\);?\s*$'
    match = re.search(pattern, contenu, re.DOTALL)
    
    if match:
        json_str = match.group(1)
    else:
        # Essayer de trouver juste les accolades
        start_idx = contenu.find('{')
        end_idx = contenu.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = contenu[start_idx:end_idx]
        else:
            return None
    
    # Nettoyer le JSON
    json_str = nettoyer_json(json_str)
    
    try:
        return json.loads(json_str)
    except:
        return None

def nettoyer_json(json_brut):
    """Nettoie le JSON brut"""
    # Supprimer les commentaires
    json_propre = re.sub(r'/\*.*?\*/', '', json_brut, flags=re.DOTALL)
    
    # Remplacer les simples quotes par des doubles quotes
    json_propre = re.sub(r'(\w+):\s*\'', r'\1: "', json_propre)
    json_propre = re.sub(r'\',', '",', json_propre)
    json_propre = re.sub(r'\'}$', '"}', json_propre)
    json_propre = re.sub(r'\'\s*\}', '"}', json_propre)
    
    # Échapper les backslashes
    json_propre = json_propre.replace('\\', '\\\\')
    
    return json_propre

def parser_resultats_json(json_data, fichier_nom):
    """Parse les résultats d'un fichier JSON"""
    resultats = []
    
    try:
        # Vérifier si c'est une fonction wrapper
        if isinstance(json_data, dict) and len(json_data) == 1:
            func_name = list(json_data.keys())[0]
            data = json_data[func_name]
        else:
            data = json_data
        
        # Vérifier s'il y a une erreur
        if 'error' in data:
            st.warning(f"⚠️ Erreur dans {fichier_nom}: {data.get('error', {}).get('message', 'Erreur inconnue')}")
            return [], {}
        
        # Récupérer les infos de pagination
        cursor_info = data.get('cursor', {})
        
        # Extraire les résultats
        items = []
        if 'results' in data:
            items = data['results']
        elif 'items' in data:
            items = data['items']
        
        st.info(f"📄 {fichier_nom}: {len(items)} résultats trouvés")
        
        for i, item in enumerate(items):
            try:
                # Extraire les informations
                titre = item.get('title', item.get('titleNoFormatting', f'Document {i+1}'))
                url = item.get('url', item.get('unescapedUrl', item.get('link', '')))
                description = item.get('contentNoFormatting', 
                                     item.get('content', 
                                     item.get('snippet', '')))
                
                # Nettoyer les entités HTML
                if description:
                    description = description.replace('\\u003cb\\u003e', '').replace('\\u003c/b\\u003e', '')
                    description = description.replace('&#39;', "'").replace('&nbsp;', ' ')
                    description = description.replace('&quot;', '"')
                
                # Extraire la date
                date_doc = "Date inconnue"
                if description:
                    date_match = re.search(r'(\d{1,2}\s+[a-zéû]+\s+\d{4}|\d{4})', description, re.IGNORECASE)
                    if date_match:
                        date_doc = date_match.group(1)
                
                # Détecter le type de document
                type_doc = "Document"
                file_format = item.get('fileFormat', '')
                
                if '.pdf' in url.lower() or 'PDF' in file_format:
                    type_doc = "PDF"
                elif 'archives.assemblee-nationale.fr' in url:
                    if '/cri/' in url:
                        type_doc = "Compte rendu"
                    elif 'journal' in titre.lower() or 'JOURNAL' in titre:
                        type_doc = "Journal Officiel"
                    elif 'constitution' in titre.lower():
                        type_doc = "Constitution"
                    elif '/qst/' in url:
                        type_doc = "Question"
                
                # Extraire la législature
                legislature = ""
                if url:
                    leg_match_url = re.search(r'/(\d+)/cri/', url)
                    if leg_match_url:
                        legislature = leg_match_url.group(1)
                    else:
                        leg_match_url = re.search(r'/(\d+)/qst/', url)
                        if leg_match_url:
                            legislature = leg_match_url.group(1)
                
                if not legislature and titre:
                    leg_match_title = re.search(r'(\d+)[\'°]?\s+Législature', titre)
                    if leg_match_title:
                        legislature = leg_match_title.group(1)
                
                # Extraire les années
                periode = "Inconnue"
                if url:
                    annee_match = re.search(r'/(\d{4})-(\d{4})', url)
                    if annee_match:
                        periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                    else:
                        annee_match = re.search(r'/(\d{4})/', url)
                        if annee_match:
                            periode = annee_match.group(1)
                
                if periode == "Inconnue" and description:
                    annee_match = re.search(r'(\d{4})\s*-\s*(\d{4})', description)
                    if annee_match:
                        periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                    else:
                        annee_match = re.search(r'(\d{4})', date_doc)
                        if annee_match:
                            annee = annee_match.group(1)
                            periode = f"{annee}"
                
                # Score de pertinence
                score = item.get('score', 100 - (i * 2) if i < 50 else 10)
                
                # Métadonnées
                metadonnees = {}
                if 'richSnippet' in item:
                    metadonnees = item['richSnippet']
                
                # Source du fichier
                source_fichier = fichier_nom
                
                resultats.append({
                    'id': f"{fichier_nom.replace('.txt', '')}_R{i+1:03d}",
                    'fichier_source': source_fichier,
                    'titre': titre[:150] + "..." if len(titre) > 150 else titre,
                    'url': url,
                    'description': description[:200] + "..." if description and len(description) > 200 else description,
                    'type': type_doc,
                    'legislature': legislature,
                    'periode': periode,
                    'date_doc': date_doc,
                    'position': i + 1,
                    'score': score,
                    'format': file_format,
                    'visible_url': item.get('visibleUrl', ''),
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                st.warning(f"Erreur sur l'élément {i+1} du fichier {fichier_nom}: {str(e)}")
                continue
        
        return resultats, cursor_info
        
    except Exception as e:
        st.error(f"Erreur lors du parsing de {fichier_nom}: {str(e)}")
        return [], {}

def analyser_tous_fichiers(fichiers):
    """Analyse tous les fichiers JSON"""
    tous_resultats = []
    stats_fichiers = []
    
    for fichier_info in fichiers:
        with st.spinner(f"Analyse de {fichier_info['nom']}..."):
            json_data = extraire_json_du_contenu(fichier_info['contenu'])
            
            if json_data:
                resultats, cursor_info = parser_resultats_json(json_data, fichier_info['nom'])
                
                if resultats:
                    tous_resultats.extend(resultats)
                    
                    stats = {
                        'fichier': fichier_info['nom'],
                        'resultats': len(resultats),
                        'estimated': cursor_info.get('estimatedResultCount', '0'),
                        'pages': len(cursor_info.get('pages', [])),
                        'search_time': cursor_info.get('searchResultTime', '0'),
                        'page_index': cursor_info.get('currentPageIndex', 0)
                    }
                    stats_fichiers.append(stats)
    
    return tous_resultats, stats_fichiers

# ==================== INTERFACE STREAMLIT ====================

# Initialisation du state
if 'resultats_complets' not in st.session_state:
    st.session_state.resultats_complets = []
if 'stats_fichiers' not in st.session_state:
    st.session_state.stats_fichiers = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Bouton pour analyser tous les fichiers
    if st.button("📁 ANALYSER LES 9 FICHIERS JSON", type="primary", use_container_width=True):
        with st.spinner("Chargement et analyse des 9 fichiers en cours..."):
            # Charger les fichiers
            fichiers = charger_fichiers_json()
            
            if fichiers:
                st.success(f"✅ {len(fichiers)} fichiers chargés")
                
                # Analyser tous les fichiers
                tous_resultats, stats_fichiers = analyser_tous_fichiers(fichiers)
                
                if tous_resultats:
                    st.session_state.resultats_complets = tous_resultats
                    st.session_state.stats_fichiers = stats_fichiers
                    
                    st.success(f"🎉 ANALYSE COMPLÈTE: {len(tous_resultats)} résultats extraits au total!")
                    
                    # Afficher les statistiques par fichier
                    with st.expander("📊 Statistiques par fichier", expanded=True):
                        for stat in stats_fichiers:
                            st.write(f"**{stat['fichier']}**: {stat['resultats']} résultats (page {stat['page_index']})")
                else:
                    st.error("❌ Aucun résultat trouvé dans les fichiers")
            else:
                st.error("❌ Aucun fichier JSON trouvé")
    
    # Afficher les statistiques si des données existent
    if st.session_state.resultats_complets:
        st.divider()
        st.subheader("📊 Statistiques globales")
        total = len(st.session_state.resultats_complets)
        
        # Compter les types
        types_counts = Counter([r['type'] for r in st.session_state.resultats_complets])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total résultats", total)
        with col2:
            st.metric("Fichiers analysés", len(st.session_state.stats_fichiers))
        
        st.write("**Types trouvés:**")
        for type_name, count in types_counts.most_common(5):
            st.write(f"- {type_name}: {count}")

# Contenu principal
if st.session_state.resultats_complets:
    donnees = st.session_state.resultats_complets
    df = pd.DataFrame(donnees)
    stats_df = pd.DataFrame(st.session_state.stats_fichiers)
    
    # ==================== VUE D'ENSEMBLE ====================
    st.header("📈 Vue d'ensemble des 9 Fichiers JSON")
    
    # Statistiques globales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents totaux", len(df))
    with col2:
        fichiers_uniques = df['fichier_source'].nunique()
        st.metric("Fichiers analysés", fichiers_uniques)
    with col3:
        types_uniques = df['type'].nunique()
        st.metric("Types de documents", types_uniques)
    with col4:
        annees_uniques = df['periode'].nunique()
        st.metric("Périodes uniques", annees_uniques)
    
    # ==================== STATISTIQUES PAR FICHIER ====================
    st.subheader("📊 Statistiques par fichier")
    
    if not stats_df.empty:
        # Graphique des résultats par fichier
        fig = px.bar(
            stats_df.sort_values('page_index'),
            x='fichier',
            y='resultats',
            title="Nombre de résultats par fichier",
            labels={'fichier': 'Fichier', 'resultats': 'Nombre de résultats'},
            color='page_index',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau des statistiques
        st.dataframe(
            stats_df[['fichier', 'resultats', 'page_index', 'estimated', 'pages', 'search_time']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "fichier": st.column_config.TextColumn("Fichier"),
                "resultats": st.column_config.NumberColumn("Résultats", format="%d"),
                "page_index": st.column_config.NumberColumn("Page", format="%d"),
                "estimated": st.column_config.TextColumn("Estimé"),
                "pages": st.column_config.NumberColumn("Pages", format="%d"),
                "search_time": st.column_config.TextColumn("Temps")
            }
        )
    
    # ==================== TABLEAU COMPLET ====================
    st.header("📄 Tableau complet de tous les résultats")
    
    # Filtres
    with st.expander("🔍 Filtres avancés", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            types = sorted(df['type'].unique())
            types_selection = st.multiselect("Types de documents", types, default=types)
        
        with col2:
            fichiers = sorted(df['fichier_source'].unique())
            fichiers_selection = st.multiselect("Fichiers source", fichiers, default=fichiers)
        
        with col3:
            legislatures = sorted([l for l in df['legislature'].unique() if l])
            leg_selection = st.multiselect("Législatures", legislatures, default=legislatures)
    
    # Filtres supplémentaires
    col1, col2 = st.columns(2)
    with col1:
        periodes = sorted([p for p in df['periode'].unique() if p != "Inconnue"])
        periode_selection = st.multiselect("Périodes", periodes, default=periodes[:5] if len(periodes) > 5 else periodes)
    
    with col2:
        min_score, max_score = st.slider(
            "Plage de score",
            min_value=0,
            max_value=100,
            value=(30, 100),
            step=5
        )
    
    # Appliquer les filtres
    df_filtre = df[
        (df['type'].isin(types_selection)) &
        (df['fichier_source'].isin(fichiers_selection)) &
        (df['legislature'].isin(leg_selection) | (df['legislature'] == '')) &
        (df['periode'].isin(periode_selection) | (df['periode'] == "Inconnue") if periode_selection else True) &
        (df['score'] >= min_score) &
        (df['score'] <= max_score)
    ]
    
    # Informations sur le filtrage
    st.info(f"📋 Affichage de {len(df_filtre)} documents sur {len(df)} ({len(df_filtre)/len(df)*100:.1f}%)")
    
    # Options d'affichage
    col1, col2 = st.columns(2)
    with col1:
        items_per_page = st.selectbox("Résultats par page", [10, 25, 50, 100], index=1)
    with col2:
        tri_par = st.selectbox("Trier par", ['fichier_source', 'position', 'score', 'periode', 'type'], index=0)
        ordre_tri = st.selectbox("Ordre", ['ascendant', 'descendant'], index=0)
    
    # Trier les données
    df_filtre_trie = df_filtre.sort_values(
        tri_par, 
        ascending=(ordre_tri == 'ascendant')
    )
    
    # Pagination
    total_pages = max(1, (len(df_filtre_trie) + items_per_page - 1) // items_per_page)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(df_filtre_trie))
    
    df_page = df_filtre_trie.iloc[start_idx:end_idx]
    
    st.write(f"**Page {page}/{total_pages}** ({start_idx+1}-{end_idx} sur {len(df_filtre_trie)})")
    
    # Afficher le tableau
    st.dataframe(
        df_page[['id', 'fichier_source', 'titre', 'type', 'legislature', 'periode', 'score']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "fichier_source": st.column_config.TextColumn("Fichier", width="medium"),
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "type": st.column_config.TextColumn("Type"),
            "legislature": st.column_config.TextColumn("Législature"),
            "periode": st.column_config.TextColumn("Période"),
            "score": st.column_config.NumberColumn("Score", format="%d")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.header("📊 Analyses visuelles complètes")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Chronologie", "📊 Distribution", "🌐 Sources", "📈 Relations"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Graphique par période
            if 'periode' in df_filtre.columns and not df_filtre.empty:
                period_data = df_filtre[df_filtre['periode'] != "Inconnue"]
                if len(period_data) > 0:
                    period_counts = period_data['periode'].value_counts().head(15)
                    
                    fig = px.bar(
                        x=period_counts.index,
                        y=period_counts.values,
                        title=f"Top 15 des périodes",
                        labels={'x': 'Période', 'y': 'Nombre'},
                        color=period_counts.values,
                        color_continuous_scale='Viridis'
                    )
                    fig.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Analyse par fichier
            if 'fichier_source' in df_filtre.columns:
                file_counts = df_filtre['fichier_source'].value_counts()
                
                fig = px.bar(
                    x=file_counts.index,
                    y=file_counts.values,
                    title="Documents par fichier",
                    labels={'x': 'Fichier', 'y': 'Nombre'},
                    color=file_counts.values,
                    color_continuous_scale='Blues'
                )
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution par type
            type_counts = df_filtre['type'].value_counts()
            if len(type_counts) > 0:
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="Distribution par type",
                    hole=0.3
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution par législature
            leg_data = df_filtre[df_filtre['legislature'] != '']
            if len(leg_data) > 0:
                leg_counts = leg_data['legislature'].value_counts()
                if len(leg_counts) > 0:
                    fig = px.bar(
                        x=leg_counts.index.astype(str),
                        y=leg_counts.values,
                        title="Documents par législature",
                        labels={'x': 'Législature', 'y': 'Nombre'},
                        color=leg_counts.values,
                        color_continuous_scale='Greens'
                    )
                    fig.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            # Analyse des domaines
            if 'visible_url' in df_filtre.columns:
                domain_data = df_filtre[df_filtre['visible_url'] != '']
                if len(domain_data) > 0:
                    domain_counts = domain_data['visible_url'].value_counts().head(10)
                    
                    fig = px.bar(
                        x=domain_counts.index,
                        y=domain_counts.values,
                        title="Top 10 des domaines",
                        labels={'x': 'Domaine', 'y': 'Documents'},
                        color=domain_counts.values,
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution par fichier et type
            if len(df_filtre) > 0:
                pivot = pd.crosstab(df_filtre['fichier_source'], df_filtre['type'])
                fig = px.imshow(
                    pivot,
                    title="Répartition Type × Fichier",
                    labels=dict(x="Type", y="Fichier", color="Nombre"),
                    color_continuous_scale='YlOrRd'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            # Score vs Position
            if 'score' in df_filtre.columns and 'position' in df_filtre.columns:
                fig = px.scatter(
                    df_filtre,
                    x='position',
                    y='score',
                    title="Score vs Position",
                    labels={'position': 'Position', 'score': 'Score'},
                    color='fichier_source',
                    size_max=15
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution des scores
            if 'score' in df_filtre.columns:
                fig = px.histogram(
                    df_filtre,
                    x='score',
                    nbins=20,
                    title="Distribution des scores",
                    labels={'score': 'Score de pertinence'},
                    color_discrete_sequence=['#FF6B6B']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    # ==================== DÉTAILS DES DOCUMENTS ====================
    st.header("🔍 Détails par document")
    
    if not df_filtre.empty:
        # Sélection d'un document
        selected_doc = st.selectbox(
            "Choisir un document à examiner",
            options=df_filtre['id'].unique(),
            format_func=lambda x: f"{x} - {df_filtre[df_filtre['id']==x]['titre'].iloc[0][:50]}..."
        )
        
        if selected_doc:
            doc = df_filtre[df_filtre['id'] == selected_doc].iloc[0]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {doc['titre']}")
                
                # Métadonnées
                st.markdown("**📋 Informations:**")
                
                meta_cols = st.columns(4)
                with meta_cols[0]:
                    st.metric("Type", doc['type'])
                with meta_cols[1]:
                    st.metric("Fichier source", doc['fichier_source'])
                with meta_cols[2]:
                    st.metric("Législature", doc['legislature'] or "N/A")
                with meta_cols[3]:
                    st.metric("Score", int(doc['score']))
                
                # Période et position
                st.markdown("**📅 Détails:**")
                detail_cols = st.columns(3)
                with detail_cols[0]:
                    st.write(f"**Période:** {doc['periode']}")
                with detail_cols[1]:
                    st.write(f"**Date document:** {doc['date_doc']}")
                with detail_cols[2]:
                    st.write(f"**Position:** {doc['position']}")
                
                # Description
                if doc['description'] and doc['description'] != 'None':
                    st.markdown("**📝 Extrait:**")
                    st.info(doc['description'])
                
                # URL
                if doc['url'] and doc['url'] != 'None':
                    st.markdown("**🔗 URL originale:**")
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
                st.markdown("**⚙️ Détails techniques:**")
                st.write(f"**Format:** {doc['format']}")
                st.write(f"**Domaine:** {doc['visible_url']}")
                st.write(f"**Timestamp:** {doc['timestamp'][:19]}")
                
                # Informations sur la source
                st.markdown("**📁 Source:**")
                st.write(f"Fichier: {doc['fichier_source']}")
                st.write(f"ID complet: {doc['id']}")
    
    # ==================== EXPORT COMPLET ====================
    st.header("💾 Export COMPLET des données")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Export CSV complet
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 CSV COMPLET",
            data=csv,
            file_name=f"9_fichiers_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON structuré
        json_data = json.dumps(donnees, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON STRUCTURÉ",
            data=json_data,
            file_name=f"9_fichiers_analyse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Export URLs seulement
        urls = [d['url'] for d in donnees if d['url'] and d['url'] != 'None']
        urls_text = "\n".join(urls)
        st.download_button(
            label="📄 LISTE DES URLs",
            data=urls_text.encode('utf-8'),
            file_name=f"urls_9_fichiers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col4:
        # Export statistiques
        stats_csv = stats_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 STATISTIQUES",
            data=stats_csv,
            file_name=f"stats_9_fichiers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("🔍 Analyseur des 9 Fichiers JSON Google CSE")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 À propos
        Ce dashboard analyse **TOUS les résultats** des **9 fichiers JSON** 
        que vous avez fournis.
        
        ### ✅ FONCTIONNALITÉS
        - **Chargement automatique** des 9 fichiers
        - **Extraction complète** de tous les résultats
        - **Analyse comparative** entre fichiers
        - **Visualisations** interactives
        - **Filtres avancés** par fichier, type, période
        - **Export** multi-formats
        
        ### 📋 CE QUI SERA ANALYSÉ
        - **json(1).txt** à **json(9).txt**
        - **Tous les résultats** de chaque fichier
        - **Métadonnées** complètes
        - **Statistiques comparatives**
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 COMMENT PROCÉDER
        1. **Assurez-vous** que les 9 fichiers sont dans le même dossier
        2. **Cliquez** sur "ANALYSER LES 9 FICHIERS JSON"
        3. **Attendez** l'analyse complète
        4. **Explorez** tous les résultats
        5. **Comparez** les fichiers entre eux
        6. **Exportez** les données complètes
        
        ### 📁 FICHIERS ATTENDUS
        - json(1).txt
        - json(2).txt
        - json(3).txt
        - json(4).txt
        - json(5).txt
        - json(6).txt
        - json(7).txt
        - json(8).txt
        - json(9).txt
        
        ### ⚠️ ATTENTION
        Si certains fichiers sont manquants, 
        le dashboard analysera ceux qui sont présents.
        """)
    
    # Instructions pour les fichiers
    with st.expander("📁 STRUCTURE DES FICHIERS ATTENDUS", expanded=True):
        st.markdown("""
        ### Structure des fichiers attendus :
        
        ```
        json(1).txt  → Page 1 (résultats 1-10)
        json(2).txt  → Page 2 (résultats 11-20)
        json(3).txt  → Page 3 (résultats 21-30)
        json(4).txt  → Page 4 (résultats 31-40)
        json(5).txt  → Page 5 (résultats 41-50)
        json(6).txt  → Page 6 (résultats 51-60)
        json(7).txt  → Page 7 (résultats 61-70)
        json(8).txt  → Page 8 (résultats 71-80)
        json(9).txt  → Page 9 (résultats 81-90)
        ```
        
        ### Format de chaque fichier :
        ```
        /*O_o*/
        google.search.cse.apiXXXX({
          "cursor": { ... },
          "results": [ ... ]
        });
        ```
        """)
    
    # Vérification des fichiers
    st.divider()
    st.subheader("🔍 Vérification des fichiers")
    
    if st.button("Vérifier les fichiers disponibles"):
        fichiers = charger_fichiers_json()
        if fichiers:
            st.success(f"✅ {len(fichiers)} fichiers détectés")
            for f in fichiers:
                st.write(f"- {f['nom']} ({f['taille']:,} caractères)")
        else:
            st.error("❌ Aucun fichier JSON détecté")
            st.info("Placez les fichiers json(1).txt à json(9).txt dans le même dossier que ce script")

# ==================== PIED DE PAGE ====================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard d'analyse des 9 Fichiers JSON Google CSE • Analyse comparative • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
