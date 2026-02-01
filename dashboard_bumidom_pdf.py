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
st.markdown("**Analyse des données JSON d'API Google CSE**")

# ==================== FONCTIONS PRINCIPALES ====================

def parser_json_google_cse(json_data, page_num=1):
    """Parse les données JSON de l'API Google CSE"""
    resultats = []
    
    try:
        # Vérifier si c'est une fonction wrapper (JSONP style)
        if isinstance(json_data, dict) and len(json_data) == 1:
            # Extraire les données de la fonction wrapper (cas du fichier json.txt)
            func_name = list(json_data.keys())[0]
            data = json_data[func_name]
        else:
            data = json_data
        
        # Extraire les résultats (L'API officielle renvoie 'items', le JSON fichier renvoie 'results')
        if 'items' in data:
            items = data['items']
        elif 'results' in data:
            items = data['results']
        else:
            items = []
        
        for i, item in enumerate(items):
            try:
                # Extraire les informations selon la structure Google CSE
                titre = item.get('title', item.get('titleNoFormatting', f'Document {i+1}'))
                url = item.get('link', item.get('url', item.get('unescapedUrl', ''))) # 'link' est standard API v1
                
                # Gestion de la description/snippet
                description = item.get('snippet', '')
                if not description:
                    description = item.get('contentNoFormatting', item.get('content', ''))
                
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
                
                # Score de pertinence
                score = 100 - (i * 5) if i < 20 else 10
                
                # Métadonnées enrichies
                metadonnees = {}
                if 'richSnippet' in item:
                    metadonnees = item['richSnippet']
                if 'pagemap' in item: # Standard API v1 uses pagemap
                     metadonnees['pagemap'] = item['pagemap']
                if 'breadcrumbUrl' in item:
                    metadonnees['breadcrumbs'] = item['breadcrumbUrl'].get('crumbs', [])
                
                resultats.append({
                    'id': f"P{page_num:02d}R{i+1:03d}",
                    'titre': titre[:200] + "..." if len(titre) > 200 else titre,
                    'url': url,
                    'description': description[:300] + "..." if description and len(description) > 300 else description,
                    'type': type_doc,
                    'legislature': legislature,
                    'periode': periode,
                    'date_doc': date_doc,
                    'page': page_num,
                    'position': i + 1,
                    'score': score, # L'API standard ne renvoie pas toujours de score explicite
                    'format': file_format,
                    'visible_url': item.get('displayLink', item.get('visibleUrl', '')),
                    'metadonnees': json.dumps(metadonnees, ensure_ascii=False) if metadonnees else '',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                st.warning(f"Erreur sur l'élément {i+1}: {str(e)}")
                continue
        
        return resultats
        
    except Exception as e:
        st.error(f"Erreur lors du parsing JSON: {str(e)}")
        return []

def scraper_toutes_pages_api(api_key, cx_id, query, nombre_pages=10):
    """Scrape toutes les pages via l'API Google Custom Search JSON officielle"""
    tous_resultats = []
    # URL CORRECTE DE L'API OFFICIELLE
    base_url = "https://www.googleapis.com/customsearch/v1"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page in range(nombre_pages):
        start_index = (page * 10) + 1  # Google Custom Search API commence à 1, pas 0
        status_text.text(f"📄 Scraping page {page + 1}/{nombre_pages} (start={start_index})")
        
        # Paramètres de l'API Officielle
        params = {
            'key': api_key,
            'cx': cx_id,
            'q': query,
            'start': start_index,
            'num': 10  # Max 10 par requête pour l'API gratuite standard
        }
        
        try:
            # Headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    
                    # Parser les résultats (L'API officielle renvoie directement le dict, pas de wrapper)
                    resultats_page = parser_json_google_cse(json_data, page + 1)
                    
                    if resultats_page:
                        tous_resultats.extend(resultats_page)
                        # st.success(f"✅ Page {page + 1}: {len(resultats_page)} résultats") # Commenté pour ne pas spammer
                    else:
                        # Si plus de résultats, on arrête
                        if json_data.get('queries', {}).get('nextPage'):
                            st.warning(f"⚠️ Page {page + 1}: Format de réponse inattendu ou vide")
                        else:
                            st.info(f"🏁 Fin des résultats atteinte à la page {page + 1}")
                            progress_bar.progress(1.0)
                            break
                    
                except json.JSONDecodeError:
                    st.error(f"❌ Page {page + 1}: Réponse JSON invalide")
                    
            elif response.status_code == 403:
                st.error("❌ Erreur 403: Clé API invalide ou quota dépassé.")
                st.stop()
            else:
                st.error(f"❌ Page {page + 1}: HTTP {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Page {page + 1}: Erreur réseau - {str(e)}")
        
        # Mettre à jour la barre de progression
        progress_bar.progress((page + 1) / nombre_pages)
        
        # Pause pour éviter le rate limiting (Google API est généreuse mais restons polis)
        time.sleep(0.5)
    
    progress_bar.empty()
    status_text.empty()
    
    return tous_resultats

def charger_json_depuis_fichier():
    """Charge le JSON depuis le fichier json.txt"""
    try:
        if os.path.exists('json.txt'):
            with open('json.txt', 'r', encoding='utf-8') as f:
                json_content = f.read()
        else:
            # Utiliser le JSON fourni dans le code
            json_content = """/*O_o*/
google.search.cse.api12938({
  "cursor": {
    "currentPageIndex": 0,
    "estimatedResultCount": "131",
    "moreResultsUrl": "http://www.google.com/cse?oe=utf8&ie=utf8&source=uds&q=bumidom&safe=off&cx=014917347718038151697:kltwr00yvbk&start=0",
    "resultCount": "131",
    "searchResultTime": "0.30",
    "pages": [
      { "label": 1, "start": "0" }, { "label": 2, "start": "10" }, { "label": 3, "start": "20" }
    ]
  },
  "results": [
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAgQAg&usg=AOvVaw3XQEsRa-ZOw0c9nxuM7XyR",
      "content": "26 oct. 1971 \\u003cb\\u003e...\\u003c/b\\u003e \\u003cb\\u003eBumidom\\u003c/b\\u003e. Nous avons donc fait un effort très sérieux — je crois qu'il commence à porter ses fruits — pour l'information, comme on l'a&nbsp;...",
      "title": "JOURNAL OFFICIAL - Assemblée nationale - Archives",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAYQAQ&usg=AOvVaw0kEy49-XtbL0tnPLfpTQKs",
      "content": "le \\u003cb\\u003eBUMIDOM\\u003c/b\\u003e qui, en 1965, a facilité l'installation en métropole. La réalisation effective de la parité globale se poursuivra de 7.000 personnes. en. 1967 . C&nbsp;...",
      "title": "Assemblée nationale - Archives",
      "url": "https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "fileFormat": "PDF/Adobe Acrobat"
    }
  ]
});"""
        
        # Nettoyer et parser le JSON (Logique existante conservée)
        json_str = json_content.strip()
        if json_str.startswith('/*'):
            json_str = json_str.split('*/', 1)[1].strip()
        
        start_idx = json_str.find('{')
        end_idx = json_str.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("Format JSON invalide")
        
        json_data_str = json_str[start_idx:end_idx]
        data = json.loads(json_data_str)
        
        return data
        
    except Exception as e:
        st.error(f"Erreur lors du chargement du JSON: {str(e)}")
        return None

# ==================== INTERFACE STREAMLIT ====================

# Initialisation du state
if 'donnees_json' not in st.session_state:
    st.session_state.donnees_json = None
if 'resultats_parses' not in st.session_state:
    st.session_state.resultats_parses = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # --- NOUVEAU : Configuration API ---
    st.subheader("Clé API Google (Requis)")
    api_key = st.text_input("API Key", type="password", help="Nécessaire pour le mode 'Scraper l'API'. Obtenez-la sur Google Cloud Console.")
    
    # Recherche par défaut
    default_query = "bumidom"
    default_cx = "014917347718038151697:kltwr00yvbk"
    
    # Options d'analyse
    st.subheader("Options d'analyse")
    
    option_chargement = st.radio(
        "Source des données:",
        ["JSON intégré (2 résultats)", "Fichier json.txt", "Scraper l'API (Officielle)"],
        index=0
    )
    
    if option_chargement == "Scraper l'API (Officielle)":
        nombre_pages = st.slider("Nombre de pages à scraper", 1, 10, 3) # Réduit à 3 par défaut pour la vitesse
        query_search = st.text_input("Terme de recherche", value=default_query)
        cx_search = st.text_input("ID Moteur (CX)", value=default_cx)
        st.info("🔑 Clé API requise. 100 requêtes/jour gratuit.")
    
    # Bouton pour charger le JSON
    btn_text = "📁 Analyser le JSON" if option_chargement != "Scraper l'API (Officielle)" else "🚀 Scraper via API Google"
    
    if st.button(btn_text, type="primary", use_container_width=True):
        with st.spinner("Chargement et analyse en cours..."):
            if option_chargement == "Fichier json.txt":
                if os.path.exists('json.txt'):
                    with open('json.txt', 'r', encoding='utf-8') as f:
                        json_content = f.read()
                    
                    json_str = json_content.strip()
                    if json_str.startswith('/*'):
                        json_str = json_str.split('*/', 1)[1].strip()
                    
                    start_idx = json_str.find('{')
                    end_idx = json_str.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx > 0:
                        json_data_str = json_str[start_idx:end_idx]
                        json_data = json.loads(json_data_str)
                    else:
                        st.error("Format invalide dans json.txt")
                        json_data = None
                else:
                    st.error("Fichier json.txt introuvable")
                    json_data = None
                    
            elif option_chargement == "Scraper l'API (Officielle)":
                if not api_key:
                    st.error("❌ Veuillez entrer une Clé API Google dans la configuration.")
                    st.stop()
                
                # Appeler la fonction de scraping mise à jour
                resultats = scraper_toutes_pages_api(api_key, cx_search, query_search, nombre_pages)
                
                if resultats:
                    st.session_state.resultats_parses = resultats
                    st.success(f"✅ Scraping terminé: {len(resultats)} résultats trouvés!")
                else:
                    st.error("❌ Aucun résultat trouvé. Vérifiez votre Clé API et le CX.")
                st.stop()
                
            else:
                # Utiliser le JSON intégré
                json_data = charger_json_depuis_fichier()
            
            if json_data:
                st.session_state.donnees_json = json_data
                resultats = parser_json_google_cse(json_data, 1)
                st.session_state.resultats_parses = resultats
                
                actual_count = len(resultats)
                st.success(f"✅ JSON analysé: {actual_count} résultats trouvés!")
            else:
                st.error("❌ Impossible de charger le JSON")
    
    # Afficher les statistiques
    if st.session_state.resultats_parses:
        st.divider()
        st.subheader("📊 Statistiques")
        total = len(st.session_state.resultats_parses)
        st.metric("Total", total)

# Contenu principal (Identique au code original)
if st.session_state.resultats_parses:
    donnees = st.session_state.resultats_parses
    df = pd.DataFrame(donnees)
    
    st.header("📈 Vue d'ensemble des données JSON")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Documents", len(df))
    with col2: st.metric("PDF", df[df['type'] == 'PDF'].shape[0])
    with col3: st.metric("Comptes rendus", df[df['type'] == 'Compte rendu'].shape[0])
    with col4: st.metric("Journaux Officiels", df[df['type'] == 'Journal Officiel'].shape[0])
    
    st.header("📄 Résultats extraits")
    
    # Filtres et affichage (condensé pour la clarté)
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            types_selection = st.multiselect("Types", sorted(df['type'].unique()), default=sorted(df['type'].unique()))
        with col2:
            legislatures = sorted([l for l in df['legislature'].unique() if l])
            leg_selection = st.multiselect("Législatures", legislatures, default=legislatures)
        with col3:
            periodes = sorted([p for p in df['periode'].unique() if p != "Inconnue"])
            periode_selection = st.multiselect("Périodes", periodes, default=periodes[:5] if len(periodes) > 5 else periodes)

    df_filtre = df[
        df['type'].isin(types_selection) &
        df['legislature'].isin(leg_selection + ['']) &
        (df['periode'].isin(periode_selection) | (df['periode'] == "Inconnue") if periode_selection else True)
    ]
    
    st.info(f"📋 Affichage de {len(df_filtre)} documents sur {len(df)}")
    
    st.dataframe(
        df_filtre[['id', 'titre', 'type', 'legislature', 'periode', 'date_doc']],
        use_container_width=True,
        hide_index=True
    )
    
    # Visualisations (condensé)
    st.header("📊 Visualisations")
    tab1, tab2 = st.tabs(["Distribution", "Détails"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            type_counts = df_filtre['type'].value_counts()
            fig = px.pie(values=type_counts.values, names=type_counts.index, title="Par type")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            leg_data = df_filtre[df_filtre['legislature'] != '']
            if not leg_data.empty:
                leg_counts = leg_data['legislature'].value_counts()
                fig = px.bar(x=leg_counts.index, y=leg_counts.values, title="Par Législature")
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger CSV", data=csv, file_name="resultats.csv", mime="text/csv")

else:
    st.info("👈 Configurez l'API ou chargez un fichier dans la sidebar pour commencer.")
