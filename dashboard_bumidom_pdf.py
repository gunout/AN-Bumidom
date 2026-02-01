import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import time
import re

st.set_page_config(page_title="Chasseur de PDF BUMIDOM - AN", layout="wide")
st.title("🔍 Dashboard de Scraping des PDF BUMIDOM")
st.markdown("Scraping des archives de l'Assemblée nationale (4ème à dernière législature)")

# Configuration
BASE_URL = "https://www.assemblee-nationale.fr/histoire/tables_archives/index.asp"
TARGET_KEYWORD = "BUMIDOM"
legislatures_cibles = ["IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]

@st.cache_data
def scraper_principal(base_url, keyword, legislatures):
    """
    Fonction principale de scraping.
    """
    tous_pdfs = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    try:
        # 1. Récupérer la page d'index principale
        reponse_index = session.get(base_url)
        soup_index = BeautifulSoup(reponse_index.content, 'html.parser')

        # 2. Itérer sur chaque législature cible
        for leg in legislatures:
            with st.spinner(f"Recherche dans la {leg}e législature..."):
                # Construire un motif pour trouver les liens de cette législature
                # Cette sélection peut nécessiter des ajustements précis selon la structure HTML réelle
                liens_legislature = soup_index.find_all('a', string=re.compile(fr'.*{leg}.*législature.*', re.IGNORECASE))

                for lien in liens_legislature:
                    href_table = lien.get('href')
                    if not href_table:
                        continue

                    url_table_complete = urljoin(base_url, href_table)

                    # 3. Scraper la page de la table pour trouver les PDF
                    try:
                        reponse_table = session.get(url_table_complete)
                        soup_table = BeautifulSoup(reponse_table.content, 'html.parser')

                        # Trouver TOUS les liens PDF sur cette page
                        for lien_pdf in soup_table.find_all('a', href=re.compile(r'.*\.pdf$', re.IGNORECASE)):
                            url_pdf = lien_pdf.get('href')
                            texte_lien = lien_pdf.get_text(strip=True)

                            # 4. Filtrer sur le mot-clé BUMIDOM (dans l'URL ou le texte)
                            if (keyword.lower() in url_pdf.lower()) or (keyword.lower() in texte_lien.lower()):
                                url_pdf_complete = urljoin(url_table_complete, url_pdf)
                                tous_pdfs.append({
                                    "Législature": leg,
                                    "Source (Table)": url_table_complete,
                                    "Lien PDF": url_pdf_complete,
                                    "Texte du Lien": texte_lien
                                })
                    except Exception as e:
                        st.warning(f"Erreur sur la table {url_table_complete} : {e}")
                        continue

                    time.sleep(0.5) # Politesse envers le serveur

    except Exception as e:
        st.error(f"Une erreur majeure est survenue : {e}")
        return []

    return tous_pdfs

# --- Interface du Dashboard ---
st.sidebar.header("Paramètres")
if st.sidebar.button("🚀 Lancer le Scraping", type="primary"):
    with st.spinner("Scraping en cours... Cela peut prendre plusieurs minutes."):
        resultats = scraper_principal(BASE_URL, TARGET_KEYWORD, legislatures_cibles)

    st.success("Scraping terminé !")

    # Affichage des résultats
    if resultats:
        df = pd.DataFrame(resultats)
        st.subheader(f"✅ {len(df)} PDF(s) trouvé(s) contenant '{TARGET_KEYWORD}'")
        st.dataframe(df[["Législature", "Texte du Lien", "Lien PDF"]], use_container_width=True)

        # Option de téléchargement
        st.download_button(
            label="📥 Télécharger la liste en CSV",
            data=df.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"pdf_bumidom_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        # Affichage des liens cliquables
        st.subheader("Liens d'accès direct")
        for idx, row in df.iterrows():
            st.markdown(f"{idx+1}. [{row['Texte du Lien'] or 'Lien PDF'}]({row['Lien PDF']})")
    else:
        st.warning(f"Aucun PDF contenant le terme '{TARGET_KEYWORD}' n'a été trouvé dans les législatures sélectionnées.")

else:
    st.info("👈 Cliquez sur le bouton 'Lancer le Scraping' dans la barre latérale pour commencer.")
    st.markdown("""
    **Ce dashboard va :**
    1. Parcourir l'index des tables d'archives.
    2. Suivre les liens des législatures IV à XIII.
    3. Scanner chaque page de table pour trouver des liens PDF.
    4. Filtrer et lister ceux qui contiennent le mot **'BUMIDOM'**.
    """)
