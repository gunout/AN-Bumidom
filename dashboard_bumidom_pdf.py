import streamlit as st
import requests
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import time
import re
import os

# ==================== CONFIGURATION ====================
st.set_page_config(page_title="Dashboard API Google CSE", layout="wide")
st.title("🔍 Dashboard API - Archives Assemblée Nationale")
st.markdown("**Analyse COMPLÈTE des données JSON Google CSE**")

# ==================== FONCTIONS PRINCIPALES ====================

def parser_json_google_cse_complet(json_data):
    """Parse COMPLÈTEMENT les données JSON de l'API Google CSE"""
    resultats = []
    
    try:
        # Vérifier si c'est une fonction wrapper comme dans le fichier
        if isinstance(json_data, dict) and len(json_data) == 1:
            # Extraire les données de la fonction wrapper
            func_name = list(json_data.keys())[0]
            data = json_data[func_name]
        else:
            data = json_data
        
        # Récupérer les infos de pagination
        cursor_info = data.get('cursor', {})
        estimated_count = cursor_info.get('estimatedResultCount', '0')
        actual_count = cursor_info.get('resultCount', '0')
        pages = cursor_info.get('pages', [])
        
        st.info(f"📊 Résultats estimés: {estimated_count}, Pages disponibles: {len(pages)}")
        
        # Extraire TOUS les résultats
        items = []
        if 'results' in data:
            items = data['results']
        elif 'items' in data:
            items = data['items']
        else:
            # Chercher dans toute la structure
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict):
                        items = value
                        break
        
        st.info(f"✅ {len(items)} résultats trouvés dans le JSON")
        
        for i, item in enumerate(items):
            try:
                # Extraire les informations selon la structure Google CSE
                titre = item.get('title', item.get('titleNoFormatting', f'Document {i+1}'))
                url = item.get('url', item.get('unescapedUrl', item.get('link', '')))
                description = item.get('contentNoFormatting', 
                                     item.get('content', 
                                     item.get('snippet', '')))
                
                # Nettoyer les entités HTML
                if description:
                    description = description.replace('\\u003cb\\u003e', '').replace('\\u003c/b\\u003e', '')
                    description = description.replace('&#39;', "'").replace('&nbsp;', ' ')
                
                # Extraire la date depuis le contenu
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
                
                # Extraire la législature depuis l'URL ou le titre
                legislature = ""
                if url:
                    leg_match_url = re.search(r'/(\d+)/cri/', url)
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
                
                if periode == "Inconnue" and description:
                    annee_match = re.search(r'(\d{4})\s*-\s*(\d{4})', description)
                    if annee_match:
                        periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                    else:
                        annee_match = re.search(r'(\d{4})', date_doc)
                        if annee_match:
                            annee = annee_match.group(1)
                            periode = f"{annee}"
                
                # Score de pertinence basé sur la position
                score = 100 - (i * 2) if i < 50 else 10
                
                # Métadonnées enrichies
                metadonnees = {}
                if 'richSnippet' in item:
                    metadonnees = item['richSnippet']
                if 'breadcrumbUrl' in item:
                    metadonnees['breadcrumbs'] = item['breadcrumbUrl'].get('crumbs', [])
                
                resultats.append({
                    'id': f"R{i+1:03d}",
                    'titre': titre[:200] + "..." if len(titre) > 200 else titre,
                    'url': url,
                    'description': description[:300] + "..." if description and len(description) > 300 else description,
                    'type': type_doc,
                    'legislature': legislature,
                    'periode': periode,
                    'date_doc': date_doc,
                    'position': i + 1,
                    'score': item.get('score', score),
                    'format': file_format,
                    'visible_url': item.get('visibleUrl', ''),
                    'metadonnees': json.dumps(metadonnees) if metadonnees else '',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                st.warning(f"Erreur sur l'élément {i+1}: {str(e)}")
                continue
        
        return resultats, cursor_info
        
    except Exception as e:
        st.error(f"Erreur lors du parsing JSON: {str(e)}")
        return [], {}

def extraire_donnees_brutes_du_fichier():
    """Extrait toutes les données brutes du fichier JSON"""
    try:
        # Vérifier si le fichier existe
        if not os.path.exists('json.txt'):
            st.error("❌ Fichier 'json.txt' non trouvé dans le répertoire courant")
            st.info("Assurez-vous que votre fichier JSON complet est nommé 'json.txt'")
            return None
        
        # Lire le fichier
        with open('json.txt', 'r', encoding='utf-8') as f:
            contenu_brut = f.read()
        
        st.info(f"📁 Fichier chargé: {len(contenu_brut)} caractères")
        
        # Essayer de trouver et extraire le JSON
        # Chercher le pattern google.search.cse.apiXXXX({
        pattern = r'google\.search\.cse\.api\d+\(\s*({.*})\);?\s*$'
        match = re.search(pattern, contenu_brut, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            st.success("✅ Structure Google CSE détectée")
        else:
            # Essayer de trouver juste les accolades
            start_idx = contenu_brut.find('{')
            end_idx = contenu_brut.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = contenu_brut[start_idx:end_idx]
                st.success("✅ JSON brut extrait")
            else:
                st.error("❌ Format JSON non reconnu")
                return None
        
        # Parser le JSON
        try:
            json_data = json.loads(json_str)
            st.success(f"✅ JSON parsé avec succès")
            return json_data
        except json.JSONDecodeError as e:
            st.error(f"❌ Erreur de parsing JSON: {e}")
            st.info("Essayer de nettoyer le JSON...")
            
            # Nettoyer le JSON
            json_str_nettoye = nettoyer_json(contenu_brut)
            
            try:
                json_data = json.loads(json_str_nettoye)
                st.success("✅ JSON nettoyé et parsé")
                return json_data
            except:
                st.error("❌ Impossible de parser le JSON même après nettoyage")
                return None
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
        return None

def nettoyer_json(json_brut):
    """Nettoie le JSON brut"""
    # Supprimer les commentaires
    json_propre = re.sub(r'/\*.*?\*/', '', json_brut, flags=re.DOTALL)
    
    # Supprimer les parties avant et après les accolades
    start_idx = json_propre.find('{')
    end_idx = json_propre.rfind('}') + 1
    
    if start_idx != -1 and end_idx > start_idx:
        json_propre = json_propre[start_idx:end_idx]
    
    # Remplacer les simples quotes par des doubles quotes pour les clés
    json_propre = re.sub(r'(\w+):\s*\'', r'\1: "', json_propre)
    json_propre = re.sub(r'\',', '",', json_propre)
    json_propre = re.sub(r'\'}$', '"}', json_propre)
    
    # Échapper les backslashes
    json_propre = json_propre.replace('\\', '\\\\')
    
    return json_propre

def analyser_structure_json(json_data):
    """Analyse la structure du JSON pour comprendre son contenu"""
    if not json_data:
        return {}
    
    analyse = {
        'niveau_1': [],
        'niveau_2': [],
        'types_donnees': {},
        'taille_estimee': 0
    }
    
    # Analyser le premier niveau
    for key, value in json_data.items():
        analyse['niveau_1'].append(key)
        
        if isinstance(value, dict):
            analyse['types_donnees'][key] = 'dict'
            analyse['niveau_2'].extend(list(value.keys()))
        elif isinstance(value, list):
            analyse['types_donnees'][key] = f'list[{len(value)}]'
            if value and isinstance(value[0], dict):
                analyse['niveau_2'].extend(list(value[0].keys()))
        else:
            analyse['types_donnees'][key] = type(value).__name__
    
    # Estimer la taille
    json_str = json.dumps(json_data)
    analyse['taille_estimee'] = len(json_str)
    
    return analyse

# ==================== INTERFACE STREAMLIT ====================

# Initialisation du state
if 'donnees_json_brutes' not in st.session_state:
    st.session_state.donnees_json_brutes = None
if 'resultats_complets' not in st.session_state:
    st.session_state.resultats_complets = []
if 'cursor_info' not in st.session_state:
    st.session_state.cursor_info = {}

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Options
    st.subheader("Options d'analyse")
    
    # Bouton pour analyser le fichier complet
    if st.button("📁 ANALYSER LE FICHIER JSON COMPLET", type="primary", use_container_width=True):
        with st.spinner("Extraction et analyse en cours..."):
            # Extraire les données brutes
            json_data = extraire_donnees_brutes_du_fichier()
            
            if json_data:
                st.session_state.donnees_json_brutes = json_data
                
                # Analyser la structure
                analyse = analyser_structure_json(json_data)
                
                # Parser les résultats
                resultats, cursor_info = parser_json_google_cse_complet(json_data)
                st.session_state.resultats_complets = resultats
                st.session_state.cursor_info = cursor_info
                
                # Afficher les statistiques
                estimated_count = cursor_info.get('estimatedResultCount', '0')
                actual_count = len(resultats)
                pages_count = len(cursor_info.get('pages', []))
                
                st.success(f"✅ ANALYSE COMPLÈTE: {actual_count} résultats extraits!")
                st.info(f"📊 Estimation Google: {estimated_count} résultats")
                st.info(f"📑 Pages disponibles: {pages_count}")
                
                # Afficher l'analyse structurelle
                with st.expander("🔍 Analyse structurelle", expanded=False):
                    st.write("**Niveau 1:**")
                    for item in analyse['niveau_1']:
                        st.write(f"- {item} ({analyse['types_donnees'].get(item, 'inconnu')})")
                    
                    if analyse['niveau_2']:
                        st.write("**Niveau 2 (échantillon):**")
                        for item in analyse['niveau_2'][:10]:
                            st.write(f"- {item}")
                    
                    st.write(f"**Taille estimée:** {analyse['taille_estimee']:,} caractères")
            else:
                st.error("❌ Impossible d'extraire les données du fichier")
    
    # Afficher les statistiques si des données existent
    if st.session_state.resultats_complets:
        st.divider()
        st.subheader("📊 Statistiques")
        total = len(st.session_state.resultats_complets)
        
        # Compter les types
        types_counts = {}
        for r in st.session_state.resultats_complets:
            types_counts[r['type']] = types_counts.get(r['type'], 0) + 1
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Résultats", total)
        with col2:
            st.metric("Types", len(types_counts))
        
        # Liste des types
        st.write("**Types trouvés:**")
        for type_name, count in types_counts.items():
            st.write(f"- {type_name}: {count}")

# Contenu principal
if st.session_state.resultats_complets:
    donnees = st.session_state.resultats_complets
    df = pd.DataFrame(donnees)
    
    # ==================== VUE D'ENSEMBLE ====================
    st.header("📈 Vue d'ensemble COMPLÈTE")
    
    # Informations sur les données
    estimated_count = st.session_state.cursor_info.get('estimatedResultCount', '0')
    pages_count = len(st.session_state.cursor_info.get('pages', []))
    search_time = st.session_state.cursor_info.get('searchResultTime', '0')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents extraits", len(df))
    with col2:
        st.metric("Estimé Google", estimated_count)
    with col3:
        st.metric("Pages", pages_count)
    with col4:
        st.metric("Temps recherche", f"{search_time}s")
    
    # Statistiques par type
    st.subheader("📊 Répartition par type")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pdf_count = df[df['type'] == 'PDF'].shape[0]
        st.metric("PDF", pdf_count)
    with col2:
        cr_count = df[df['type'] == 'Compte rendu'].shape[0]
        st.metric("Comptes rendus", cr_count)
    with col3:
        jo_count = df[df['type'] == 'Journal Officiel'].shape[0]
        st.metric("Journaux Officiels", jo_count)
    with col4:
        constitution_count = df[df['type'] == 'Constitution'].shape[0]
        st.metric("Constitutions", constitution_count)
    
    # ==================== TABLEAU COMPLET ====================
    st.header("📄 Tableau complet des résultats")
    
    # Filtres
    with st.expander("🔍 Filtres avancés", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            types = sorted(df['type'].unique())
            types_selection = st.multiselect("Types de documents", types, default=types)
        
        with col2:
            legislatures = sorted([l for l in df['legislature'].unique() if l])
            leg_selection = st.multiselect("Législatures", legislatures, default=legislatures)
        
        with col3:
            periodes = sorted([p for p in df['periode'].unique() if p != "Inconnue"])
            periode_selection = st.multiselect("Périodes", periodes, default=periodes[:10] if len(periodes) > 10 else periodes)
    
    # Filtre par score
    with st.expander("🎯 Filtre par score", expanded=False):
        min_score, max_score = st.slider(
            "Plage de score",
            min_value=0,
            max_value=100,
            value=(50, 100),
            step=5
        )
    
    # Appliquer les filtres
    df_filtre = df[
        (df['type'].isin(types_selection)) &
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
        tri_par = st.selectbox("Trier par", ['position', 'score', 'periode', 'legislature'], index=0)
        ordre_tri = st.selectbox("Ordre", ['ascendant', 'descendant'], index=1)
    
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
        df_page[['id', 'titre', 'type', 'legislature', 'periode', 'date_doc', 'score', 'visible_url']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "type": st.column_config.TextColumn("Type"),
            "legislature": st.column_config.TextColumn("Législature"),
            "periode": st.column_config.TextColumn("Période"),
            "date_doc": st.column_config.TextColumn("Date"),
            "score": st.column_config.NumberColumn("Score", format="%d"),
            "visible_url": st.column_config.TextColumn("Domaine")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.header("📊 Analyses visuelles complètes")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Chronologie", "📊 Distribution", "🌐 Sources", "🎯 Scores", "📈 Tendances"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Graphique par période
            if 'periode' in df_filtre.columns and not df_filtre.empty:
                period_data = df_filtre[df_filtre['periode'] != "Inconnue"]
                if len(period_data) > 0:
                    period_counts = period_data['periode'].value_counts().head(20)
                    
                    fig = px.bar(
                        x=period_counts.index,
                        y=period_counts.values,
                        title=f"Top 20 des périodes ({len(period_counts)} au total)",
                        labels={'x': 'Période', 'y': 'Nombre'},
                        color=period_counts.values,
                        color_continuous_scale='Viridis'
                    )
                    fig.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Analyse par année
            if 'periode' in df_filtre.columns:
                # Extraire l'année de début
                def extract_year(periode):
                    match = re.search(r'(\d{4})', str(periode))
                    return int(match.group(1)) if match else None
                
                df_filtre['annee'] = df_filtre['periode'].apply(extract_year)
                df_annee = df_filtre.dropna(subset=['annee'])
                
                if len(df_annee) > 0:
                    year_counts = df_annee['annee'].value_counts().sort_index()
                    
                    fig = px.line(
                        x=year_counts.index,
                        y=year_counts.values,
                        title="Évolution par année",
                        labels={'x': 'Année', 'y': 'Documents'},
                        markers=True
                    )
                    fig.update_traces(line=dict(width=3))
                    fig.update_layout(height=400)
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
                        color_continuous_scale='Blues'
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
                    domain_counts = domain_data['visible_url'].value_counts().head(15)
                    
                    fig = px.bar(
                        x=domain_counts.index,
                        y=domain_counts.values,
                        title="Top 15 des domaines",
                        labels={'x': 'Domaine', 'y': 'Documents'},
                        color=domain_counts.values,
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution des formats
            if 'format' in df_filtre.columns:
                format_data = df_filtre[df_filtre['format'] != '']
                if len(format_data) > 0:
                    format_counts = format_data['format'].value_counts()
                    
                    fig = px.pie(
                        values=format_counts.values,
                        names=format_counts.index,
                        title="Distribution des formats",
                        hole=0.3
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
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
        
        with col2:
            # Score vs Position
            if 'score' in df_filtre.columns and 'position' in df_filtre.columns:
                fig = px.scatter(
                    df_filtre,
                    x='position',
                    y='score',
                    title="Score vs Position",
                    labels={'position': 'Position', 'score': 'Score'},
                    trendline="lowess",
                    color='type'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        # Analyses temporelles avancées
        if 'periode' in df_filtre.columns and 'score' in df_filtre.columns:
            # Extraire l'année
            def extract_start_year(periode):
                match = re.search(r'(\d{4})', str(periode))
                return int(match.group(1)) if match else None
            
            df_filtre['annee_debut'] = df_filtre['periode'].apply(extract_start_year)
            df_annee = df_filtre.dropna(subset=['annee_debut'])
            
            if len(df_annee) > 0:
                # Score moyen par année
                score_par_annee = df_annee.groupby('annee_debut')['score'].mean().reset_index()
                
                fig = px.line(
                    x=score_par_annee['annee_debut'],
                    y=score_par_annee['score'],
                    title="Score moyen par année",
                    labels={'x': 'Année', 'y': 'Score moyen'},
                    markers=True
                )
                fig.update_traces(line=dict(width=3))
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    # ==================== DÉTAILS DES DOCUMENTS ====================
    st.header("🔍 Détails par document")
    
    if not df_filtre.empty:
        # Sélection d'un document avec recherche
        col1, col2 = st.columns([3, 1])
        
        with col1:
            recherche = st.text_input("Rechercher dans les titres", "")
        
        with col2:
            if recherche:
                options_filtrees = [(row['id'], row['titre']) for _, row in df_filtre.iterrows() 
                                  if recherche.lower() in row['titre'].lower()]
            else:
                options_filtrees = [(row['id'], f"{row['id']} - {row['titre'][:80]}...") 
                                  for _, row in df_filtre.iterrows()]
        
        if options_filtrees:
            selected_option = st.selectbox(
                "Choisir un document",
                options=[opt[0] for opt in options_filtrees],
                format_func=lambda x: dict(options_filtrees).get(x, x)
            )
            
            if selected_option:
                doc = df_filtre[df_filtre['id'] == selected_option].iloc[0]
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {doc['titre']}")
                    
                    # Métadonnées
                    st.markdown("**📋 Informations:**")
                    
                    meta_cols = st.columns(4)
                    with meta_cols[0]:
                        st.metric("Type", doc['type'])
                    with meta_cols[1]:
                        st.metric("Législature", doc['legislature'] or "N/A")
                    with meta_cols[2]:
                        st.metric("Période", doc['periode'])
                    with meta_cols[3]:
                        st.metric("Score", int(doc['score']))
                    
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
                    st.markdown("**⚙️ Détails:**")
                    st.metric("Position", doc['position'])
                    st.metric("Date", doc['date_doc'])
                    st.metric("Domaine", doc['visible_url'])
                    
                    # Informations supplémentaires
                    with st.expander("Plus d'infos"):
                        st.write(f"**Format:** {doc['format']}")
                        st.write(f"**ID:** {doc['id']}")
                        st.write(f"**Timestamp:** {doc['timestamp']}")
                    
                    # Métadonnées brutes
                    if doc['metadonnees'] and doc['metadonnees'] != '{}' and doc['metadonnees'] != 'None':
                        with st.expander("Métadonnées techniques"):
                            try:
                                meta = json.loads(doc['metadonnees'])
                                st.json(meta)
                            except:
                                st.text(doc['metadonnees'])
    
    # ==================== EXPORT COMPLET ====================
    st.header("💾 Export COMPLET des données")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Export CSV complet
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 CSV COMPLET",
            data=csv,
            file_name=f"google_cse_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON structuré
        json_data = json.dumps(donnees, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON STRUCTURÉ",
            data=json_data,
            file_name=f"google_cse_analyse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
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
            file_name=f"urls_complets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col4:
        # Export données filtrées
        if len(df_filtre) < len(df):
            csv_filtre = df_filtre.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 CSV FILTRÉ",
                data=csv_filtre,
                file_name=f"google_cse_filtre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # ==================== DONNÉES BRUTES ====================
    with st.expander("📊 DONNÉES BRUTES COMPLÈTES", expanded=False):
        if st.session_state.donnees_json_brutes:
            st.json(st.session_state.donnees_json_brutes)

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("🔍 Analyseur COMPLET de données JSON Google CSE")
    
    st.warning("⚠️ **IMPORTANT : Ce dashboard analyse VOS DONNÉES RÉELLES**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 À propos
        Ce dashboard analyse **TOUTES les données** de votre 
        **fichier JSON Google CSE complet**.
        
        ### ✅ FONCTIONNALITÉS COMPLÈTES
        - **Extraction COMPLÈTE** de tous les résultats
        - **Analyse structurelle** automatique
        - **Filtres avancés** par type, législature, période
        - **Visualisations** professionnelles
        - **Export** multi-formats
        
        ### 📋 CE QUI SERA ANALYSÉ
        - **Tous les résultats** de votre JSON
        - **Métadonnées complètes**
        - **Informations de pagination**
        - **Données techniques** brutes
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 COMMENT PROCÉDER
        1. **Assurez-vous** que votre fichier `json.txt` contient TOUS les résultats
        2. **Cliquez** sur "ANALYSER LE FICHIER JSON COMPLET"
        3. **Attendez** l'extraction complète
        4. **Explorez** TOUS les résultats
        5. **Exportez** les données complètes
        
        ### 🔍 PRÉREQUIS
        - Votre fichier doit s'appeler **`json.txt`**
        - Il doit être dans le **même dossier** que ce script
        - Il doit contenir la **réponse JSON COMPLÈTE** de l'API
        
        ### ⚠️ ATTENTION
        Si votre fichier ne contient que 10 résultats, 
        le dashboard n'analysera que ces 10 résultats.
        """)
    
    # Instructions détaillées
    with st.expander("📁 COMMENT OBTENIR LES DONNÉES COMPLÈTES", expanded=True):
        st.markdown("""
        ### Pour obtenir TOUS les 131 résultats estimés :
        
        **Option 1 : API Google CSE officielle**
        ```
        https://www.googleapis.com/customsearch/v1?
        key=VOTRE_CLE_API&
        cx=014917347718038151697:kltwr00yvbk&
        q=bumidom&
        start=1&
        num=10
        ```
        
        **Option 2 : Requêtes paginées manuelles**
        ```
        Page 1: &start=1
        Page 2: &start=11
        Page 3: &start=21
        ...
        Page 14: &start=131
        ```
        
        **Option 3 : Votre fichier actuel**
        - Si votre `json.txt` contient déjà 131 résultats
        - Le dashboard les analysera TOUS
        - Sinon, vous n'aurez que les résultats présents
        """)
    
    # Zone de dépôt de fichier (simulée)
    st.divider()
    st.subheader("📤 Téléversement de fichier (simulé)")
    
    uploaded_file = st.file_uploader(
        "Déposez votre fichier JSON complet ici",
        type=['txt', 'json'],
        help="Fichier contenant la réponse JSON complète de l'API Google CSE"
    )
    
    if uploaded_file is not None:
        st.info(f"Fichier détecté: {uploaded_file.name} ({uploaded_file.size} octets)")
        st.warning("⚠️ Pour utiliser ce fichier, renommez-le en 'json.txt' et placez-le dans le dossier du script")

# ==================== PIED DE PAGE ====================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard d'analyse COMPLÈTE Google CSE • Extraction de données réelles • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
