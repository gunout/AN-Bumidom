import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
import json
import time
from urllib.parse import quote
import io
import google.auth
from googleapiclient.discovery import build

# Configuration
st.set_page_config(
    page_title="Archives BUMIDOM - API Google", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Archives BUMIDOM - Recherche Google CSE")
st.markdown("Utilisation de l'API Google Custom Search Engine")

# Configuration Google CSE
CSE_ID = "014917347718038151697:kltwr00yvbk"  # ID du moteur de recherche du site
API_KEYS = [
    "AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY",  # Clé 1
    "AIzaSyB2Lp5C5dRhLkKxmwJHR0XCHXMr2h5IVJ8",  # Clé 2
    "AIzaSyD9YcP7R6QzJ3vYQvQz7Qj3vYQvQz7Qj3v",  # Clé 3 (générique)
]

def get_google_service(api_key_index=0):
    """Initialise le service Google Custom Search"""
    try:
        api_key = API_KEYS[api_key_index]
        return build("customsearch", "v1", developerKey=api_key)
    except Exception as e:
        st.warning(f"Clé API {api_key_index+1} échouée: {str(e)[:100]}")
        if api_key_index + 1 < len(API_KEYS):
            return get_google_service(api_key_index + 1)
        return None

def search_google_cse(query, page=1, results_per_page=10):
    """Recherche via Google Custom Search API"""
    
    service = get_google_service()
    if not service:
        return []
    
    try:
        start_index = (page - 1) * results_per_page + 1
        
        res = service.cse().list(
            q=query,
            cx=CSE_ID,
            start=start_index,
            num=results_per_page,
            lr='lang_fr',
            siteSearch='archives.assemblee-nationale.fr',
            sort='date'
        ).execute()
        
        return parse_google_results(res, page)
        
    except Exception as e:
        st.error(f"Erreur API Google: {str(e)[:200]}")
        return []

def parse_google_results(google_data, page_num):
    """Parse les résultats de Google"""
    
    results = []
    
    if 'items' not in google_data:
        return results
    
    for idx, item in enumerate(google_data['items']):
        try:
            title = item.get('title', '')
            url = item.get('link', '')
            snippet = item.get('snippet', '')
            
            # Informations supplémentaires
            pagemap = item.get('pagemap', {})
            
            # Extraire la date
            date = ""
            if 'metatags' in pagemap and pagemap['metatags']:
                metatags = pagemap['metatags'][0]
                date = metatags.get('article:published_time', 
                                  metatags.get('dc.date', 
                                             metatags.get('date', '')))
            
            # Extraire l'année
            year = extract_year(title + " " + snippet + " " + date)
            
            # Type de document
            doc_type = determine_document_type(title, snippet, url)
            
            # Législature
            legislature = extract_legislature(title, url)
            
            # Nom du fichier
            file_name = url.split('/')[-1] if '/' in url else ""
            
            # Mentions BUMIDOM
            mentions = count_bumidom_mentions(title + " " + snippet)
            
            # Informations de pagination
            display_link = item.get('displayLink', '')
            formatted_url = item.get('formattedUrl', '')
            
            results.append({
                'id': f"G{page_num}-{idx+1:03d}",
                'titre': title,
                'url': url,
                'extrait': snippet[:400] + "..." if len(snippet) > 400 else snippet,
                'date': format_date(date),
                'année': year,
                'type': doc_type,
                'législature': legislature,
                'fichier': file_name,
                'mentions': mentions,
                'page_source': page_num,
                'position': idx + 1,
                'display_link': display_link,
                'formatted_url': formatted_url,
                'cache_id': item.get('cacheId', ''),
                'source': 'Google CSE API'
            })
            
        except Exception as e:
            st.warning(f"Erreur parsing item {idx}: {str(e)[:100]}")
            continue
    
    return results

def extract_year(text):
    """Extrait l'année d'un texte"""
    matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
    if matches:
        try:
            return int(matches[0])  # Prendre la première année trouvée
        except:
            pass
    return None

def determine_document_type(title, snippet, url):
    """Détermine le type de document"""
    text = (title + " " + snippet).lower()
    url_lower = url.lower()
    
    # D'abord vérifier l'URL
    if '/cri/' in url_lower:
        if 'constitution' in text:
            return "Constitution"
        elif 'journal' in text or 'officiel' in text:
            return "Journal Officiel"
        elif 'compte rendu' in text:
            return "Compte Rendu"
        else:
            return "CRI"
    elif '/qst/' in url_lower:
        return "Question"
    elif '/tanalytique/' in url_lower:
        return "Tables analytiques"
    
    # Vérifier le texte
    if 'constitution' in text:
        return "Constitution"
    elif 'journal officiel' in text or 'j.o.' in text or 'jo ' in text:
        return "Journal Officiel"
    elif 'compte rendu' in text:
        return "Compte Rendu"
    elif 'séance' in text or 'seance' in text:
        return "Séance"
    elif 'débat' in text:
        return "Débat"
    elif 'rapport' in text:
        return "Rapport"
    
    return "Document"

def extract_legislature(title, url):
    """Extrait la législature"""
    # Chercher dans le titre
    leg_match = re.search(r'(\d+)(?:è?me|ème|°|\')\s*(?:législature|legislature|Leg)', title, re.I)
    if leg_match:
        return f"{leg_match.group(1)}ème"
    
    # Chercher dans l'URL (pattern: /4/cri/, /2/qst/, etc.)
    url_match = re.search(r'/(\d)/[a-z]+/', url)
    if url_match:
        leg_num = url_match.group(1)
        return f"{leg_num}ème"
    
    return ""

def count_bumidom_mentions(text):
    """Compte les mentions de BUMIDOM"""
    if not text:
        return 0
    text_lower = text.lower()
    return text_lower.count('bumidom')

def format_date(date_str):
    """Formate une date ISO en format lisible"""
    if not date_str:
        return ""
    
    # Essayer différents formats
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{1,2}\s+\w+\s+\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            return match.group(1)
    
    return date_str[:10]

def test_document_access(url):
    """Teste l'accessibilité d'un document"""
    if not url:
        return {'accessible': False, 'error': 'URL vide'}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    }
    
    try:
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        return {
            'accessible': response.status_code == 200,
            'status': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'is_pdf': 'pdf' in response.headers.get('content-type', '').lower(),
            'size': response.headers.get('content-length')
        }
    except Exception as e:
        return {'accessible': False, 'error': str(e)[:100]}

def download_document(url):
    """Télécharge un document"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Erreur: {str(e)[:100]}")
    return None

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration Google CSE")
        
        st.markdown("### 🔍 Paramètres de recherche")
        
        search_query = st.text_input("Terme de recherche:", value="BUMIDOM")
        total_pages = st.slider("Nombre de pages:", 1, 10, 5)
        results_per_page = st.selectbox("Résultats par page:", [10, 20, 30, 40, 50], index=0)
        
        st.markdown("### 🎯 Filtres")
        
        col_year1, col_year2 = st.columns(2)
        with col_year1:
            min_year = st.number_input("Année min:", 1900, 2025, 1960)
        with col_year2:
            max_year = st.number_input("Année max:", 1900, 2025, 1990)
        
        doc_types = st.multiselect(
            "Types de documents:",
            ["Tous", "Constitution", "Journal Officiel", "Compte Rendu", "CRI", 
             "Séance", "Question", "Tables analytiques", "Document"],
            default=["Tous"]
        )
        
        st.markdown("### ⚡ Options avancées")
        
        search_site = st.checkbox("Limiter au site archives.assemblee-nationale.fr", value=True)
        sort_by_date = st.checkbox("Trier par date", value=False)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            search_btn = st.button("🔍 Lancer la recherche", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state.search_results = None
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("### ℹ️ Informations API")
        st.info(f"""
        **Configuration:**
        - Moteur CSE: {CSE_ID[:20]}...
        - Pages: {total_pages}
        - Résultats/page: {results_per_page}
        - Période: {min_year}-{max_year}
        
        **Statut API:**
        - Clés disponibles: {len(API_KEYS)}
        - Site cible: archives.assemblee-nationale.fr
        """)
    
    # Initialisation
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'search_stats' not in st.session_state:
        st.session_state.search_stats = {}
    
    # Recherche
    if search_btn:
        with st.spinner("Recherche via Google CSE..."):
            all_results = []
            stats = {
                'total_documents': 0,
                'successful_pages': 0,
                'failed_pages': 0,
                'start_time': time.time()
            }
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num in range(1, total_pages + 1):
                status_text.text(f"Recherche page {page_num}/{total_pages}...")
                
                try:
                    # Construire la requête
                    query = search_query
                    if search_site:
                        query = f"site:archives.assemblee-nationale.fr {search_query}"
                    
                    page_results = search_google_cse(query, page_num, results_per_page)
                    
                    if page_results:
                        all_results.extend(page_results)
                        stats['successful_pages'] += 1
                        st.success(f"✓ Page {page_num}: {len(page_results)} résultats")
                    else:
                        stats['failed_pages'] += 1
                        st.warning(f"⚠ Page {page_num}: Aucun résultat")
                        
                except Exception as e:
                    stats['failed_pages'] += 1
                    st.error(f"✗ Page {page_num}: {str(e)[:100]}")
                
                # Mise à jour progression
                progress_bar.progress(page_num / total_pages)
                
                # Pause pour éviter les limites API
                time.sleep(2)
            
            stats['total_documents'] = len(all_results)
            stats['end_time'] = time.time()
            stats['duration'] = stats['end_time'] - stats['start_time']
            
            st.session_state.search_results = all_results
            st.session_state.search_stats = stats
            
            progress_bar.empty()
            status_text.empty()
            
            if all_results:
                st.success(f"✅ Recherche terminée ! {len(all_results)} documents trouvés en {stats['duration']:.1f}s.")
            else:
                st.warning("⚠️ Aucun document trouvé. Essayez avec moins de pages ou vérifiez les clés API.")
    
    # Affichage des résultats
    if st.session_state.search_results is not None:
        results = st.session_state.search_results
        stats = st.session_state.search_stats
        
        if results:
            # Statistiques
            st.subheader("📊 Statistiques de recherche")
            
            col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
            
            with col_stat1:
                st.metric("Documents", stats.get('total_documents', 0))
            with col_stat2:
                st.metric("Pages réussies", stats.get('successful_pages', 0))
            with col_stat3:
                st.metric("Durée", f"{stats.get('duration', 0):.1f}s")
            with col_stat4:
                years = len(set(r.get('année') for r in results if r.get('année')))
                st.metric("Années", years)
            with col_stat5:
                total_mentions = sum(r.get('mentions', 0) for r in results)
                st.metric("Mentions BUMIDOM", total_mentions)
            
            # Filtrage
            st.subheader("🎯 Filtrage des résultats")
            
            filtered_results = []
            for doc in results:
                # Filtre année
                year = doc.get('année')
                if year and (year < min_year or year > max_year):
                    continue
                
                # Filtre type
                doc_type = doc.get('type', 'Document')
                if "Tous" not in doc_types and doc_type not in doc_types:
                    continue
                
                filtered_results.append(doc)
            
            st.info(f"📄 {len(filtered_results)} documents après filtrage")
            
            # Affichage des documents
            st.subheader("📋 Documents trouvés")
            
            if filtered_results:
                # Pagination
                items_per_page = st.slider("Documents par page:", 5, 50, 10, key="display_pagination")
                total_pages_view = max(1, (len(filtered_results) + items_per_page - 1) // items_per_page)
                
                if total_pages_view > 1:
                    current_page = st.number_input("Page:", 1, total_pages_view, 1, key="display_page")
                    start_idx = (current_page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(filtered_results))
                    current_docs = filtered_results[start_idx:end_idx]
                    st.caption(f"Documents {start_idx+1}-{end_idx} sur {len(filtered_results)}")
                else:
                    current_docs = filtered_results
                
                # Tableau
                df_data = []
                for doc in current_docs:
                    df_data.append({
                        'ID': doc.get('id', ''),
                        'Titre': doc.get('titre', '')[:70] + ('...' if len(doc.get('titre', '')) > 70 else ''),
                        'Type': doc.get('type', ''),
                        'Année': doc.get('année', ''),
                        'Législature': doc.get('législature', ''),
                        'Page': doc.get('page_source', ''),
                        'Mentions': doc.get('mentions', 0),
                        'Fichier': doc.get('fichier', '')[:15]
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Détail d'un document
                st.subheader("🔍 Détail du document")
                
                if current_docs:
                    doc_options = [f"{doc['id']} - {doc['titre'][:60]}..." for doc in current_docs]
                    selected_option = st.selectbox("Sélectionner un document:", doc_options, key="doc_select")
                    
                    if selected_option:
                        selected_id = selected_option.split(' - ')[0]
                        selected_doc = next((d for d in current_docs if d['id'] == selected_id), None)
                        
                        if selected_doc:
                            col_detail1, col_detail2 = st.columns([2, 1])
                            
                            with col_detail1:
                                st.markdown(f"**ID:** {selected_doc.get('id', '')}")
                                st.markdown(f"**Titre:** {selected_doc.get('titre', '')}")
                                st.markdown(f"**Type:** {selected_doc.get('type', '')}")
                                st.markdown(f"**Source:** {selected_doc.get('source', '')}")
                                st.markdown(f"**Législature:** {selected_doc.get('législature', '')}")
                                st.markdown(f"**Année:** {selected_doc.get('année', '')}")
                                st.markdown(f"**Date:** {selected_doc.get('date', '')}")
                                st.markdown(f"**Page source:** {selected_doc.get('page_source', '')}")
                                st.markdown(f"**Position:** {selected_doc.get('position', '')}")
                                st.markdown(f"**Mentions BUMIDOM:** {selected_doc.get('mentions', 0)}")
                                st.markdown(f"**Fichier:** {selected_doc.get('fichier', '')}")
                                
                                if selected_doc.get('extrait'):
                                    st.markdown("**Extrait Google:**")
                                    extrait = selected_doc['extrait']
                                    # Mettre en évidence BUMIDOM
                                    highlighted = re.sub(
                                        r'(bumidom|BUMIDOM|Bumidom)',
                                        r'**\1**',
                                        extrait
                                    )
                                    st.markdown(f"> {highlighted}")
                                
                                if selected_doc.get('url'):
                                    st.markdown("**URL:**")
                                    st.code(selected_doc['url'])
                                
                                if selected_doc.get('formatted_url'):
                                    st.markdown("**URL formatée:**")
                                    st.code(selected_doc['formatted_url'])
                            
                            with col_detail2:
                                st.markdown("**Actions:**")
                                
                                if selected_doc.get('url'):
                                    # Test d'accès
                                    if st.button("🔗 Tester l'accès PDF", key=f"test_{selected_id}"):
                                        access_info = test_document_access(selected_doc['url'])
                                        
                                        if access_info.get('accessible'):
                                            st.success(f"✅ Accessible (HTTP {access_info.get('status')})")
                                            
                                            if access_info.get('is_pdf'):
                                                st.success("📄 Fichier PDF détecté")
                                                if access_info.get('size'):
                                                    size_mb = int(access_info.get('size')) / (1024 * 1024)
                                                    st.info(f"Taille: {size_mb:.1f} MB")
                                                
                                                # Téléchargement
                                                if st.button("📥 Télécharger PDF", key=f"dl_{selected_id}"):
                                                    pdf_content = download_document(selected_doc['url'])
                                                    if pdf_content:
                                                        filename = selected_doc.get('fichier', f"{selected_id}.pdf")
                                                        st.download_button(
                                                            label="💾 Sauvegarder PDF",
                                                            data=pdf_content,
                                                            file_name=filename,
                                                            mime="application/pdf",
                                                            key=f"save_{selected_id}"
                                                        )
                                            else:
                                                st.warning(f"Type: {access_info.get('content_type', 'Inconnu')}")
                                        else:
                                            st.error(f"❌ Non accessible")
                                            if access_info.get('error'):
                                                st.error(f"Erreur: {access_info.get('error')}")
                                    
                                    # Liens
                                    st.markdown("**Liens rapides:**")
                                    st.markdown(f"[🔗 Ouvrir le PDF]({selected_doc['url']})")
                                    
                                    if selected_doc.get('cache_id'):
                                        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{selected_doc['cache_id']}"
                                        st.markdown(f"[📄 Cache Google]({cache_url})")
            
            # Analyses
            st.subheader("📈 Analyses")
            
            tab1, tab2, tab3, tab4 = st.tabs(["Par année", "Par type", "Par législature", "Par page"])
            
            with tab1:
                year_counts = {}
                for doc in filtered_results:
                    year = doc.get('année')
                    if year:
                        if year not in year_counts:
                            year_counts[year] = 0
                        year_counts[year] += 1
                
                if year_counts:
                    df_years = pd.DataFrame({
                        'Année': list(year_counts.keys()),
                        'Documents': list(year_counts.values())
                    }).sort_values('Année')
                    
                    st.bar_chart(df_years.set_index('Année'))
                else:
                    st.info("Aucune donnée d'année disponible")
            
            with tab2:
                type_counts = {}
                for doc in filtered_results:
                    doc_type = doc.get('type', 'Inconnu')
                    if doc_type not in type_counts:
                        type_counts[doc_type] = 0
                    type_counts[doc_type] += 1
                
                if type_counts:
                    df_types = pd.DataFrame({
                        'Type': list(type_counts.keys()),
                        'Documents': list(type_counts.values())
                    })
                    
                    st.bar_chart(df_types.set_index('Type'))
            
            with tab3:
                leg_counts = {}
                for doc in filtered_results:
                    leg = doc.get('législature')
                    if leg:
                        if leg not in leg_counts:
                            leg_counts[leg] = 0
                        leg_counts[leg] += 1
                
                if leg_counts:
                    df_leg = pd.DataFrame({
                        'Législature': list(leg_counts.keys()),
                        'Documents': list(leg_counts.values())
                    })
                    
                    try:
                        df_leg['Num'] = df_leg['Législature'].str.extract(r'(\d+)').astype(int)
                        df_leg = df_leg.sort_values('Num')
                    except:
                        pass
                    
                    st.bar_chart(df_leg.set_index('Législature'))
            
            with tab4:
                page_counts = {}
                for doc in filtered_results:
                    page = doc.get('page_source', 1)
                    if page not in page_counts:
                        page_counts[page] = 0
                    page_counts[page] += 1
                
                if page_counts:
                    df_pages = pd.DataFrame({
                        'Page': list(page_counts.keys()),
                        'Documents': list(page_counts.values())
                    }).sort_values('Page')
                    
                    st.bar_chart(df_pages.set_index('Page'))
            
            # Export
            st.subheader("💾 Export des données")
            
            export_format = st.selectbox(
                "Format d'export:",
                ["CSV", "JSON", "Excel", "URLs seulement", "Rapport complet"]
            )
            
            if st.button("📤 Exporter les résultats"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if export_format == "CSV":
                    df_export = pd.DataFrame(filtered_results)
                    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv_data,
                        file_name=f"bumidom_google_{timestamp}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = json.dumps(filtered_results, ensure_ascii=False, indent=2)
                    
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json_data,
                        file_name=f"bumidom_google_{timestamp}.json",
                        mime="application/json"
                    )
                
                elif export_format == "Excel":
                    df_export = pd.DataFrame(filtered_results)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Résultats')
                        # Ajouter une feuille de statistiques
                        stats_df = pd.DataFrame([stats])
                        stats_df.to_excel(writer, index=False, sheet_name='Statistiques')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=excel_data,
                        file_name=f"bumidom_google_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                elif export_format == "URLs seulement":
                    urls = "\n".join([doc.get('url', '') for doc in filtered_results if doc.get('url')])
                    
                    st.download_button(
                        label="📥 Télécharger URLs",
                        data=urls,
                        file_name=f"bumidom_urls_{timestamp}.txt",
                        mime="text/plain"
                    )
                
                elif export_format == "Rapport complet":
                    rapport = f"""
                    RAPPORT DE RECHERCHE BUMIDOM - GOOGLE CSE
                    ===========================================
                    
                    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    Terme recherché: {search_query}
                    Pages analysées: {total_pages}
                    Documents trouvés: {len(filtered_results)}
                    Période couverte: {min_year}-{max_year}
                    
                    STATISTIQUES:
                    -------------
                    • Documents totaux: {len(filtered_results)}
                    • Pages réussies: {stats.get('successful_pages', 0)}
                    • Durée: {stats.get('duration', 0):.1f} secondes
                    • Années couvertes: {len(set(d.get('année') for d in filtered_results if d.get('année')))}
                    • Législatures: {len(set(d.get('législature') for d in filtered_results if d.get('législature')))}
                    • Mentions BUMIDOM totales: {sum(d.get('mentions', 0) for d in filtered_results)}
                    
                    LISTE DES DOCUMENTS:
                    --------------------
                    """
                    
                    for doc in filtered_results[:100]:  # Limiter à 100
                        rapport += f"""
                    {doc.get('id')} - {doc.get('titre')}
                      Type: {doc.get('type', 'N/A')}
                      Année: {doc.get('année', 'N/A')}
                      Législature: {doc.get('législature', 'N/A')}
                      Date: {doc.get('date', 'N/A')}
                      Mentions: {doc.get('mentions', 0)}
                      URL: {doc.get('url', 'N/A')}
                      Extrait: {doc.get('extrait', '')[:150]}...
                    """
                    
                    st.download_button(
                        label="📥 Télécharger Rapport",
                        data=rapport,
                        file_name=f"rapport_bumidom_{timestamp}.txt",
                        mime="text/plain"
                    )
        
        else:
            st.warning("⚠️ Aucun document trouvé")
            st.info("""
            **Suggestions:**
            1. Essayez avec moins de pages (1-2)
            2. Vérifiez que les clés API sont valides
            3. Essayez un terme de recherche plus large
            4. Attendez quelques minutes avant de réessayer (limites API)
            """)
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🔍 Recherche Archives BUMIDOM via Google CSE
        
        ### 🎯 Recherche en temps réel via l'API Google
        
        Cette application utilise l'**API Google Custom Search Engine** pour rechercher les documents BUMIDOM dans les archives de l'Assemblée Nationale.
        
        ### 🌐 Comment ça marche:
        
        1. **Identification** du moteur Google CSE intégré au site
        2. **Requête API** directe à Google
        3. **Extraction** des résultats avec métadonnées
        4. **Analyse** et présentation des données
        
        ### 📊 Données extraites:
        
        - **Titres complets** des documents
        - **URLs directes** vers les PDFs
        - **Extraits** de texte avec contexte
        - **Dates** de publication
        - **Législatures** concernées
        - **Types** de documents
        - **Nombre de mentions** BUMIDOM
        
        ### 🔧 Configuration requise:
        
        Pour utiliser cette application, vous avez besoin de **clés API Google valides**. 
        L'application inclut quelques clés par défaut, mais vous pouvez ajouter les vôtres.
        
        ### 🚀 Pour commencer:
        
        1. Configurez les paramètres dans la sidebar
        2. Cliquez sur **"Lancer la recherche"**
        3. Explorez les résultats avec les filtres
        4. Téléchargez les documents ou exportez les données
        """)
        
        with st.expander("🔑 Configuration des clés API"):
            st.markdown("""
            ### Comment ajouter vos propres clés API Google:
            
            1. **Créez un projet** sur [Google Cloud Console](https://console.cloud.google.com/)
            2. **Activez l'API** Custom Search
            3. **Générez une clé API**
            4. **Ajoutez-la** au tableau `API_KEYS` dans le code
            
            ### Limites de l'API Google:
            
            - **100 requêtes gratuites** par jour par clé
            - **10 résultats** par requête maximum
            - **Limite de débit** selon le plan
            
            ### Alternative sans API:
            
            Si vous ne pouvez pas utiliser l'API Google, vous pouvez:
            
            1. Utiliser la version avec données simulées
            2. Importer manuellement les données HTML
            3. Contacter les Archives pour un accès direct
            """)
            
            # Aperçu des clés actuelles
            st.code("""
            # Clés API actuelles dans le code:
            API_KEYS = [
                "AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY",
                "AIzaSyB2Lp5C5dRhLkKxmwJHR0XCHXMr2h5IVJ8", 
                "AIzaSyD9YcP7R6QzJ3vYQvQz7Qj3vYQvQz7Qj3v"
            ]
            """)

if __name__ == "__main__":
    main()
