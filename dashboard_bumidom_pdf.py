import streamlit as st
import pandas as pd
import json
import plotly.express as px
from datetime import datetime
import re
import os

# ==================== CONFIGURATION ====================
st.set_page_config(page_title="Dashboard BUMIDOM", layout="wide")
st.title("🔍 Dashboard COMPLET - Archives BUMIDOM")
st.markdown("**Analyse de TOUS les résultats BUMIDOM**")

# ==================== FONCTIONS DE DÉBOGAGE ====================

def analyser_structure_json(json_data):
    """Analyse la structure complète du JSON"""
    analyse = {
        'clés_niveau_1': [],
        'types': {},
        'nombre_total_elements': 0,
        'structure_detaille': {}
    }
    
    if isinstance(json_data, dict):
        analyse['clés_niveau_1'] = list(json_data.keys())
        
        for key, value in json_data.items():
            analyse['types'][key] = type(value).__name__
            
            if isinstance(value, list):
                analyse['structure_detaille'][key] = {
                    'type': 'list',
                    'longueur': len(value),
                    'exemple_element': value[0] if len(value) > 0 else None
                }
                analyse['nombre_total_elements'] += len(value)
            elif isinstance(value, dict):
                analyse['structure_detaille'][key] = {
                    'type': 'dict',
                    'clés': list(value.keys())[:5],  # 5 premières clés
                    'sous_structure': {}
                }
    
    return analyse

def extraire_tous_les_resultats(json_data):
    """Extrait TOUS les résultats possibles du JSON"""
    resultats = []
    
    # Mode débogage
    with st.expander("🔧 DEBUG: Structure JSON", expanded=False):
        st.json(json_data)
    
    # Essayer plusieurs stratégies d'extraction
    strategies = []
    
    # Stratégie 1: Chercher directement 'results'
    if 'results' in json_data and isinstance(json_data['results'], list):
        strategies.append(("results direct", json_data['results']))
    
    # Stratégie 2: Chercher dans les clés principales
    for key, value in json_data.items():
        if isinstance(value, list):
            strategies.append((f"clé '{key}'", value))
        elif isinstance(value, dict) and 'results' in value:
            if isinstance(value['results'], list):
                strategies.append((f"clé '{key}.results'", value['results']))
    
    # Afficher les stratégies trouvées
    st.info(f"**Stratégies trouvées:** {len(strategies)}")
    for nom, data in strategies:
        st.write(f"- {nom}: {len(data)} éléments")
    
    # Utiliser la stratégie avec le plus d'éléments
    if strategies:
        meilleure_strategie = max(strategies, key=lambda x: len(x[1]))
        st.success(f"✅ Utilisation de: {meilleure_strategie[0]} avec {len(meilleure_strategie[1])} éléments")
        return meilleure_strategie[1]
    
    return []

# ==================== PARSER SPÉCIFIQUE ====================

def parser_resultats_complets(items):
    """Parse tous les résultats trouvés"""
    resultats = []
    
    st.info(f"📊 Parsing de {len(items)} éléments...")
    
    for i, item in enumerate(items):
        try:
            # DÉBOGAGE: Afficher les premiers éléments
            if i < 3:  # Afficher seulement les 3 premiers pour le débogage
                with st.expander(f"DEBUG: Élément {i+1}", expanded=False):
                    st.json(item)
            
            # Titre
            titre = item.get('title', 
                    item.get('titleNoFormatting', 
                    item.get('name', f'Document {i+1}')))
            
            # URL
            url = item.get('url',
                  item.get('unescapedUrl',
                  item.get('link',
                  item.get('formattedUrl', ''))))
            
            # Description
            description = item.get('contentNoFormatting',
                          item.get('content',
                          item.get('snippet',
                          item.get('description', ''))))
            
            # Nettoyage
            if description:
                description = description.replace('&#39;', "'").replace('&nbsp;', ' ')
            
            # Date
            date_doc = "Inconnue"
            if description:
                date_match = re.search(r'(\d{1,2}\s+[a-zéû]+\s+\d{4}|\d{4})', description, re.IGNORECASE)
                if date_match:
                    date_doc = date_match.group(1)
            
            # Type de document
            type_doc = "Document"
            if 'pdf' in url.lower() or 'PDF' in str(item.get('fileFormat', '')):
                type_doc = "PDF"
            if 'journal' in titre.lower() or 'OFFICIEL' in titre:
                type_doc = "Journal Officiel"
            if '/cri/' in url:
                type_doc = "Compte rendu"
            if '/qst/' in url:
                type_doc = "Question écrite"
            
            # Législature
            legislature = ""
            if url:
                leg_match = re.search(r'/(\d+)/cri/', url)
                if leg_match:
                    legislature = leg_match.group(1)
                else:
                    leg_match = re.search(r'/(\d+)/qst/', url)
                    if leg_match:
                        legislature = leg_match.group(1)
            
            # Période
            periode = "Inconnue"
            if url:
                periode_match = re.search(r'/(\d{4})-(\d{4})', url)
                if periode_match:
                    periode = f"{periode_match.group(1)}-{periode_match.group(2)}"
            
            # Score (basé sur la position)
            score = 100 - (i * 0.5)
            
            # Source
            visible_url = item.get('visibleUrl', '')
            if not visible_url and url:
                from urllib.parse import urlparse
                try:
                    visible_url = urlparse(url).netloc
                except:
                    visible_url = url[:30] + "..."
            
            # Format
            format_doc = item.get('fileFormat', '')
            
            # Créer l'entrée
            resultats.append({
                'id': f"DOC_{i+1:03d}",
                'position': i + 1,
                'titre': titre[:100] + "..." if len(titre) > 100 else titre,
                'url': url,
                'description': description[:200] + "..." if description and len(description) > 200 else (description or ""),
                'type': type_doc,
                'legislature': legislature,
                'periode': periode,
                'date': date_doc,
                'score': score,
                'format': format_doc,
                'source': visible_url,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        except Exception as e:
            st.warning(f"⚠️ Erreur sur élément {i+1}: {str(e)[:50]}")
            continue
    
    return resultats

# ==================== CHARGEMENT DU FICHIER ====================

@st.cache_data
def charger_json():
    """Charge et parse le fichier JSON"""
    try:
        with open('json.txt', 'r', encoding='utf-8') as f:
            contenu = f.read()
        
        st.success(f"📁 Fichier chargé: {len(contenu):,} caractères")
        
        # Essayer de parser
        try:
            data = json.loads(contenu)
        except:
            # Nettoyer
            contenu = re.sub(r'google\.search\.cse\.api\d+\(', '', contenu)
            contenu = re.sub(r'\);\s*$', '', contenu)
            contenu = contenu.strip()
            data = json.loads(contenu)
        
        # Analyser la structure
        analyse = analyser_structure_json(data)
        
        with st.expander("📊 Analyse structurelle", expanded=False):
            st.write("**Clés niveau 1:**")
            for cle in analyse['clés_niveau_1']:
                st.write(f"- {cle} ({analyse['types'].get(cle, 'inconnu')})")
            
            st.write("**Structure détaillée:**")
            for cle, details in analyse['structure_detaille'].items():
                if details['type'] == 'list':
                    st.write(f"- {cle}: liste de {details['longueur']} éléments")
                elif details['type'] == 'dict':
                    st.write(f"- {cle}: dict avec clés {', '.join(details['clés'][:5])}")
        
        # Extraire tous les résultats
        items = extraire_tous_les_resultats(data)
        
        if not items:
            st.error("❌ Aucun résultat trouvé dans le JSON!")
            return None, []
        
        # Parser
        resultats = parser_resultats_complets(items)
        
        return data, resultats
        
    except Exception as e:
        st.error(f"❌ Erreur de chargement: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None, []

# ==================== INTERFACE ====================

# Initialisation
if 'donnees' not in st.session_state:
    st.session_state.donnees = []
if 'json_source' not in st.session_state:
    st.session_state.json_source = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if st.button("🔄 CHARGER ET ANALYSER", type="primary", use_container_width=True):
        with st.spinner("Analyse en cours..."):
            json_source, resultats = charger_json()
            
            if resultats:
                st.session_state.json_source = json_source
                st.session_state.donnees = resultats
                st.success(f"✅ {len(resultats)} documents analysés!")
                
                # Statistiques
                types = {}
                for r in resultats:
                    types[r['type']] = types.get(r['type'], 0) + 1
                
                st.write("**📊 Répartition:**")
                for type_name, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {type_name}: {count}")
            else:
                st.error("❌ Aucune donnée analysée")

# ==================== AFFICHAGE PRINCIPAL ====================

if st.session_state.donnees:
    donnees = st.session_state.donnees
    df = pd.DataFrame(donnees)
    
    st.header(f"📊 Résultats: {len(df)} documents")
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(df))
    with col2:
        st.metric("Types", len(df['type'].unique()))
    with col3:
        st.metric("Législatures", len([x for x in df['legislature'].unique() if x]))
    with col4:
        st.metric("Périodes", len([x for x in df['periode'].unique() if x != "Inconnue"]))
    
    # Filtres
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            types = st.multiselect("Type", df['type'].unique(), default=df['type'].unique())
        
        with col2:
            legislatures = st.multiselect("Législature", 
                                         [l for l in sorted(df['legislature'].unique()) if l],
                                         default=[])
        
        with col3:
            periodes = st.multiselect("Période",
                                     [p for p in sorted(df['periode'].unique()) if p != "Inconnue"],
                                     default=[])
    
    # Appliquer filtres
    mask = df['type'].isin(types)
    if legislatures:
        mask = mask & df['legislature'].isin(legislatures)
    if periodes:
        mask = mask & df['periode'].isin(periodes)
    
    df_filtre = df[mask]
    
    st.info(f"📋 {len(df_filtre)} documents après filtrage ({len(df_filtre)/len(df)*100:.0f}%)")
    
    # Tableau
    st.dataframe(
        df_filtre[[
            'id', 'titre', 'type', 'legislature', 
            'periode', 'date', 'score', 'source'
        ]],
        use_container_width=True,
        column_config={
            'id': 'ID',
            'titre': 'Titre',
            'type': 'Type',
            'legislature': 'Législature',
            'periode': 'Période',
            'date': 'Date',
            'score': 'Score',
            'source': 'Source'
        }
    )
    
    # Visualisations
    st.subheader("📈 Visualisations")
    
    tab1, tab2, tab3 = st.tabs(["Types", "Périodes", "Scores"])
    
    with tab1:
        type_counts = df_filtre['type'].value_counts()
        fig = px.pie(values=type_counts.values, names=type_counts.index, 
                    title="Répartition par type")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if len(df_filtre['periode'].unique()) > 1:
            periode_counts = df_filtre['periode'].value_counts().head(15)
            fig = px.bar(x=periode_counts.index, y=periode_counts.values,
                        title="Top 15 des périodes")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = px.histogram(df_filtre, x='score', nbins=20,
                          title="Distribution des scores")
        st.plotly_chart(fig, use_container_width=True)
    
    # Export
    st.subheader("💾 Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV complet", csv, 
                          "bumidom_complet.csv", "text/csv",
                          use_container_width=True)
    
    with col2:
        json_data = json.dumps(donnees, ensure_ascii=False, indent=2)
        st.download_button("📥 JSON structuré", json_data.encode('utf-8'),
                          "bumidom_structuré.json", "application/json",
                          use_container_width=True)
    
    with col3:
        urls = "\n".join(df['url'].tolist())
        st.download_button("🔗 URLs seulement", urls.encode('utf-8'),
                          "urls_bumidom.txt", "text/plain",
                          use_container_width=True)

else:
    # Écran d'accueil
    st.header("📁 Analyseur BUMIDOM")
    
    st.markdown("""
    ### 🔍 Ce dashboard analyse VOTRE fichier JSON complet
    
    **Fonctionnalités:**
    - ✅ Analyse COMPLÈTE de tous les résultats
    - ✅ Détection automatique de la structure
    - ✅ Parsing intelligent des données
    - ✅ Filtres et visualisations
    - ✅ Export multi-formats
    
    ### 🚀 Comment procéder:
    1. Assurez-vous que `json.txt` est dans le dossier
    2. Cliquez sur **"CHARGER ET ANALYSER"** dans la sidebar
    3. Explorez les résultats complets
    
    ### 📋 Prérequis:
    - Votre fichier doit s'appeler `json.txt`
    - Il doit contenir la réponse JSON complète de l'API
    - Format: JSON standard ou Google CSE wrapper
    """)
    
    # Aide pour la structure
    with st.expander("🔧 Aide technique", expanded=False):
        st.markdown("""
        ### Structures supportées:
        
        **1. Google CSE standard:**
        ```json
        {
          "items": [...],
          "queries": {...}
        }
        ```
        
        **2. Google CSE wrapper:**
        ```javascript
        google.search.cse.api123({
          "results": [...],
          "cursor": {...}
        });
        ```
        
        **3. Votre structure actuelle:**
        - 100+ éléments détectés
        - Chaque élément avec titre, URL, description
        - Format PDF des archives Assemblée Nationale
        
        ### En cas de problème:
        - Vérifiez que le fichier est bien nommé `json.txt`
        - Vérifiez qu'il contient du JSON valide
        - Utilisez le mode DEBUG pour voir la structure
        """)

# Pied de page
st.divider()
st.caption("Dashboard BUMIDOM • Analyse complète • " + datetime.now().strftime("%d/%m/%Y %H:%M"))
