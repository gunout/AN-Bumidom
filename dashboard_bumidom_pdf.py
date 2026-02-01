import streamlit as st
import pandas as pd
import re
from datetime import datetime
import base64
import io

# Configuration
st.set_page_config(
    page_title="Analyse BUMIDOM - Résultats Google", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse des Résultats Google BUMIDOM")
st.markdown("Extraction et analyse des informations depuis vos résultats Google")

def parse_google_results():
    """Parse vos résultats Google affichés"""
    
    # Vos résultats Google (collés depuis votre message)
    google_results_text = """
    JOURNAL OFFICIAL - Assemblée nationale - Archives
    archives.assemblee-nationale.fr › cri › 1971-1972-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    26 oct. 1971 ... Bumidom. Nous avons donc fait un effort très sérieux — je crois qu'il commence à porter ses fruits — pour l'information, comme on l'a ...
    
    CONSTITUTION DU 4 OCTOBRE 1958 4' Législature
    archives.assemblee-nationale.fr › cri › 1968-1969-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    9 nov. 2025 ... Bumidom. Dès mon arrivée au ministère, je me suis essentielle- ment préoccupé des conditions d'accueil et d'adaptation des originaires des ...
    
    Assemblée nationale - Archives
    archives.assemblee-nationale.fr › cri › 1966-1967-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    le BUMIDOM qui, en 1965, a facilité l'installation en métropole. La réalisation effective de la parité globale se poursuivra de 7.000 personnes. en. 1967 . C ...
    
    CONSTITUTION DU 4 OCTOBRE 1958 7' Législature
    archives.assemblee-nationale.fr › cri › 1982-1983-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    5 nov. 1982 ... Le Bumidom, tant décrié par vos amis, a été, dans la pratique, remplacé par un succédané — l'agence nationale pour l'insertion et la ...
    
    COMPTE RENDU INTEGRAL - Assemblée nationale - Archives
    archives.assemblee-nationale.fr › cri › 1976-1977-ordinaire2
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    27 janv. 2025 ... des crédits affectés au Bumidom pour les années 1976 et 1977;. 2° les raisons de la réduction des crédits pour l'année 1977 si tou- tefois ...
    
    CONSTITUTION DU 4 OCTOBRE 1958 4° Législature
    archives.assemblee-nationale.fr › cri › 1970-1971-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    16 nov. 1970 ... des départements d'outre-mer — Bumidom — dont l'objectif est à la fois de faciliter l'immigration et d'orienter les tra- vailleurs vers un ...
    
    JOUR AL OFFICIEL - Assemblée nationale - Archives
    archives.assemblee-nationale.fr › cri › 1971-1972-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    5 nov. 2025 ... société d 'Etat « Bumidom », qui prend à sa charge les frais du voyage. En conséquence, il lui demande quelles mesures il compte prendre ...
    
    CONSTITUTION DU 4 OCTOBRE 1958 4° Législature
    archives.assemblee-nationale.fr › cri › 1970-1971-ordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    26 oct. 1970 ... Le Bumidom ne devrait pas être traité comme un instrument de la ... tés d'accueil et du Bumidom, c'est-à-dire du bureau des migrations.
    
    DE LA RÉPUBLIQUE FRANÇAISE - Assemblée nationale - Archives
    archives.assemblee-nationale.fr › cri › 1985-1986-extraordinaire1
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    11 juil. 1986 ... Bumidom . On crée l ' A.N.T., Agence nationale pour l ' inser- tion et la promotion des travailleurs. Le slogan gouverne- mental était ...
    
    JOUR: AL OFFICIEL - Assemblée nationale - Archives
    archives.assemblee-nationale.fr › cri › 1970-1971-ordinaire2
    Image miniature
    Format de fichier : PDF/Adobe Acrobat
    7 mars 2025 ... nisée par le Bumidom, est loin d'être satisfaisante. Ses effets sont du reste annihilés par l'entrée d'une main-d'oeuvre impor- tante dans ...
    """
    
    # Analyser le texte
    lines = google_results_text.strip().split('\n')
    results = []
    current_result = {}
    
    for line in lines:
        line = line.strip()
        
        # Nouveau résultat commence par un titre
        if line and not line.startswith('archives.assemblee-nationale.fr') and not line.startswith('Image') and not line.startswith('Format'):
            if current_result:
                results.append(current_result)
                current_result = {}
            
            if line and len(line) > 10:
                current_result['title'] = line
        
        # URL trouvée
        elif 'archives.assemblee-nationale.fr' in line:
            # Extraire l'URL partielle
            match = re.search(r'› cri › (.+)$', line)
            if match:
                url_part = match.group(1).strip()
                current_result['url_part'] = url_part
                
                # Extraire l'année
                year_match = re.search(r'(\d{4})-(\d{4})', url_part)
                if year_match:
                    current_result['year_start'] = int(year_match.group(1))
                    current_result['year_end'] = int(year_match.group(2))
                    current_result['year'] = int(year_match.group(1))
        
        # Date trouvée
        elif re.search(r'\d{1,2}\s+\w+\.?\s+\d{4}', line):
            date_match = re.search(r'(\d{1,2}\s+\w+\.?\s+\d{4})', line)
            if date_match:
                current_result['date'] = date_match.group(1)
        
        # Extrait de texte
        elif 'Bumidom' in line or 'BUMIDOM' in line:
            if 'extract' not in current_result:
                current_result['extract'] = line
            else:
                current_result['extract'] += " " + line
    
    # Ajouter le dernier résultat
    if current_result:
        results.append(current_result)
    
    # Nettoyer et formater les résultats
    formatted_results = []
    for i, result in enumerate(results):
        if 'title' in result and 'url_part' in result:
            # Construire l'URL complète
            url = f"https://archives.assemblee-nationale.fr/cri/{result['url_part']}"
            
            # Identifier le type de document
            doc_type = "CRI"
            if 'CONSTITUTION' in result.get('title', ''):
                doc_type = "Constitution"
            elif 'JOURNAL' in result.get('title', ''):
                doc_type = "Journal Officiel"
            elif 'COMPTE RENDU' in result.get('title', ''):
                doc_type = "Compte Rendu"
            
            formatted_results.append({
                'id': i + 1,
                'titre': result.get('title', 'Document sans titre'),
                'url': url,
                'url_part': result.get('url_part', ''),
                'année': result.get('year', 'N/A'),
                'date': result.get('date', 'Date inconnue'),
                'extrait': result.get('extract', 'Pas d\'extrait'),
                'type': doc_type,
                'législature': result.get('year', '')  # Approximation
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
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            analyze_btn = st.button("🔍 Analyser résultats", type="primary", use_container_width=True)
        with col2:
            export_btn = st.button("📥 Exporter données", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Source:** Résultats Google
        **Période:** 1966-1986
        **Documents:** 10 résultats trouvés
        """)
    
    # Analyse des résultats
    if analyze_btn or 'results' not in st.session_state:
        with st.spinner("Analyse des résultats Google..."):
            results = parse_google_results()
            st.session_state.results = results
    
    # Affichage des résultats
    if 'results' in st.session_state:
        results = st.session_state.results
        
        st.success(f"✅ {len(results)} documents trouvés dans les résultats Google")
        
        # Statistiques
        st.subheader("📈 Statistiques")
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("Documents", len(results))
        with col_stat2:
            years = len(set(r['année'] for r in results if r['année'] != 'N/A'))
            st.metric("Années", years)
        with col_stat3:
            types = len(set(r['type'] for r in results))
            st.metric("Types", types)
        with col_stat4:
            mentions = sum(1 for r in results if 'extrait' in r and r['extrait'])
            st.metric("Mentions", mentions)
        
        # Tableau des résultats
        st.subheader("📋 Documents trouvés")
        
        # Filtrer par année si demandé
        filtered_results = results
        if 'show_all' in locals() and not show_all:
            filtered_results = [r for r in results 
                              if r['année'] != 'N/A' 
                              and min_year <= r['année'] <= max_year]
        
        # Afficher chaque document
        for doc in filtered_results:
            with st.expander(f"📄 {doc['titre'][:80]}... ({doc['année']})"):
                col_doc1, col_doc2 = st.columns([3, 1])
                
                with col_doc1:
                    st.markdown(f"**Type:** {doc['type']}")
                    st.markdown(f"**Année:** {doc['année']}")
                    st.markdown(f"**Date:** {doc['date']}")
                    st.markdown(f"**URL Google:** `{doc['url_part']}`")
                    
                    # Contexte extrait
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
                    st.code(f"https://archives.assemblee-nationale.fr/cri/{doc['url_part']}")
                
                with col_doc2:
                    # Tentative d'accès
                    st.markdown("**Accès:**")
                    
                    # Bouton pour essayer l'URL
                    if st.button("🔗 Tester l'URL", key=f"test_{doc['id']}"):
                        import requests
                        try:
                            response = requests.get(doc['url'], timeout=10)
                            if response.status_code == 200:
                                st.success(f"✅ Accessible ({response.status_code})")
                                
                                # Vérifier si c'est un PDF
                                if 'pdf' in response.headers.get('content-type', '').lower():
                                    st.info("📄 Fichier PDF détecté")
                                    
                                    # Option de téléchargement
                                    st.download_button(
                                        label="📥 Télécharger",
                                        data=response.content,
                                        file_name=f"{doc['url_part']}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_{doc['id']}"
                                    )
                                else:
                                    st.warning("⚠️ Pas un PDF")
                            else:
                                st.error(f"❌ Erreur {response.status_code}")
                        except Exception as e:
                            st.error(f"❌ Erreur: {str(e)[:50]}")
        
        # Analyse par année
        st.subheader("📅 Répartition par année")
        
        # Grouper par année
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
            
            # Graphique simple
            st.bar_chart(df_years.set_index('Année'))
        
        # Table des URLs
        st.subheader("🔗 URLs trouvées")
        
        urls_table = pd.DataFrame([{
            'ID': doc['id'],
            'Année': doc['année'],
            'URL Partielle': doc['url_part'],
            'Type': doc['type']
        } for doc in results])
        
        st.dataframe(urls_table, use_container_width=True)
        
        # Export des données
        if export_btn:
            st.subheader("💾 Export des données")
            
            # Données complètes
            df_complet = pd.DataFrame(results)
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                # CSV
                csv_data = df_complet.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📊 CSV complet",
                    data=csv_data,
                    file_name=f"bumidom_google_results_{datetime.now().strftime('%Y%m%d')}.csv",
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
                RAPPORT D'ANALYSE BUMIDOM - RÉSULTATS GOOGLE
                ============================================
                
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
                   Type: {doc['type']}
                   URL: https://archives.assemblee-nationale.fr/cri/{doc['url_part']}
                   Extrait: {doc['extrait'][:150]}...
                   
                """
                
                st.download_button(
                    label="📝 Rapport texte",
                    data=rapport,
                    file_name=f"rapport_bumidom_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🎯 Analyse des Résultats Google BUMIDOM
        
        ### Problème identifié:
        Les URLs trouvées dans Google retournent **404** quand on essaie d'y accéder directement.
        
        ### Solution:
        Analyser les **extraits de texte** que Google a déjà indexés, qui contiennent les informations précieuses.
        
        ### 📊 Informations disponibles dans vos résultats:
        
        1. **Titres des documents**
        2. **URLs structurelles** (pattern)
        3. **Dates de publication**
        4. **Extraits de texte** contenant "BUMIDOM"
        5. **Types de documents** (CRI, Journal Officiel, etc.)
        
        ### 🚀 Ce que fait cette analyse:
        
        - **Extrait automatiquement** les informations de vos résultats Google
        - **Analyse le contexte** autour de "BUMIDOM"
        - **Organise par année** et type de document
        - **Génère un rapport** détaillé
        - **Permet de tester** les URLs une par une
        
        ### 📋 Exemple d'extrait analysé:
        
        ```
        "le BUMIDOM qui, en 1965, a facilité l'installation en métropole."
        ```
        
        Cette phrase vient du document **1966-1967-ordinaire1** et contient déjà une information historique précieuse.
        
        ### ⏱️ Cliquez sur "🔍 Analyser résultats" pour commencer
        """)

if __name__ == "__main__":
    main()
