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
                    'clés': list(value.keys())[:5],
                    'sous_structure': {}
                }
    
    return analyse

def extraire_tous_les_resultats(json_data):
    """Extrait TOUS les résultats possibles du JSON"""
    resultats = []
    
    # Mode débogage
    with st.expander("🔧 DEBUG: Structure JSON", expanded=False):
        st.json(json_data)
    
    # Stratégie 1: Chercher directement 'results'
    if 'results' in json_data and isinstance(json_data['results'], list):
        resultats = json_data['results']
        st.success(f"✅ Stratégie 1: 'results' avec {len(resultats)} éléments")
        return resultats
    
    # Stratégie 2: Chercher dans les clés principales
    for key, value in json_data.items():
        if isinstance(value, list):
            resultats = value
            st.success(f"✅ Stratégie 2: clé '{key}' avec {len(resultats)} éléments")
            return resultats
        elif isinstance(value, dict) and 'results' in value:
            if isinstance(value['results'], list):
                resultats = value['results']
                st.success(f"✅ Stratégie 3: clé '{key}.results' avec {len(resultats)} éléments")
                return resultats
    
    # Stratégie 4: Chercher n'importe quelle liste
    for key, value in json_data.items():
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict):
                resultats = value
                st.success(f"✅ Stratégie 4: clé '{key}' (n'importe quelle liste) avec {len(resultats)} éléments")
                return resultats
    
    st.error("❌ Aucune stratégie n'a trouvé de résultats!")
    return []

# ==================== PARSER SPÉCIFIQUE ====================

def parser_resultats_complets(items):
    """Parse tous les résultats trouvés"""
    resultats = []
    
    st.info(f"📊 Parsing de {len(items)} éléments...")
    
    for i, item in enumerate(items):
        try:
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
                description = description.replace('\\u003cb\\u003e', '').replace('\\u003c/b\\u003e', '')
            
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
            
            # Métadonnées supplémentaires
            metadonnees = {}
            if 'richSnippet' in item:
                metadonnees['richSnippet'] = item['richSnippet']
            if 'breadcrumbUrl' in item:
                metadonnees['breadcrumbs'] = item['breadcrumbUrl'].get('crumbs', [])
            
            # Créer l'entrée avec PLUS d'informations pour la sélection
            resultats.append({
                'id': f"DOC_{i+1:04d}",
                'doc_num': i + 1,
                'position': i + 1,
                'titre_complet': titre,
                'titre_affichage': titre[:80] + "..." if len(titre) > 80 else titre,
                'url': url,
                'description_complete': description,
                'description_courte': description[:150] + "..." if description and len(description) > 150 else (description or ""),
                'type': type_doc,
                'legislature': legislature,
                'periode': periode,
                'date': date_doc,
                'score': score,
                'format': format_doc,
                'source': visible_url,
                'metadonnees': json.dumps(metadonnees) if metadonnees else '',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'selected': False  # Pour la sélection
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
        
        # Nettoyer si nécessaire
        if 'google.search.cse.api' in contenu:
            contenu = re.sub(r'google\.search\.cse\.api\d+\(', '', contenu)
            contenu = re.sub(r'\);\s*$', '', contenu)
            contenu = contenu.strip()
        
        data = json.loads(contenu)
        
        # Analyser la structure
        analyse = analyser_structure_json(data)
        
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
        return None, []

# ==================== FONCTION D'AFFICHAGE DE DOCUMENT ====================

def afficher_document_detail(doc):
    """Affiche le détail d'un document sélectionné"""
    st.markdown("---")
    st.markdown(f"### 📄 **{doc['titre_complet']}**")
    
    # Métadonnées en colonnes
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Type", doc['type'])
    with col2:
        st.metric("Législature", doc['legislature'] or "N/A")
    with col3:
        st.metric("Période", doc['periode'])
    with col4:
        st.metric("Score", f"{doc['score']:.1f}")
    
    # Informations supplémentaires
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(f"**Date:** {doc['date']}")
        st.info(f"**Format:** {doc['format']}")
        st.info(f"**Source:** {doc['source']}")
    
    with col_info2:
        st.info(f"**ID:** {doc['id']}")
        st.info(f"**Position:** {doc['position']}")
        st.info(f"**Analyse:** {doc['timestamp']}")
    
    # Description complète
    if doc['description_complete']:
        with st.expander("📝 **Description complète**", expanded=True):
            st.write(doc['description_complete'])
    
    # URL avec bouton d'ouverture
    if doc['url']:
        st.markdown("**🔗 URL originale:**")
        st.code(doc['url'])
        
        # Bouton pour ouvrir le PDF
        st.markdown(
            f"""
            <a href="{doc['url']}" target="_blank">
            <button style="
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px 0;
                display: inline-block;
            ">
            📄 Ouvrir le document PDF
            </button>
            </a>
            """,
            unsafe_allow_html=True
        )
    
    # Métadonnées techniques
    if doc['metadonnees'] and doc['metadonnees'] != '{}':
        with st.expander("⚙️ **Métadonnées techniques**", expanded=False):
            try:
                meta = json.loads(doc['metadonnees'])
                st.json(meta)
            except:
                st.text(doc['metadonnees'])
    
    st.markdown("---")

# ==================== INTERFACE ====================

# Initialisation
if 'donnees' not in st.session_state:
    st.session_state.donnees = []
if 'json_source' not in st.session_state:
    st.session_state.json_source = None
if 'selected_doc_id' not in st.session_state:
    st.session_state.selected_doc_id = None

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
    
    # Affichage des statistiques si données existent
    if st.session_state.donnees:
        st.divider()
        st.subheader("📈 Statistiques")
        
        total = len(st.session_state.donnees)
        st.metric("Documents", total)
        
        types_uniques = len(set([r['type'] for r in st.session_state.donnees]))
        st.metric("Types", types_uniques)

# ==================== AFFICHAGE PRINCIPAL ====================

if st.session_state.donnees:
    donnees = st.session_state.donnees
    df = pd.DataFrame(donnees)
    
    # Interface à deux onglets
    tab1, tab2 = st.tabs(["📋 Liste des documents", "🔍 Consultation détaillée"])
    
    with tab1:
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
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                types = st.multiselect("Type", 
                                      df['type'].unique(), 
                                      default=df['type'].unique())
            
            with col_f2:
                legislatures = st.multiselect("Législature", 
                                             [l for l in sorted(df['legislature'].unique()) if l],
                                             default=[])
            
            with col_f3:
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
        
        # Tableau avec bouton de sélection
        st.subheader("📄 Liste des documents")
        
        # Options de tri
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            sort_by = st.selectbox("Trier par", 
                                  ['position', 'score', 'type', 'legislature', 'periode'],
                                  index=0)
        with col_sort2:
            sort_order = st.selectbox("Ordre", ['descendant', 'ascendant'], index=0)
        
        # Trier
        df_sorted = df_filtre.sort_values(
            sort_by, 
            ascending=(sort_order == 'ascendant')
        )
        
        # Affichage du tableau avec colonne de sélection
        for idx, row in df_sorted.iterrows():
            col_sel, col_info = st.columns([1, 10])
            
            with col_sel:
                # Bouton radio pour sélectionner
                if st.button("👁️", key=f"select_{row['id']}"):
                    st.session_state.selected_doc_id = row['id']
                    st.rerun()
            
            with col_info:
                # Informations du document
                with st.expander(f"**{row['titre_affichage']}** - {row['type']}", expanded=False):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**ID:** {row['id']}")
                        st.write(f"**Législature:** {row['legislature'] or 'N/A'}")
                        st.write(f"**Période:** {row['periode']}")
                    
                    with col_info2:
                        st.write(f"**Date:** {row['date']}")
                        st.write(f"**Score:** {row['score']:.1f}")
                        st.write(f"**Source:** {row['source']}")
                    
                    if row['description_courte']:
                        st.write(f"**Description:** {row['description_courte']}")
                    
                    # Bouton pour consulter ce document
                    if st.button("📖 Consulter ce document", key=f"view_{row['id']}"):
                        st.session_state.selected_doc_id = row['id']
                        st.rerun()
        
        # Visualisations
        st.subheader("📈 Visualisations")
        
        viz_tab1, viz_tab2, viz_tab3 = st.tabs(["Types", "Périodes", "Scores"])
        
        with viz_tab1:
            type_counts = df_filtre['type'].value_counts()
            fig = px.pie(values=type_counts.values, names=type_counts.index, 
                        title="Répartition par type")
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tab2:
            if len(df_filtre['periode'].unique()) > 1:
                periode_counts = df_filtre['periode'].value_counts().head(15)
                fig = px.bar(x=periode_counts.index, y=periode_counts.values,
                            title="Top 15 des périodes")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        with viz_tab3:
            fig = px.histogram(df_filtre, x='score', nbins=20,
                              title="Distribution des scores")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("🔍 Consultation détaillée")
        
        if st.session_state.selected_doc_id:
            # Trouver le document sélectionné
            selected_doc = next((d for d in donnees if d['id'] == st.session_state.selected_doc_id), None)
            
            if selected_doc:
                afficher_document_detail(selected_doc)
                
                # Navigation entre documents
                st.subheader("📄 Navigation")
                
                current_idx = next((i for i, d in enumerate(donnees) if d['id'] == st.session_state.selected_doc_id), 0)
                
                col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
                
                with col_nav1:
                    if current_idx > 0:
                        if st.button("◀️ Document précédent"):
                            st.session_state.selected_doc_id = donnees[current_idx - 1]['id']
                            st.rerun()
                
                with col_nav2:
                    if st.button("📋 Retour à la liste"):
                        st.session_state.selected_doc_id = None
                        st.rerun()
                
                with col_nav3:
                    if st.button("🔄 Recharger ce document"):
                        st.rerun()
                
                with col_nav4:
                    if current_idx < len(donnees) - 1:
                        if st.button("Document suivant ▶️"):
                            st.session_state.selected_doc_id = donnees[current_idx + 1]['id']
                            st.rerun()
            else:
                st.warning("Document sélectionné non trouvé.")
                if st.button("📋 Retour à la liste"):
                    st.session_state.selected_doc_id = None
                    st.rerun()
        else:
            st.info("👈 Sélectionnez un document dans la liste pour le consulter ici.")
            
            # Afficher quelques documents récents
            st.subheader("📌 Documents récemment consultés")
            recent_docs = donnees[:5]  # 5 premiers
            
            for doc in recent_docs:
                with st.expander(f"{doc['titre_affichage']}", expanded=False):
                    st.write(f"**Type:** {doc['type']}")
                    st.write(f"**Législature:** {doc['legislature'] or 'N/A'}")
                    st.write(f"**Période:** {doc['periode']}")
                    if doc['description_courte']:
                        st.write(f"**Description:** {doc['description_courte'][:100]}...")
                    
                    if st.button("Consulter", key=f"quick_{doc['id']}"):
                        st.session_state.selected_doc_id = doc['id']
                        st.rerun()
    
    # Export (dans les deux onglets)
    st.sidebar.divider()
    st.sidebar.subheader("💾 Export")
    
    col_exp1, col_exp2 = st.sidebar.columns(2)
    
    with col_exp1:
        if st.button("📥 CSV", use_container_width=True):
            csv = df.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name=f"bumidom_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col_exp2:
        if st.button("🔗 URLs", use_container_width=True):
            urls = "\n".join(df['url'].tolist())
            st.sidebar.download_button(
                label="Télécharger URLs",
                data=urls.encode('utf-8'),
                file_name=f"urls_bumidom_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )

else:
    # Écran d'accueil
    st.header("📁 Analyseur BUMIDOM")
    
    col_welcome1, col_welcome2 = st.columns(2)
    
    with col_welcome1:
        st.markdown("""
        ### 🔍 Ce dashboard analyse VOTRE fichier JSON complet
        
        **Nouvelles fonctionnalités:**
        - ✅ **Sélection individuelle** des documents
        - ✅ **Consultation détaillée** un par un
        - ✅ **Navigation** entre documents
        - ✅ **Interface à onglets** (liste + détail)
        - ✅ **Recherche et filtres** avancés
        
        ### 🚀 Comment procéder:
        1. Cliquez sur **"CHARGER ET ANALYSER"** dans la sidebar
        2. Explorez la **liste des documents** dans l'onglet 📋
        3. **Sélectionnez** un document avec le bouton 👁️
        4. **Consultez le détail** dans l'onglet 🔍
        5. **Naviguez** entre les documents avec les flèches
        """)
    
    with col_welcome2:
        st.markdown("""
        ### 📋 Exemple d'utilisation:
        
        **1. Chargement des données:**
        ```
        📁 Fichier chargé: X caractères
        ✅ Stratégie trouvée: X éléments
        ✅ Y documents analysés
        ```
        
        **2. Navigation:**
        ```
        📋 Liste: Voir tous les documents
        🔍 Détail: Voir un document spécifique
        ◀️▶️ Navigation: Entre les documents
        ```
        
        **3. Fonctions clés:**
        - **Filtrage** par type/législature/période
        - **Tri** par score/date/type
        - **Visualisations** graphiques
        - **Export** CSV/URLs
        - **Ouverture directe** des PDF
        """)
    
    # Instructions
    with st.expander("🔧 Configuration requise", expanded=False):
        st.markdown("""
        ### Fichier requis:
        - Nom: `json.txt`
        - Format: JSON (Google CSE ou standard)
        - Contenu: Données d'archive BUMIDOM
        - Emplacement: Même dossier que ce script
        
        ### Structure attendue:
        ```json
        {
          "results": [
            {
              "title": "...",
              "url": "...",
              "contentNoFormatting": "...",
              "fileFormat": "PDF/Adobe Acrobat"
            },
            // ... autres documents ...
          ]
        }
        ```
        
        ### Support:
        - Format Google CSE wrapper: ✅
        - Format JSON standard: ✅
        - Archives Assemblée Nationale: ✅
        - Documents PDF: ✅
        """)

# Pied de page
st.divider()
st.caption(f"Dashboard BUMIDOM • Consultation individuelle • {datetime.now().strftime('%d/%m/%Y %H:%M')} • Sélection: {st.session_state.selected_doc_id or 'Aucune'}")
