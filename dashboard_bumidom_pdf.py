import streamlit as st
import pandas as pd
import re
from datetime import datetime
import base64
import io
import requests

# Configuration
st.set_page_config(
    page_title="Analyse BUMIDOM - Résultats Google", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse des Résultats Google BUMIDOM")
st.markdown("Extraction et analyse des informations depuis vos résultats Google")

def parse_google_results():
    """Parse les résultats Google structurés"""
    
    # Données structurées extraites du HTML fourni
    results_data = [
        {
            'title': 'JOURNAL OFFICIAL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf',
            'date': '26 oct. 1971',
            'extract': 'Bumidom. Nous avons donc fait un effort très sérieux — je crois qu\'il commence à porter ses fruits — pour l\'information, comme on l\'a ...',
            'year': 1971,
            'file_name': '024.pdf'
        },
        {
            'title': 'CONSTITUTION DU 4 OCTOBRE 1958 4\' Législature',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1968-1969-ordinaire1/050.pdf',
            'date': '9 nov. 2025',
            'extract': 'Bumidom. Dès mon arrivée au ministère, je me suis essentiellement préoccupé des conditions d\'accueil et d\'adaptation des originaires des ...',
            'year': 1968,
            'file_name': '050.pdf'
        },
        {
            'title': 'Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf',
            'date': '',
            'extract': 'le BUMIDOM qui, en 1965, a facilité l\'installation en métropole. La réalisation effective de la parité globale se poursuivra de 7.000 personnes. en. 1967 . C ...',
            'year': 1966,
            'file_name': '021.pdf'
        },
        {
            'title': 'CONSTITUTION DU 4 OCTOBRE 1958 7\' Législature',
            'url': 'https://archives.assemblee-nationale.fr/7/cri/1982-1983-ordinaire1/057.pdf',
            'date': '5 nov. 1982',
            'extract': 'Le Bumidom, tant décrié par vos amis, a été, dans la pratique, remplacé par un succédané — l\'agence nationale pour l\'insertion et la ...',
            'year': 1982,
            'file_name': '057.pdf'
        },
        {
            'title': 'COMPTE RENDU INTEGRAL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/057.pdf',
            'date': '27 janv. 2025',
            'extract': 'des crédits affectés au Bumidom pour les années 1976 et 1977;. 2° les raisons de la réduction des crédits pour l\'année 1977 si tou- tefois ...',
            'year': 1976,
            'file_name': '057.pdf'
        },
        {
            'title': 'CONSTITUTION DU 4 OCTOBRE 1958 4° Législature',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/060.pdf',
            'date': '16 nov. 1970',
            'extract': 'des départements d\'outre-mer — Bumidom — dont l\'objectif est à la fois de faciliter l\'immigration et d\'orienter les tra- vailleurs vers un ...',
            'year': 1970,
            'file_name': '060.pdf'
        },
        {
            'title': 'DE LA RÉPUBLIQUE FRANÇAISE - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/8/cri/1985-1986-extraordinaire1/015.pdf',
            'date': '11 juil. 1986',
            'extract': 'Bumidom . On crée l \' A.N.T., Agence nationale pour l \' inser- tion et la promotion des travailleurs. Le slogan gouverne- mental était ...',
            'year': 1985,
            'file_name': '015.pdf'
        },
        {
            'title': 'JOUR AL OFFICIEL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/067.pdf',
            'date': '5 nov. 2025',
            'extract': 'société d \'Etat « Bumidom », qui prend à sa charge les frais du voyage. En conséquence, il lui demande quelles mesures il compte prendre ...',
            'year': 1971,
            'file_name': '067.pdf'
        },
        {
            'title': 'CONSTITUTION DU 4 OCTOBRE 1958 4° Législature',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/023.pdf',
            'date': '26 oct. 1970',
            'extract': 'Le Bumidom ne devrait pas être traité comme un instrument de la ... tés d\'accueil et du Bumidom, c\'est-à-dire du bureau des migrations.',
            'year': 1970,
            'file_name': '023.pdf'
        },
        {
            'title': 'JOUR: AL OFFICIEL - Assemblée nationale - Archives',
            'url': 'https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire2/007.pdf',
            'date': '7 mars 2025',
            'extract': 'nisée par le Bumidom, est loin d\'être satisfaisante. Ses effets sont du reste annihilés par l\'entrée d\'une main-d\'oeuvre impor- tante dans ...',
            'year': 1970,
            'file_name': '007.pdf'
        }
    ]
    
    # Formater les résultats
    formatted_results = []
    for i, result in enumerate(results_data):
        # Extraire le nom de fichier pour l'URL partielle
        url_parts = result['url'].split('/')
        url_part = '/'.join(url_parts[-4:]) if len(url_parts) >= 4 else result['url']
        
        # Identifier le type de document
        doc_type = "CRI"
        title_upper = result['title'].upper()
        if 'CONSTITUTION' in title_upper:
            doc_type = "Constitution"
        elif 'JOURNAL' in title_upper or 'JOUR' in title_upper:
            doc_type = "Journal Officiel"
        elif 'COMPTE RENDU' in title_upper:
            doc_type = "Compte Rendu"
        elif 'RÉPUBLIQUE' in title_upper:
            doc_type = "Débat parlementaire"
        
        # Extraire la législature
        legislature = ""
        if "4'" in result['title'] or "4°" in result['title']:
            legislature = "4ème"
        elif "7'" in result['title']:
            legislature = "7ème"
        elif "2'" in result['title'] or "Assemblée nationale" in result['title']:
            legislature = "2ème"
        elif "5'" in result['title']:
            legislature = "5ème"
        elif "8'" in result['title']:
            legislature = "8ème"
        
        # Extraire la période parlementaire de l'URL
        periode = ""
        if 'ordinaire1' in result['url']:
            periode = "Session ordinaire 1"
        elif 'ordinaire2' in result['url']:
            periode = "Session ordinaire 2"
        elif 'extraordinaire' in result['url']:
            periode = "Session extraordinaire"
        
        formatted_results.append({
            'id': i + 1,
            'titre': result['title'],
            'url': result['url'],
            'url_part': url_part,
            'file_name': result['file_name'],
            'année': result['year'],
            'date': result['date'],
            'extrait': result['extract'],
            'type': doc_type,
            'législature': legislature,
            'période': periode
        })
    
    return formatted_results

def extract_context(extrait, keyword="BUMIDOM"):
    """Extrait le contexte autour du mot-clé"""
    if not extrait:
        return ""
    
    # Trouver la position du mot-clé
    texte_lower = extrait.lower()
    keyword_lower = keyword.lower()
    
    pos = texte_lower.find(keyword_lower)
    if pos == -1:
        return extrait[:150] + "..." if len(extrait) > 150 else extrait
    
    # Extraire 100 caractères avant et après
    start = max(0, pos - 100)
    end = min(len(extrait), pos + len(keyword) + 100)
    
    context = extrait[start:end]
    
    # Ajouter des ellipses si nécessaire
    if start > 0:
        context = "..." + context
    if end < len(extrait):
        context = context + "..."
    
    return context

def test_url_access(url):
    """Teste l'accessibilité d'une URL"""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return {
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'accessible': response.status_code == 200
        }
    except Exception as e:
        return {
            'status_code': 0,
            'content_type': '',
            'accessible': False,
            'error': str(e)
        }

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Analyse des résultats")
        
        keyword = st.text_input("Mot-clé analysé:", value="BUMIDOM")
        
        st.markdown("### 📊 Filtres")
        
        show_all = st.checkbox("Afficher tous les résultats", value=True)
        
        if show_all:
            min_year = st.slider("Année minimum:", 1960, 1990, 1966)
            max_year = st.slider("Année maximum:", 1960, 1990, 1986)
        
        st.markdown("### 🏛️ Filtres par type")
        doc_types = st.multiselect(
            "Types de documents:",
            ["Tous", "CRI", "Constitution", "Journal Officiel", "Compte Rendu", "Débat parlementaire"],
            default=["Tous"]
        )
        
        st.markdown("### 📅 Filtres par législature")
        legislatures = st.multiselect(
            "Législatures:",
            ["Toutes", "2ème", "4ème", "5ème", "7ème", "8ème"],
            default=["Toutes"]
        )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            analyze_btn = st.button("🔍 Analyser résultats", type="primary", use_container_width=True)
        with col2:
            export_btn = st.button("📥 Exporter données", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Source:** Archives de l'Assemblée Nationale
        **Période:** 1966-1986
        **Documents:** 10 résultats trouvés
        **Format:** Documents PDF
        """)
    
    # Analyse des résultats
    if analyze_btn or 'results' not in st.session_state:
        with st.spinner("Analyse des résultats Google..."):
            results = parse_google_results()
            st.session_state.results = results
    
    # Affichage des résultats
    if 'results' in st.session_state:
        results = st.session_state.results
        
        st.success(f"✅ {len(results)} documents trouvés dans les Archives de l'Assemblée Nationale")
        
        # Statistiques
        st.subheader("📈 Statistiques")
        
        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
        with col_stat1:
            st.metric("Documents", len(results))
        with col_stat2:
            years = len(set(r['année'] for r in results if r['année'] != 'N/A'))
            st.metric("Années", years)
        with col_stat3:
            types = len(set(r['type'] for r in results))
            st.metric("Types", types)
        with col_stat4:
            legislatures_count = len(set(r['législature'] for r in results if r['législature']))
            st.metric("Législatures", legislatures_count)
        with col_stat5:
            mentions = sum(1 for r in results if 'extrait' in r and r['extrait'])
            st.metric("Mentions", mentions)
        
        # Tableau des résultats
        st.subheader("📋 Documents trouvés")
        
        # Filtrer les résultats
        filtered_results = results
        
        # Filtrer par année
        if 'show_all' in locals() and not show_all:
            filtered_results = [r for r in filtered_results 
                              if r['année'] != 'N/A' 
                              and min_year <= r['année'] <= max_year]
        
        # Filtrer par type
        if "Tous" not in doc_types and doc_types:
            filtered_results = [r for r in filtered_results if r['type'] in doc_types]
        
        # Filtrer par législature
        if "Toutes" not in legislatures and legislatures:
            filtered_results = [r for r in filtered_results if r['législature'] in legislatures]
        
        st.info(f"📄 {len(filtered_results)} documents après filtrage")
        
        # Afficher chaque document
        for doc in filtered_results:
            with st.expander(f"📄 {doc['titre'][:80]}... ({doc['année']}) - Législature {doc['législature']}"):
                col_doc1, col_doc2 = st.columns([3, 1])
                
                with col_doc1:
                    st.markdown(f"**Type:** {doc['type']}")
                    st.markdown(f"**Année:** {doc['année']}")
                    st.markdown(f"**Date:** {doc['date']}")
                    st.markdown(f"**Législature:** {doc['législature']}")
                    st.markdown(f"**Période:** {doc['période']}")
                    st.markdown(f"**Fichier:** `{doc['file_name']}`")
                    
                    # Afficher l'URL complète comme lien cliquable
                    st.markdown(f"**URL complète:** [{doc['url']}]({doc['url']})")
                    
                    # Extrait Google
                    if doc['extrait']:
                        st.markdown("**Extrait Google:**")
                        # Mettre en évidence le mot-clé
                        highlighted = re.sub(
                            r'(' + re.escape(keyword) + ')',
                            r'**\1**',
                            doc['extrait'],
                            flags=re.IGNORECASE
                        )
                        st.markdown(f"> {highlighted}")
                    
                    # Informations supplémentaires
                    st.markdown("**Structure d'URL:**")
                    st.code(doc['url'])
                
                with col_doc2:
                    # Test d'accès
                    st.markdown("**Accès:**")
                    
                    if st.button("🔗 Tester l'accès", key=f"test_{doc['id']}"):
                        access_info = test_url_access(doc['url'])
                        
                        if access_info['accessible']:
                            st.success(f"✅ Accessible ({access_info['status_code']})")
                            
                            # Vérifier si c'est un PDF
                            if 'pdf' in access_info['content_type'].lower():
                                st.info("📄 Fichier PDF détecté")
                                
                                # Option de téléchargement
                                try:
                                    pdf_response = requests.get(doc['url'], timeout=10)
                                    st.download_button(
                                        label="📥 Télécharger PDF",
                                        data=pdf_response.content,
                                        file_name=f"{doc['file_name']}",
                                        mime="application/pdf",
                                        key=f"dl_{doc['id']}"
                                    )
                                except Exception as e:
                                    st.error(f"❌ Erreur de téléchargement: {str(e)[:50]}")
                            else:
                                st.warning(f"⚠️ Type: {access_info['content_type']}")
                        else:
                            if 'error' in access_info:
                                st.error(f"❌ Erreur: {access_info['error'][:50]}")
                            else:
                                st.error(f"❌ Erreur {access_info['status_code']}")
        
        # Analyses visuelles
        col_anal1, col_anal2 = st.columns(2)
        
        with col_anal1:
            # Analyse par année
            st.subheader("📅 Répartition par année")
            
            year_data = {}
            for doc in results:
                if doc['année'] != 'N/A':
                    year = doc['année']
                    if year not in year_data:
                        year_data[year] = 0
                    year_data[year] += 1
            
            if year_data:
                df_years = pd.DataFrame({
                    'Année': list(year_data.keys()),
                    'Documents': list(year_data.values())
                }).sort_values('Année')
                
                st.bar_chart(df_years.set_index('Année'))
        
        with col_anal2:
            # Analyse par législature
            st.subheader("🏛️ Répartition par législature")
            
            legislature_data = {}
            for doc in results:
                if doc['législature']:
                    leg = doc['législature']
                    if leg not in legislature_data:
                        legislature_data[leg] = 0
                    legislature_data[leg] += 1
            
            if legislature_data:
                # Trier par ordre numérique
                leg_df = pd.DataFrame({
                    'Législature': list(legislature_data.keys()),
                    'Documents': list(legislature_data.values())
                })
                
                # Extraire le numéro pour trier
                leg_df['Num'] = leg_df['Législature'].str.extract(r'(\d+)').astype(int)
                leg_df = leg_df.sort_values('Num')
                
                st.bar_chart(leg_df.set_index('Législature')['Documents'])
        
        # Table des URLs
        st.subheader("🔗 URLs trouvées")
        
        urls_table = pd.DataFrame([{
            'ID': doc['id'],
            'Année': doc['année'],
            'Législature': doc['législature'],
            'Type': doc['type'],
            'Fichier': doc['file_name'],
            'URL': doc['url']
        } for doc in results])
        
        st.dataframe(urls_table, use_container_width=True, hide_index=True)
        
        # Export des données
        if export_btn:
            st.subheader("💾 Export des données")
            
            # Données complètes
            df_complet = pd.DataFrame(results)
            
            col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
            
            with col_exp1:
                # CSV complet
                csv_data = df_complet.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📊 CSV complet",
                    data=csv_data,
                    file_name=f"bumidom_archives_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col_exp2:
                # URLs seulement
                urls_csv = urls_table.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="🔗 URLs seulement",
                    data=urls_csv,
                    file_name=f"bumidom_urls_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col_exp3:
                # Rapport textuel
                rapport = f"""
                RAPPORT D'ANALYSE BUMIDOM - ARCHIVES ASSEMBLÉE NATIONALE
                ==========================================================
                
                Date d'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                Nombre de documents: {len(results)}
                Période couverte: {min(r['année'] for r in results if r['année'] != 'N/A')}-{max(r['année'] for r in results if r['année'] != 'N/A')}
                
                DOCUMENTS TROUVÉS:
                ------------------
                
                """
                
                for doc in results:
                    rapport += f"""
                {doc['id']}. {doc['titre']}
                   Année: {doc['année']}
                   Législature: {doc['législature']}
                   Type: {doc['type']}
                   Fichier: {doc['file_name']}
                   URL: {doc['url']}
                   Extrait: {doc['extrait'][:150]}...
                   
                """
                
                st.download_button(
                    label="📝 Rapport texte",
                    data=rapport,
                    file_name=f"rapport_bumidom_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
            
            with col_exp4:
                # Liste des URLs pour navigateur
                urls_list = "\n".join([doc['url'] for doc in results])
                st.download_button(
                    label="🌐 URLs pour navigateur",
                    data=urls_list,
                    file_name=f"bumidom_urls_list_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🎯 Analyse des Archives BUMIDOM - Assemblée Nationale
        
        ### 📚 Informations disponibles:
        
        Les documents suivants ont été identifiés dans les archives de l'Assemblée Nationale:
        
        1. **Documents PDF** accessibles directement
        2. **Informations structurées** : titre, date, législature, type
        3. **Extraits de texte** contenant "BUMIDOM"
        4. **URLs complètes** pour accès direct
        
        ### 🚀 Fonctionnalités:
        
        - **Analyse automatique** des résultats
        - **Test d'accessibilité** des documents PDF
        - **Téléchargement direct** des fichiers
        - **Filtrage avancé** par année, type, législature
        - **Export des données** en multiples formats
        
        ### 📋 Exemple d'information historique:
        
        ```
        "le BUMIDOM qui, en 1965, a facilité l'installation en métropole."
        ```
        
        Cette phrase provient du document **1966-1967-ordinaire1/021.pdf** et témoigne du rôle historique du BUMIDOM.
        
        ### ⏱️ Cliquez sur "🔍 Analyser résultats" pour commencer
        """)

if __name__ == "__main__":
    main()
