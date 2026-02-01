import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re
import os

# ==================== CONFIGURATION ====================
st.set_page_config(page_title="Dashboard API Google CSE", layout="wide")
st.title("🔍 Dashboard API - Archives Assemblée Nationale")
st.markdown("**Analyse COMPLÈTE de 131 résultats BUMIDOM**")

# ==================== FONCTIONS DE PARSING SPÉCIFIQUES ====================

def parser_json_bumidom_complet(json_data):
    """Parser SPÉCIFIQUE pour le fichier JSON BUMIDOM avec 131 résultats"""
    resultats = []
    
    try:
        # Votre fichier a une structure spécifique
        if 'results' in json_data:
            items = json_data['results']
        elif isinstance(json_data, dict) and 'results' in list(json_data.values())[0]:
            # Structure wrapper
            items = list(json_data.values())[0]['results']
        else:
            # Chercher dans toute la structure
            for key, value in json_data.items():
                if isinstance(value, list) and len(value) > 0:
                    items = value
                    break
        
        st.info(f"✅ {len(items)} résultats trouvés dans la structure principale")
        
        # Parser CHAQUE résultat individuellement
        for i, item in enumerate(items):
            try:
                # Extraire les informations selon votre structure spécifique
                titre = item.get('title', item.get('titleNoFormatting', f'Document {i+1}'))
                url = item.get('url', item.get('unescapedUrl', item.get('link', '')))
                
                # Extraire le contenu (description)
                description = ""
                if 'contentNoFormatting' in item:
                    description = item['contentNoFormatting']
                elif 'content' in item:
                    description = item['content']
                elif 'snippet' in item:
                    description = item['snippet']
                
                # Nettoyer les entités HTML
                if description:
                    description = description.replace('\\u003cb\\u003e', '').replace('\\u003c/b\\u003e', '')
                    description = description.replace('&#39;', "'").replace('&nbsp;', ' ')
                    description = description.replace('&quot;', '"')
                
                # Extraire la date depuis le contenu
                date_doc = "Date inconnue"
                if description:
                    # Chercher des patterns de date
                    date_patterns = [
                        r'(\d{1,2}\s+[a-zéû]+\s+\d{4})',  # 26 oct. 1971
                        r'(\d{4})',                      # 1971
                        r'(\d{1,2}/\d{1,2}/\d{4})',      # 26/10/1971
                        r'(\d{1,2}\s+[a-zA-Z]+\s+\d{4})' # 26 October 1971
                    ]
                    
                    for pattern in date_patterns:
                        date_match = re.search(pattern, description, re.IGNORECASE)
                        if date_match:
                            date_doc = date_match.group(1)
                            break
                
                # Détecter le type de document
                type_doc = "Document"
                file_format = item.get('fileFormat', '')
                
                if '.pdf' in url.lower() or 'PDF' in file_format or 'pdf' in str(item).lower():
                    type_doc = "PDF"
                elif 'archives.assemblee-nationale.fr' in url:
                    if '/cri/' in url:
                        type_doc = "Compte rendu"
                    elif 'journal' in titre.lower() or 'JOURNAL' in titre or 'OFFICIEL' in titre:
                        type_doc = "Journal Officiel"
                    elif 'constitution' in titre.lower():
                        type_doc = "Constitution"
                    elif '/qst/' in url:
                        type_doc = "Question écrite"
                
                # Extraire la législature
                legislature = ""
                
                # Chercher dans l'URL
                if url:
                    leg_match_url = re.search(r'/(\d+)/cri/', url)
                    if leg_match_url:
                        legislature = leg_match_url.group(1)
                    else:
                        leg_match_url = re.search(r'/(\d+)/qst/', url)
                        if leg_match_url:
                            legislature = leg_match_url.group(1)
                
                # Chercher dans le titre
                if not legislature and titre:
                    leg_match_title = re.search(r'(\d+)[\'°]?\s+Législature', titre)
                    if leg_match_title:
                        legislature = leg_match_title.group(1)
                
                # Extraire les années
                periode = "Inconnue"
                if url:
                    # Pattern: /1971-1972-ordonnaire1/
                    annee_match = re.search(r'/(\d{4})-(\d{4})', url)
                    if annee_match:
                        periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                
                if periode == "Inconnue" and description:
                    # Pattern: 1971-1972
                    annee_match = re.search(r'(\d{4})\s*-\s*(\d{4})', description)
                    if annee_match:
                        periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                    else:
                        # Pattern: 1971
                        annee_match = re.search(r'(\d{4})', date_doc)
                        if annee_match:
                            annee = annee_match.group(1)
                            periode = f"{annee}"
                
                # Score de pertinence (basé sur la position dans le JSON)
                score = 100 - (i * 0.5)  # Plus doux pour 131 résultats
                
                # Métadonnées
                metadonnees = {}
                if 'richSnippet' in item:
                    metadonnees = item['richSnippet']
                if 'breadcrumbUrl' in item:
                    metadonnees['breadcrumbs'] = item['breadcrumbUrl'].get('crumbs', [])
                
                # Identifier le domaine
                visible_url = item.get('visibleUrl', '')
                if not visible_url and url:
                    from urllib.parse import urlparse
                    try:
                        parsed = urlparse(url)
                        visible_url = parsed.netloc
                    except:
                        visible_url = url[:50] + "..."
                
                # Ajouter au résultat
                resultats.append({
                    'id': f"R{i+1:03d}",
                    'titre': titre[:150] + "..." if len(titre) > 150 else titre,
                    'url': url,
                    'description': description[:250] + "..." if description and len(description) > 250 else (description or "Pas de description"),
                    'type': type_doc,
                    'legislature': legislature,
                    'periode': periode,
                    'date_doc': date_doc,
                    'position': i + 1,
                    'score': score,
                    'format': file_format,
                    'visible_url': visible_url,
                    'metadonnees': json.dumps(metadonnees, ensure_ascii=False) if metadonnees else '',
                    'timestamp': datetime.now().isoformat(),
                    'doc_id': f"DOC_{i+1:04d}"
                })
                
            except Exception as e:
                st.warning(f"⚠️ Erreur sur l'élément {i+1}: {str(e)[:100]}")
                continue
        
        st.success(f"🎉 {len(resultats)} résultats parsés avec succès!")
        return resultats
        
    except Exception as e:
        st.error(f"❌ Erreur majeure lors du parsing: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return []

def charger_fichier_json_complet():
    """Charge le fichier JSON complet"""
    try:
        # Lire le fichier
        with open('json.txt', 'r', encoding='utf-8') as f:
            contenu = f.read()
        
        st.info(f"📁 Fichier chargé: {len(contenu):,} caractères")
        
        # Essayer de parser directement
        try:
            data = json.loads(contenu)
            st.success("✅ JSON parsé directement")
            return data
        except json.JSONDecodeError:
            st.warning("⚠️ JSON direct échoué, tentative de nettoyage...")
            
            # Nettoyer le JSON
            contenu_nettoye = nettoyer_json_bumidom(contenu)
            
            try:
                data = json.loads(contenu_nettoye)
                st.success("✅ JSON nettoyé et parsé")
                return data
            except Exception as e:
                st.error(f"❌ Échec du parsing même après nettoyage: {e}")
                return None
                
    except FileNotFoundError:
        st.error("❌ Fichier 'json.txt' non trouvé!")
        st.info("Placez votre fichier JSON complet dans le même dossier que ce script")
        return None
    except Exception as e:
        st.error(f"❌ Erreur de chargement: {str(e)}")
        return None

def nettoyer_json_bumidom(contenu):
    """Nettoie spécifiquement le JSON BUMIDOM"""
    # Supprimer la fonction wrapper
    contenu = re.sub(r'google\.search\.cse\.api\d+\(\s*', '', contenu)
    contenu = re.sub(r'\);\s*$', '', contenu)
    
    # Remplacer les simples quotes par des doubles quotes pour les clés JSON
    lines = contenu.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remplacer les clés avec simples quotes
        line = re.sub(r'(\s*)(\w+)(\s*):(\s*)\'', r'\1"\2"\3:\4"', line)
        line = re.sub(r'\'(,?)\s*$', r'"\1', line)
        line = line.replace("' : '", '" : "')
        line = line.replace("': '", '": "')
        line = line.replace("',", '",')
        
        # Gérer les apostrophes dans le contenu
        line = line.replace("\\'", "'")
        line = line.replace("&#39;", "'")
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

# ==================== INTERFACE PRINCIPALE ====================

# Initialisation
if 'donnees_completes' not in st.session_state:
    st.session_state.donnees_completes = []
if 'json_brut' not in st.session_state:
    st.session_state.json_brut = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration BUMIDOM")
    
    # Bouton d'analyse principal
    if st.button("🚀 ANALYSER LES 131 RÉSULTATS BUMIDOM", 
                 type="primary", 
                 use_container_width=True,
                 help="Cliquez pour analyser TOUS les résultats du fichier JSON"):
        
        with st.spinner("Chargement et analyse complète en cours..."):
            # Charger le JSON
            json_data = charger_fichier_json_complet()
            
            if json_data:
                st.session_state.json_brut = json_data
                
                # Parser TOUS les résultats
                resultats = parser_json_bumidom_complet(json_data)
                st.session_state.donnees_completes = resultats
                
                # Afficher les statistiques
                if resultats:
                    st.success(f"✅ {len(resultats)} résultats analysés!")
                    
                    # Statistiques par type
                    types = {}
                    for r in resultats:
                        types[r['type']] = types.get(r['type'], 0) + 1
                    
                    st.write("**📊 Répartition:**")
                    for type_name, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
                        st.write(f"- {type_name}: {count}")
            else:
                st.error("❌ Impossible de charger le fichier JSON")
    
    # Statistiques
    if st.session_state.donnees_completes:
        st.divider()
        st.subheader("📈 Statistiques")
        
        total = len(st.session_state.donnees_completes)
        st.metric("Résultats totaux", total)
        
        # Types uniques
        types_uniques = len(set([r['type'] for r in st.session_state.donnees_completes]))
        st.metric("Types de documents", types_uniques)
        
        # Législatures uniques
        legislatures_uniques = len(set([r['legislature'] for r in st.session_state.donnees_completes if r['legislature']]))
        st.metric("Législatures", legislatures_uniques)

# ==================== CONTENU PRINCIPAL ====================

if st.session_state.donnees_completes:
    donnees = st.session_state.donnees_completes
    df = pd.DataFrame(donnees)
    
    # Header avec statistiques
    st.header(f"📊 Analyse complète: {len(df)} documents BUMIDOM")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pdf_count = df[df['format'].str.contains('PDF', na=False)].shape[0]
        st.metric("Documents PDF", pdf_count)
    
    with col2:
        cr_count = df[df['type'] == 'Compte rendu'].shape[0]
        st.metric("Comptes rendus", cr_count)
    
    with col3:
        jo_count = df[df['type'] == 'Journal Officiel'].shape[0]
        st.metric("Journaux Officiels", jo_count)
    
    with col4:
        qst_count = df[df['type'] == 'Question écrite'].shape[0]
        st.metric("Questions écrites", qst_count)
    
    # ==================== TABLEAU COMPLET ====================
    st.subheader("📋 Liste complète des documents")
    
    # Filtres rapides
    with st.expander("🔍 Filtres rapides", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtre par type
            types_disponibles = sorted(df['type'].unique())
            types_selection = st.multiselect(
                "Types de documents",
                types_disponibles,
                default=types_disponibles
            )
        
        with col2:
            # Filtre par législature
            legislatures_disponibles = sorted([l for l in df['legislature'].unique() if l])
            leg_selection = st.multiselect(
                "Législatures",
                legislatures_disponibles,
                default=legislatures_disponibles
            )
        
        with col3:
            # Filtre par période
            periodes_disponibles = sorted([p for p in df['periode'].unique() if p != "Inconnue"])
            periode_selection = st.multiselect(
                "Périodes",
                periodes_disponibles,
                default=periodes_disponibles[:10] if len(periodes_disponibles) > 10 else periodes_disponibles
            )
    
    # Appliquer les filtres
    df_filtre = df[
        (df['type'].isin(types_selection)) &
        (df['legislature'].isin(leg_selection) if leg_selection else True) &
        (df['periode'].isin(periode_selection) if periode_selection else True)
    ]
    
    st.info(f"📋 Affichage de {len(df_filtre)} sur {len(df)} documents ({len(df_filtre)/len(df)*100:.1f}%)")
    
    # Options d'affichage
    col1, col2 = st.columns(2)
    with col1:
        items_per_page = st.selectbox("Résultats par page", [10, 25, 50, 100, 200], index=2)
    with col2:
        tri_par = st.selectbox("Trier par", ['position', 'score', 'periode', 'legislature', 'type'], index=0)
        ordre_tri = st.selectbox("Ordre", ['ascendant', 'descendant'], index=1)
    
    # Tri
    df_filtre_trie = df_filtre.sort_values(
        tri_par,
        ascending=(ordre_tri == 'ascendant')
    )
    
    # Pagination
    total_pages = max(1, (len(df_filtre_trie) + items_per_page - 1) // items_per_page)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(df_filtre_trie))
    
    df_page = df_filtre_trie.iloc[start_idx:end_idx]
    
    st.write(f"**Page {page}/{total_pages}** ({start_idx+1}-{end_idx} sur {len(df_filtre_trie)})")
    
    # Affichage du tableau
    st.dataframe(
        df_page[[
            'id', 'titre', 'type', 'legislature', 
            'periode', 'date_doc', 'score', 'visible_url'
        ]],
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
            "visible_url": st.column_config.TextColumn("Source", width="medium")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.subheader("📈 Visualisations")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Par type", "Par période", "Par législature", "Scores"])
    
    with tab1:
        # Distribution par type
        type_counts = df_filtre['type'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title=f"Répartition par type ({len(type_counts)} types)",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Distribution par période
        periode_counts = df_filtre['periode'].value_counts().head(20)
        fig = px.bar(
            x=periode_counts.index,
            y=periode_counts.values,
            title=f"Top 20 des périodes",
            labels={'x': 'Période', 'y': 'Documents'},
            color=periode_counts.values,
            color_continuous_scale='Viridis'
        )
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Distribution par législature
        leg_counts = df_filtre[df_filtre['legislature'] != '']['legislature'].value_counts()
        if len(leg_counts) > 0:
            fig = px.bar(
                x=leg_counts.index,
                y=leg_counts.values,
                title="Documents par législature",
                labels={'x': 'Législature', 'y': 'Documents'},
                color=leg_counts.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune législure trouvée dans les données filtrées")
    
    with tab4:
        # Distribution des scores
        fig = px.histogram(
            df_filtre,
            x='score',
            nbins=20,
            title="Distribution des scores de pertinence",
            labels={'score': 'Score'},
            color_discrete_sequence=['#FF6B6B']
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # ==================== DÉTAILS PAR DOCUMENT ====================
    st.subheader("🔍 Détail document par document")
    
    if not df_filtre.empty:
        # Sélection d'un document
        options = [(row['id'], f"{row['id']} - {row['titre'][:80]}... [{row['type']}]") 
                  for _, row in df_filtre.iterrows()]
        
        selected_id = st.selectbox(
            "Choisir un document à inspecter",
            options=[opt[0] for opt in options],
            format_func=lambda x: dict(options).get(x, x)
        )
        
        if selected_id:
            doc = df_filtre[df_filtre['id'] == selected_id].iloc[0]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### 📄 {doc['titre']}")
                
                if doc['description'] and doc['description'] != "Pas de description":
                    with st.expander("📝 Description complète", expanded=True):
                        st.write(doc['description'])
                
                # URL
                if doc['url']:
                    st.markdown("**🔗 Lien original:**")
                    st.code(doc['url'])
                    
                    # Bouton pour ouvrir
                    st.markdown(
                        f'<a href="{doc["url"]}" target="_blank" style="text-decoration: none;">'
                        '<button style="padding: 10px 20px; background-color: #4CAF50; color: white; '
                        'border: none; border-radius: 5px; cursor: pointer; margin: 5px 0;">'
                        '📄 Ouvrir le document PDF</button></a>',
                        unsafe_allow_html=True
                    )
            
            with col2:
                st.markdown("**📊 Métadonnées**")
                
                info_cols = st.columns(2)
                with info_cols[0]:
                    st.metric("Type", doc['type'])
                    st.metric("Position", doc['position'])
                    st.metric("Score", f"{doc['score']:.1f}")
                
                with info_cols[1]:
                    st.metric("Législature", doc['legislature'] or "N/A")
                    st.metric("Période", doc['periode'])
                    st.metric("Date", doc['date_doc'])
                
                # Informations techniques
                with st.expander("⚙️ Techniques"):
                    st.write(f"**Format:** {doc['format']}")
                    st.write(f"**Source:** {doc['visible_url']}")
                    st.write(f"**ID technique:** {doc['doc_id']}")
                    st.write(f"**Extrait le:** {doc['timestamp'][:19]}")
    
    # ==================== EXPORT ====================
    st.subheader("💾 Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV complet
        csv_complet = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV COMPLET",
            data=csv_complet,
            file_name=f"bumidom_complet_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON structuré
        json_struct = json.dumps(donnees, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON STRUCTURÉ",
            data=json_struct.encode('utf-8'),
            file_name=f"bumidom_structuré_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Export URLs seulement
        urls = "\n".join([d['url'] for d in donnees if d['url']])
        st.download_button(
            label="🔗 LISTE DES URLs",
            data=urls.encode('utf-8'),
            file_name=f"urls_bumidom_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    # ==================== DONNÉES BRUTES ====================
    with st.expander("📊 DONNÉES BRUTES (extrait)", expanded=False):
        if st.session_state.json_brut:
            # Afficher un extrait des données brutes
            if 'results' in st.session_state.json_brut:
                st.json(st.session_state.json_brut['results'][:2])  # 2 premiers résultats
            elif isinstance(st.session_state.json_brut, list):
                st.json(st.session_state.json_brut[:2])
            else:
                st.json({k: st.session_state.json_brut[k] for k in list(st.session_state.json_brut.keys())[:2]})

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("📊 Analyseur des 131 documents BUMIDOM")
    
    st.success("""
    ### ✅ PRÊT À ANALYSER VOS 131 DOCUMENTS
    
    **Votre fichier contient les données réelles de l'API Google CSE.**
    
    ### 🎯 CE QUE CETTE VERSION FAIT DIFFÉREMMENT:
    1. **Analyse TOUS les 131 résultats** de votre fichier JSON
    2. **Parser SPÉCIFIQUE** pour votre structure de données
    3. **Extraction COMPLÈTE** des métadonnées
    4. **Interface OPTIMISÉE** pour 100+ résultats
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📋 CE QUI SERA EXTRACT:
        - **Tous les 131 résultats** du fichier
        - **Métadonnées complètes** de chaque document
        - **Informations techniques** (format, score, etc.)
        - **Données de contexte** (législature, période)
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 COMMENT PROCÉDER:
        1. **Assurez-vous** que `json.txt` est dans le bon dossier
        2. **Cliquez** sur le bouton dans la sidebar
        3. **Attendez** l'analyse complète
        4. **Explorez** TOUS les résultats
        
        ### ⏱️ TEMPS ESTIMÉ:
        - Chargement: 2-3 secondes
        - Parsing: 3-5 secondes
        - Total: < 10 secondes
        """)
    
    # Instructions techniques
    with st.expander("🔧 INFORMATIONS TECHNIQUES", expanded=False):
        st.markdown("""
        ### Structure attendue du fichier:
        ```
        {
          "context": {...},
          "results": [
            {
              "title": "...",
              "url": "...",
              "contentNoFormatting": "...",
              "fileFormat": "PDF/Adobe Acrobat",
              ...
            },
            ... 130 autres résultats ...
          ]
        }
        ```
        
        ### Caractéristiques de vos données:
        - **131 résultats** dans le tableau `results`
        - **Documents PDF** des archives de l'Assemblée Nationale
        - **Recherche sur BUMIDOM** (Bureau des migrations DOM)
        - **Période:** 1960s-1980s
        - **Source:** archives.assemblée-nationale.fr
        """)
    
    st.warning("""
    ⚠️ **IMPORTANT:** 
    Si vous ne voyez que 13 résultats avec l'ancienne version, 
    c'est parce qu'elle ne lisait pas correctement votre structure JSON.
    
    Cette nouvelle version est SPÉCIFIQUE à votre fichier.
    """)

# ==================== PIED DE PAGE ====================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard spécifique BUMIDOM • 131 documents analysés • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
