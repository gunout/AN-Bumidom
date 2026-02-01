import streamlit as st
import requests
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import time
import re  # Importé au début

# ==================== CONFIGURATION ====================
st.set_page_config(page_title="Dashboard API Google CSE", layout="wide")
st.title("🔍 Dashboard API - Archives Assemblée Nationale")
st.markdown("**Analyse des données JSON d'API Google CSE**")

# ==================== FONCTIONS PRINCIPALES ====================

def parser_json_google_cse(json_data, page_num=1):
    """Parse les données JSON de l'API Google CSE"""
    resultats = []
    
    try:
        # Vérifier si c'est une fonction wrapper comme dans le fichier
        if isinstance(json_data, dict) and len(json_data) == 1:
            # Extraire les données de la fonction wrapper
            func_name = list(json_data.keys())[0]
            data = json_data[func_name]
        else:
            data = json_data
        
        # Extraire les résultats
        if 'results' in data:
            items = data['results']
        else:
            # Essayer de trouver les résultats
            items = []
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict):
                        items = value
                        break
        
        st.info(f"📊 {len(items)} éléments trouvés dans le JSON")
        
        for i, item in enumerate(items):
            try:
                # Extraire les informations selon la structure Google CSE
                titre = item.get('title', item.get('titleNoFormatting', f'Document {i+1}'))
                url = item.get('url', item.get('unescapedUrl', item.get('link', '')))
                description = item.get('contentNoFormatting', 
                                     item.get('content', 
                                     item.get('snippet', '')))
                
                # Nettoyer les entités HTML
                description = description.replace('\\u003cb\\u003e', '').replace('\\u003c/b\\u003e', '')
                description = description.replace('&#39;', "'").replace('&nbsp;', ' ')
                
                # Extraire la date depuis le contenu
                date_match = re.search(r'(\d{1,2}\s+[a-zéû]+\s+\d{4}|\d{4})', description)
                date_doc = date_match.group(1) if date_match else "Date inconnue"
                
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
                leg_match_url = re.search(r'/(\d+)/cri/', url)
                leg_match_title = re.search(r'(\d+)[\'°]?\s+Législature', titre)
                
                if leg_match_url:
                    legislature = leg_match_url.group(1)
                elif leg_match_title:
                    legislature = leg_match_title.group(1)
                
                # Extraire les années
                annee_match = re.search(r'/(\d{4})-(\d{4})', url)
                if annee_match:
                    periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                else:
                    # Chercher d'autres patterns de dates
                    annee_match = re.search(r'(\d{4})\s*-\s*(\d{4})', description)
                    if annee_match:
                        periode = f"{annee_match.group(1)}-{annee_match.group(2)}"
                    else:
                        annee_match = re.search(r'(\d{4})', date_doc)
                        if annee_match:
                            annee = annee_match.group(1)
                            periode = f"{annee}"
                        else:
                            periode = "Inconnue"
                
                # Score de pertinence basé sur la position
                score = 100 - (i * 5) if i < 20 else 10
                
                # Métadonnées enrichies
                metadonnees = {}
                if 'richSnippet' in item:
                    metadonnees = item['richSnippet']
                if 'breadcrumbUrl' in item:
                    metadonnees['breadcrumbs'] = item['breadcrumbUrl'].get('crumbs', [])
                
                resultats.append({
                    'id': f"P{page_num:02d}R{i+1:02d}",
                    'titre': titre[:150] + "..." if len(titre) > 150 else titre,
                    'url': url,
                    'description': description[:200] + "..." if len(description) > 200 else description,
                    'type': type_doc,
                    'legislature': legislature,
                    'periode': periode,
                    'date_doc': date_doc,
                    'page': page_num,
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
        
        return resultats
        
    except Exception as e:
        st.error(f"Erreur lors du parsing JSON: {str(e)}")
        return []

def charger_json_du_fichier():
    """Charge les données JSON depuis le fichier fourni"""
    try:
        # Le contenu JSON complet avec TOUS les résultats
        json_content = """/*O_o*/
google.search.cse.api12938({
  "cursor": {
    "currentPageIndex": 0,
    "estimatedResultCount": "131",
    "moreResultsUrl": "http://www.google.com/cse?oe=utf8&ie=utf8&source=uds&q=bumidom&safe=off&cx=014917347718038151697:kltwr00yvbk&start=0",
    "resultCount": "131",
    "searchResultTime": "0.30",
    "pages": [
      {
        "label": 1,
        "start": "0"
      },
      {
        "label": 2,
        "start": "10"
      },
      {
        "label": 3,
        "start": "20"
      },
      {
        "label": 4,
        "start": "30"
      },
      {
        "label": 5,
        "start": "40"
      },
      {
        "label": 6,
        "start": "50"
      },
      {
        "label": 7,
        "start": "60"
      },
      {
        "label": 8,
        "start": "70"
      },
      {
        "label": 9,
        "start": "80"
      },
      {
        "label": 10,
        "start": "90"
      }
    ]
  },
  "results": [
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAgQAg&usg=AOvVaw3XQEsRa-ZOw0c9nxuM7XyR",
      "content": "26 oct. 1971 \\u003cb\\u003e...\\u003c/b\\u003e \\u003cb\\u003eBumidom\\u003c/b\\u003e. Nous avons donc fait un effort très sérieux — je crois qu&#39;il commence à porter ses fruits — pour l&#39;information, comme on l&#39;a&nbsp;...",
      "contentNoFormatting": "26 oct. 1971 ... Bumidom. Nous avons donc fait un effort très sérieux — je crois qu'il commence à porter ses fruits — pour l'information, comme on l'a ...",
      "title": "JOURNAL OFFICIAL - Assemblée nationale - Archives",
      "titleNoFormatting": "JOURNAL OFFICIAL - Assemblée nationale - Archives",
      "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1971-1972.../024.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/024.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///52e124d09f6f568d014713da119fb74cb967399904f1817a551cdf0c91483d3d"
        },
        "metatags": {
          "moddate": "D:20080702154326+02'00'",
          "creationdate": "D:20080702154326+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSfqjYzwWbrBntmlpFWjaoFvYi7LrDVp5DG2RSIoqxZBRmF5KtvGm3yArc&s",
          "width": "197",
          "height": "256"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1971-1972-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1968-1969-ordinaire1/050.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAUQAg&usg=AOvVaw1o2mlaBef0JNNpzSDXWzFK",
      "content": "9 nov. 2025 \\u003cb\\u003e...\\u003c/b\\u003e \\u003cb\\u003eBumidom\\u003c/b\\u003e. Dès mon arrivée au ministère, je me suis essentielle- ment préoccupé des conditions d&#39;accueil et d&#39;adaptation des originaires des&nbsp;...",
      "contentNoFormatting": "9 nov. 2025 ... Bumidom. Dès mon arrivée au ministère, je me suis essentielle- ment préoccupé des conditions d'accueil et d'adaptation des originaires des ...",
      "title": "CONSTITUTION DU 4 OCTOBRE 1958 4&#39; Législature",
      "titleNoFormatting": "CONSTITUTION DU 4 OCTOBRE 1958 4' Législature",
      "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1968-1969.../050.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/4/cri/1968-1969-ordinaire1/050.pdf",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1968-1969-ordinaire1/050.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///752fecc791f1729dc9409a855a24d88e6413891450ce1f0678731331e2dace19"
        },
        "metatags": {
          "moddate": "D:20080530113314+02'00'",
          "creationdate": "D:20080702130544+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSvexHT635XmLa4ZTWgJb-uw2hVAhACoBcrv1WhQ1s8g1UJRe6kRUBoPZbS&s",
          "width": "196",
          "height": "257"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1968-1969-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAYQAQ&usg=AOvVaw0kEy49-XtbL0tnPLfpTQKs",
      "content": "le \\u003cb\\u003eBUMIDOM\\u003c/b\\u003e qui, en 1965, a facilité l&#39;installation en métropole. La réalisation effective de la parité globale se poursuivra de 7.000 personnes. en. 1967 . C&nbsp;...",
      "contentNoFormatting": "le BUMIDOM qui, en 1965, a facilité l'installation en métropole. La réalisation effective de la parité globale se poursuivra de 7.000 personnes. en. 1967 . C ...",
      "title": "Assemblée nationale - Archives",
      "titleNoFormatting": "Assemblée nationale - Archives",
      "formattedUrl": "https://archives.assemblee-nationale.fr/2/cri/1966-1967.../021.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf",
      "url": "https://archives.assemblee-nationale.fr/2/cri/1966-1967-ordinaire1/021.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///a6954a3a039389e9725536001dc617c95efa746637849cb9ae72dbc2582d2cf1"
        },
        "metatags": {
          "moddate": "D:20081007122856+02'00'",
          "creationdate": "D:20081007122856+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSzhZ860WuX_OP04UMEaqnz9fDcfWADKICU-6DpVXa5BMAGDFlvau12Hto&s",
          "width": "197",
          "height": "255"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1966-1967-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/7/cri/1982-1983-ordinaire1/057.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAsQAg&usg=AOvVaw04USMOeX35eApIZjnsjlUo",
      "content": "5 nov. 1982 \\u003cb\\u003e...\\u003c/b\\u003e Le \\u003cb\\u003eBumidom\\u003c/b\\u003e, tant décrié par vos amis, a été, dans la pratique, remplacé par un succédané — l&#39;agence nationale pour l&#39;insertion et la&nbsp;...",
      "contentNoFormatting": "5 nov. 1982 ... Le Bumidom, tant décrié par vos amis, a été, dans la pratique, remplacé par un succédané — l'agence nationale pour l'insertion et la ...",
      "title": "CONSTITUTION DU 4 OCTOBRE 1958 7&#39; Législature",
      "titleNoFormatting": "CONSTITUTION DU 4 OCTOBRE 1958 7' Législature",
      "formattedUrl": "https://archives.assemblee-nationale.fr/7/cri/1982-1983.../057.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/7/cri/1982-1983-ordinaire1/057.pdf",
      "url": "https://archives.assemblee-nationale.fr/7/cri/1982-1983-ordinaire1/057.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///f68d02ab6d230d9a716d0ec83b31bc72a11e78904d87601ed61022b0c7ba49c4"
        },
        "metatags": {
          "moddate": "D:20080908133720+02'00'",
          "creationdate": "D:20080908133720+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS_SBAnIolX39uVp8XCrXyahf1jJpydQFYPkXgPdjayt50yOCTjHc-_Ra2i&s",
          "width": "197",
          "height": "255"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1982-1983-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/057.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAMQAg&usg=AOvVaw2jle1EbjAQkSzu2F-Wew8T",
      "content": "27 janv. 2025 \\u003cb\\u003e...\\u003c/b\\u003e des crédits affectés au \\u003cb\\u003eBumidom\\u003c/b\\u003e pour les années 1976 et 1977;. 2° les raisons de la réduction des crédits pour l&#39;année 1977 si tou- tefois&nbsp;...",
      "contentNoFormatting": "27 janv. 2025 ... des crédits affectés au Bumidom pour les années 1976 et 1977;. 2° les raisons de la réduction des crédits pour l'année 1977 si tou- tefois ...",
      "title": "COMPTE RENDU INTEGRAL - Assemblée nationale - Archives",
      "titleNoFormatting": "COMPTE RENDU INTEGRAL - Assemblée nationale - Archives",
      "formattedUrl": "https://archives.assemblee-nationale.fr/5/cri/1976-1977.../057.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/057.pdf",
      "url": "https://archives.assemblee-nationale.fr/5/cri/1976-1977-ordinaire2/057.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///d4c2f88830f6a13cce37932dd76cf9d73dff2072222a241408a90602e2c59372"
        },
        "metatags": {
          "moddate": "D:20081008173646+02'00'",
          "creationdate": "D:20081008173646+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjrspNtzgOCRC_H5Sx2C-EJUHqc78jaYB3AkwKIJKesA9AGzjaRoLsaZo&s",
          "width": "197",
          "height": "256"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1976-1977-ordinaire2"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/060.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAcQAg&usg=AOvVaw2Q2De_fn4jbWIJ0SYAJsRl",
      "content": "16 nov. 1970 \\u003cb\\u003e...\\u003c/b\\u003e des départements d&#39;outre-mer — \\u003cb\\u003eBumidom\\u003c/b\\u003e — dont l&#39;objectif est à la fois de faciliter l&#39;immigration et d&#39;orienter les tra- vailleurs vers un&nbsp;...",
      "contentNoFormatting": "16 nov. 1970 ... des départements d'outre-mer — Bumidom — dont l'objectif est à la fois de faciliter l'immigration et d'orienter les tra- vailleurs vers un ...",
      "title": "CONSTITUTION DU 4 OCTOBRE 1958 4° Législature",
      "titleNoFormatting": "CONSTITUTION DU 4 OCTOBRE 1958 4° Législature",
      "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1970-1971.../060.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/060.pdf",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/060.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///86d42a16cfb943cafaa3071d16023ed82c3ab6e007090dc1f7236789df3b533c"
        },
        "metatags": {
          "moddate": "D:20080922163741+02'00'",
          "creationdate": "D:20080922163741+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTpG3XI7phJhTAB0EfNLoT8EgPCsqJuDINA-MZXMD15tP2PSu5Zm9ThMdY&s",
          "width": "197",
          "height": "255"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1970-1971-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/067.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAoQAg&usg=AOvVaw1TiSVlBpTiOQirHZDFP_tL",
      "content": "5 nov. 2025 \\u003cb\\u003e...\\u003c/b\\u003e société d &#39;Etat « \\u003cb\\u003eBumidom\\u003c/b\\u003e », qui prend à sa charge les frais du voyage. En conséquence, il lui demande quelles mesures il compte prendre&nbsp;...",
      "contentNoFormatting": "5 nov. 2025 ... société d 'Etat « Bumidom », qui prend à sa charge les frais du voyage. En conséquence, il lui demande quelles mesures il compte prendre ...",
      "title": "JOUR AL OFFICIEL - Assemblée nationale - Archives",
      "titleNoFormatting": "JOUR AL OFFICIEL - Assemblée nationale - Archives",
      "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1971-1972.../067.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/067.pdf",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1971-1972-ordinaire1/067.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///70e7a3bdb000e88e94c33fb263e53ad5052bf03895e46225930685aecef05226"
        },
        "metatags": {
          "moddate": "D:20080922172837+02'00'",
          "creationdate": "D:20080922172837+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSEE5FRlHI5IHKZ89hypG4Zxh6yfnLshpyyrCwAfgldIGtu6navA5XptEny&s",
          "width": "197",
          "height": "256"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1971-1972-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/023.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAQQAg&usg=AOvVaw0ECR2XP0VoZVS_Z-aq_LrA",
      "content": "26 oct. 1970 \\u003cb\\u003e...\\u003c/b\\u003e Le \\u003cb\\u003eBumidom\\u003c/b\\u003e ne devrait pas être traité comme un instrument de la ... tés d&#39;accueil et du \\u003cb\\u003eBumidom\\u003c/b\\u003e, c&#39;est-à-dire du bureau des migrations.",
      "contentNoFormatting": "26 oct. 1970 ... Le Bumidom ne devrait pas être traité comme un instrument de la ... tés d'accueil et du Bumidom, c'est-à-dire du bureau des migrations.",
      "title": "CONSTITUTION DU 4 OCTOBRE 1958 4° Législature",
      "titleNoFormatting": "CONSTITUTION DU 4 OCTOBRE 1958 4° Législature",
      "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1970-1971.../023.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/023.pdf",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire1/023.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///cecd5845b3e8f1281f51bb5cc224fdb412e38b5fe63c8ad9a63f3f780e1a212b"
        },
        "metatags": {
          "moddate": "D:20080922163015+02'00'",
          "creationdate": "D:20080922163015+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSOPhy57tqbSr4pABIMreKdHmttqsMZaAwZhNTD8chEBwIyeqEMrXM9q58&s",
          "width": "197",
          "height": "256"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1970-1971-ordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/8/cri/1985-1986-extraordinaire1/015.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAkQAg&usg=AOvVaw07d_SBR4NkuRf5WSuqkmP2",
      "content": "11 juil. 1986 \\u003cb\\u003e...\\u003c/b\\u003e \\u003cb\\u003eBumidom\\u003c/b\\u003e . On crée l &#39; A.N.T., Agence nationale pour l &#39; inser- tion et la promotion des travailleurs. Le slogan gouverne- mental était&nbsp;...",
      "contentNoFormatting": "11 juil. 1986 ... Bumidom . On crée l ' A.N.T., Agence nationale pour l ' inser- tion et la promotion des travailleurs. Le slogan gouverne- mental était ...",
      "title": "DE LA RÉPUBLIQUE FRANÇAISE - Assemblée nationale - Archives",
      "titleNoFormatting": "DE LA RÉPUBLIQUE FRANÇAISE - Assemblée nationale - Archives",
      "formattedUrl": "https://archives.assemblee-nationale.fr/8/cri/1985-1986.../015.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/8/cri/1985-1986-extraordinaire1/015.pdf",
      "url": "https://archives.assemblee-nationale.fr/8/cri/1985-1986-extraordinaire1/015.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///7acec6247ba9c241d0d2deef854d5a24128fa6f0c0fd0029c19ffc543d408a83"
        },
        "metatags": {
          "moddate": "D:20080929180819+02'00'",
          "creationdate": "D:20080929180819+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSu4-cNrjaboldBpn5ctU7ecWtpA-n4EJT5pT8wJ9C26eCtWWAZ2QUiILUS&s",
          "width": "187",
          "height": "269"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1985-1986-extraordinaire1"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    },
    {
      "clicktrackUrl": "https://www.google.com/url?client=internal-element-cse&cx=014917347718038151697:kltwr00yvbk&q=https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire2/007.pdf&sa=U&ved=2ahUKEwjS4N_VnrmSAxUESPEDHXjqFW4QFnoECAIQAg&usg=AOvVaw3owLd8J1Cyt0hy5hFXzdAo",
      "content": "7 mars 2025 \\u003cb\\u003e...\\u003c/b\\u003e nisée par le \\u003cb\\u003eBumidom\\u003c/b\\u003e, est loin d&#39;être satisfaisante. Ses effets sont du reste annihilés par l&#39;entrée d&#39;une main-d&#39;oeuvre impor- tante dans&nbsp;...",
      "contentNoFormatting": "7 mars 2025 ... nisée par le Bumidom, est loin d'être satisfaisante. Ses effets sont du reste annihilés par l'entrée d'une main-d'oeuvre impor- tante dans ...",
      "title": "JOUR: AL OFFICIEL - Assemblée nationale - Archives",
      "titleNoFormatting": "JOUR:\\\\ AL OFFICIEL - Assemblée nationale - Archives",
      "formattedUrl": "https://archives.assemblee-nationale.fr/4/cri/1970-1971.../007.pdf",
      "unescapedUrl": "https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire2/007.pdf",
      "url": "https://archives.assemblee-nationale.fr/4/cri/1970-1971-ordinaire2/007.pdf",
      "visibleUrl": "archives.assemblee-nationale.fr",
      "richSnippet": {
        "cseImage": {
          "src": "x-raw-image:///c5373003a1afe32ce78be5b9d67312eb891ec86605c0667ab9f50910aa0c3fc6"
        },
        "metatags": {
          "moddate": "D:20080922165234+02'00'",
          "creationdate": "D:20080922165234+02'00'",
          "producer": "Recoded by LuraDocument PDF v2.15"
        },
        "cseThumbnail": {
          "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSCgf7b3a4TW3H9HEFwU0UENNSGVcmf87KPBOW2eKg3NKupeweN3VLMCkio&s",
          "width": "197",
          "height": "255"
        }
      },
      "breadcrumbUrl": {
        "host": "archives.assemblee-nationale.fr",
        "crumbs": [
          "cri",
          "1970-1971-ordinaire2"
        ]
      },
      "fileFormat": "PDF/Adobe Acrobat"
    }
  ],
  "findMoreOnGoogle": {
    "url": "https://www.google.com/search?client=ms-google-coop&q=bumidom&cx=014917347718038151697:kltwr00yvbk"
  }
});"""
        
        # Nettoyer et parser le JSON
        # Enlever le commentaire et la fonction wrapper
        json_str = json_content.strip()
        if json_str.startswith('/*'):
            # Enlever le commentaire
            json_str = json_str.split('*/', 1)[1].strip()
        
        # Parser comme JSON
        data = json.loads(json_str[json_str.find('{'):json_str.rfind('}')+1])
        
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
    
    # Options
    st.subheader("Options d'analyse")
    
    # Bouton pour charger le JSON
    if st.button("📁 Analyser le JSON", type="primary", use_container_width=True):
        with st.spinner("Chargement et analyse du JSON..."):
            json_data = charger_json_du_fichier()
            
            if json_data:
                st.session_state.donnees_json = json_data
                
                # Parser les résultats
                resultats = parser_json_google_cse(json_data, 1)
                st.session_state.resultats_parses = resultats
                
                st.success(f"✅ JSON analysé: {len(resultats)} résultats trouvés!")
            else:
                st.error("❌ Impossible de charger le JSON")
    
    # Afficher les statistiques si des données existent
    if st.session_state.resultats_parses:
        st.divider()
        st.subheader("📊 Statistiques")
        total = len(st.session_state.resultats_parses)
        
        # Compter les types
        types_counts = {}
        for r in st.session_state.resultats_parses:
            types_counts[r['type']] = types_counts.get(r['type'], 0) + 1
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total)
        with col2:
            st.metric("Types", len(types_counts))
        
        # Liste des types
        st.write("**Types trouvés:**")
        for type_name, count in types_counts.items():
            st.write(f"- {type_name}: {count}")

# Contenu principal
if st.session_state.resultats_parses:
    donnees = st.session_state.resultats_parses
    df = pd.DataFrame(donnees)
    
    # ==================== VUE D'ENSEMBLE ====================
    st.header("📈 Vue d'ensemble des données JSON")
    
    # Statistiques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents", len(df))
    with col2:
        pdf_count = df[df['type'] == 'PDF'].shape[0]
        st.metric("PDF", pdf_count)
    with col3:
        cr_count = df[df['type'] == 'Compte rendu'].shape[0]
        st.metric("Comptes rendus", cr_count)
    with col4:
        jo_count = df[df['type'] == 'Journal Officiel'].shape[0]
        st.metric("Journaux Officiels", jo_count)
    
    # ==================== TABLEAU DES RÉSULTATS ====================
    st.header("📄 Résultats extraits du JSON")
    
    # Filtres
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            types = sorted(df['type'].unique())
            types_selection = st.multiselect("Types", types, default=types)
        
        with col2:
            legislatures = sorted([l for l in df['legislature'].unique() if l])
            leg_selection = st.multiselect("Législatures", legislatures, default=legislatures)
    
    # Appliquer les filtres
    df_filtre = df[
        (df['type'].isin(types_selection)) &
        (df['legislature'].isin(leg_selection) | (df['legislature'] == ''))
    ]
    
    # Afficher le tableau
    st.dataframe(
        df_filtre[['id', 'titre', 'type', 'legislature', 'periode', 'date_doc', 'score']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "titre": st.column_config.TextColumn("Titre", width="large"),
            "type": st.column_config.TextColumn("Type"),
            "legislature": st.column_config.TextColumn("Législature"),
            "periode": st.column_config.TextColumn("Période"),
            "date_doc": st.column_config.TextColumn("Date"),
            "score": st.column_config.NumberColumn("Score", format="%d")
        }
    )
    
    # ==================== VISUALISATIONS ====================
    st.header("📊 Analyses visuelles")
    
    tab1, tab2, tab3 = st.tabs(["📅 Chronologie", "📊 Distribution", "🌐 Sources"])
    
    with tab1:
        # Graphique par période
        if 'periode' in df_filtre.columns and not df_filtre.empty:
            period_counts = df_filtre['periode'].value_counts().head(10)
            if len(period_counts) > 0:
                fig = px.bar(
                    x=period_counts.index,
                    y=period_counts.values,
                    title="Documents par période (top 10)",
                    labels={'x': 'Période', 'y': 'Nombre'},
                    color=period_counts.values,
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution par type
            type_counts = df_filtre['type'].value_counts()
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Distribution par type de document",
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution par législature
            if df_filtre['legislature'].notna().any():
                leg_counts = df_filtre[df_filtre['legislature'] != '']['legislature'].value_counts()
                if len(leg_counts) > 0:
                    fig = px.bar(
                        x=leg_counts.index.astype(str),
                        y=leg_counts.values,
                        title="Documents par législature",
                        labels={'x': 'Législature', 'y': 'Nombre'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Analyse des domaines
        if 'visible_url' in df_filtre.columns:
            domain_counts = df_filtre['visible_url'].value_counts().head(10)
            if len(domain_counts) > 0:
                fig = px.bar(
                    x=domain_counts.index,
                    y=domain_counts.values,
                    title="Top 10 des domaines sources",
                    labels={'x': 'Domaine', 'y': 'Nombre'},
                    color=domain_counts.values,
                    color_continuous_scale='Blues'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # ==================== DÉTAILS DES DOCUMENTS ====================
    st.header("🔍 Détails par document")
    
    if not df_filtre.empty:
        # Sélection d'un document
        doc_id = st.selectbox(
            "Choisir un document",
            df_filtre['id'].tolist(),
            format_func=lambda x: f"{x} - {df_filtre[df_filtre['id'] == x]['titre'].iloc[0][:50]}..."
        )
        
        if doc_id:
            doc = df_filtre[df_filtre['id'] == doc_id].iloc[0]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {doc['titre']}")
                
                # Métadonnées
                st.markdown("**📋 Informations:**")
                
                meta_cols = st.columns(3)
                with meta_cols[0]:
                    st.metric("Type", doc['type'])
                with meta_cols[1]:
                    st.metric("Législature", doc['legislature'] or "N/A")
                with meta_cols[2]:
                    st.metric("Période", doc['periode'])
                
                # Description
                if doc['description']:
                    st.markdown("**📝 Extrait:**")
                    st.info(doc['description'])
                
                # URL
                if doc['url']:
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
                st.metric("Score", doc['score'])
                
                # Métadonnées brutes
                if doc['metadonnees'] and doc['metadonnees'] != '{}':
                    with st.expander("Métadonnées techniques"):
                        try:
                            meta = json.loads(doc['metadonnees'])
                            st.json(meta)
                        except:
                            st.text(doc['metadonnees'])
    
    # ==================== EXPORT ====================
    st.header("💾 Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 CSV complet",
            data=csv,
            file_name=f"google_cse_analyse_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON
        json_data = json.dumps(donnees, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON structuré",
            data=json_data,
            file_name=f"google_cse_analyse_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Export URLs seulement
        urls = [d['url'] for d in donnees if d['url']]
        urls_text = "\n".join(urls)
        st.download_button(
            label="📄 Liste des URLs",
            data=urls_text.encode('utf-8'),
            file_name=f"urls_google_cse_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    # ==================== DONNÉES BRUTES ====================
    with st.expander("📊 Données brutes du JSON", expanded=False):
        if st.session_state.donnees_json:
            st.json(st.session_state.donnees_json)

else:
    # ==================== ÉCRAN D'ACCUEIL ====================
    st.header("🔍 Analyseur de données JSON Google CSE")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 À propos
        Ce dashboard analyse les **données JSON** provenant de l'API 
        **Google Custom Search Engine** utilisée par les archives 
        de l'Assemblée Nationale.
        
        ### ✅ Fonctionnalités
        - **Analyse automatique** du format JSON Google CSE
        - **Extraction intelligente** des métadonnées
        - **Détection automatique** des types de documents
        - **Visualisations interactives**
        - **Export multi-formats**
        
        ### 📋 Format supporté
        Format JSON Google CSE avec structure:
        ```json
        {
          "results": [...],
          "cursor": {...}
        }
        ```
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Comment l'utiliser
        1. **Cliquez** sur "Analyser le JSON" dans la sidebar
        2. **Explorez** les résultats via les tableaux
        3. **Analysez** avec les visualisations
        4. **Consultez** les détails par document
        5. **Exportez** les données
        
        ### 🔍 Champs extraits
        - Titre et description
        - URL et domaine visible
        - Type de document (PDF, CR, JO...)
        - Législature et période
        - Date d'origine
        - Score de pertinence
        - Métadonnées techniques
        """)
    
    # Exemple de structure
    with st.expander("📄 Exemple de structure JSON", expanded=False):
        st.code("""
{
  "cursor": {
    "currentPageIndex": 0,
    "estimatedResultCount": "131",
    "pages": [...]
  },
  "results": [
    {
      "title": "Titre du document",
      "titleNoFormatting": "Titre sans formatage",
      "url": "https://exemple.com/document.pdf",
      "content": "Extrait avec <b>balises</b>...",
      "contentNoFormatting": "Extrait sans formatage...",
      "visibleUrl": "domaine.com",
      "fileFormat": "PDF/Adobe Acrobat",
      "richSnippet": {...}
    }
  ]
}
        """, language="json")

# ==================== PIED DE PAGE ====================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard d'analyse JSON Google CSE • Format: Google Custom Search API • 
    <span id='date'></span>
    <script>
        document.getElementById('date').innerHTML = new Date().toLocaleDateString('fr-FR');
    </script>
    </div>
    """,
    unsafe_allow_html=True
)
