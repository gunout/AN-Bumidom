# bumidom_dashboard.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from io import BytesIO
import fitz  # PyMuPDF
import time
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
import hashlib
import pickle
import os
import urllib.parse
from datetime import datetime
import json

# ==================== CONFIGURATION INITIALE ====================

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Analyse BUMIDOM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Télécharger les ressources NLTK
try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

# Titre de l'application
st.title("📊 Dashboard d'Analyse BUMIDOM - Archives Assemblée Nationale")
st.markdown("""
Analyse des documents parlementaires relatifs au **BUMIDOM** (Bureau pour le développement 
des migrations dans les départements d'outre-mer, 1963-1982).
""")

# ==================== CLASSES ET FONCTIONS UTILITAIRES ====================

class DocumentCache:
    """Cache pour stocker les PDFs téléchargés"""
    
    def __init__(self, cache_dir="pdf_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, url):
        """Génère une clé unique pour une URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get_cached_text(self, url):
        """Récupère le texte depuis le cache"""
        cache_key = self.get_cache_key(url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    return data.get('text', ''), data.get('pages', 0)
            except:
                return None, 0
        return None, 0
    
    def cache_text(self, url, text, pages):
        """Stocke le texte dans le cache"""
        cache_key = self.get_cache_key(url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({'text': text, 'pages': pages, 'url': url, 'timestamp': time.time()}, f)
        except Exception as e:
            st.warning(f"Erreur cache: {str(e)}")

# Initialisation du cache
document_cache = DocumentCache()

# ==================== FONCTIONS DE SCRAPING RÉEL ====================

def search_bumidom_documents_real():
    """
    Scrape réel du site des archives pour trouver les documents BUMIDOM
    """
    base_url = "https://archives.assemblee-nationale.fr"
    search_url = f"{base_url}/r/1/search?q=BUMIDOM"
    
    documents = []
    
    try:
        st.info("🔍 Scraping du site des archives en cours...")
        
        # Headers pour simuler un navigateur
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Requête HTTP
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parser le HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Plusieurs stratégies pour trouver les documents
        found_documents = []
        
        # Stratégie 1: Chercher tous les liens PDF
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        
        # Stratégie 2: Chercher les résultats de recherche
        search_results = soup.find_all(['div', 'li'], class_=re.compile(r'(result|item|document)', re.I))
        
        # Stratégie 3: Chercher par texte
        bumidom_elements = soup.find_all(text=re.compile(r'bumidom', re.I))
        
        st.info(f"PDF trouvés: {len(pdf_links)}, Résultats: {len(search_results)}, Éléments BUMIDOM: {len(bumidom_elements)}")
        
        # Combiner toutes les sources
        all_elements = []
        
        # Ajouter les liens PDF directs
        for link in pdf_links[:50]:  # Limiter pour les tests
            title = link.get_text(strip=True) or link.get('href', 'Document PDF')
            url = link.get('href', '')
            
            if not url.startswith('http'):
                url = urllib.parse.urljoin(base_url, url)
            
            all_elements.append({
                'title': title,
                'url': url,
                'element': link
            })
        
        # Traiter les résultats de recherche
        for result in search_results[:30]:
            # Essayer d'extraire un titre
            title_elem = result.find(['h3', 'h4', 'a', 'strong'])
            title = title_elem.get_text(strip=True) if title_elem else "Document sans titre"
            
            # Chercher un lien PDF dans ce résultat
            pdf_link = result.find('a', href=re.compile(r'\.pdf$', re.I))
            if pdf_link:
                url = pdf_link.get('href', '')
                if not url.startswith('http'):
                    url = urllib.parse.urljoin(base_url, url)
                
                all_elements.append({
                    'title': title,
                    'url': url,
                    'element': result
                })
        
        # Filtrer et organiser les documents
        seen_urls = set()
        for elem in all_elements:
            url = elem['url']
            
            # Éviter les doublons
            if url in seen_urls or not url:
                continue
            
            seen_urls.add(url)
            
            # Extraire la date si possible
            date_match = re.search(r'(19\d{2}|20\d{2})', elem['title'])
            date = date_match.group(1) if date_match else "ND"
            
            # Déterminer le type de document
            doc_type = "Document"
            title_lower = elem['title'].lower()
            
            type_patterns = [
                ('rapport', 'Rapport'),
                ('compte rendu', 'Compte rendu'),
                ('audition', 'Audition'),
                ('débat', 'Débats'),
                ('budget', 'Budget'),
                ('question', 'Question'),
                ('loi', 'Loi'),
                ('délibération', 'Délibération'),
                ('arrêté', 'Arrêté')
            ]
            
            for pattern, doc_type_name in type_patterns:
                if pattern in title_lower:
                    doc_type = doc_type_name
                    break
            
            documents.append({
                'title': elem['title'][:200],  # Limiter la longueur
                'url': url,
                'date': date,
                'type': doc_type,
                'pages': 0,  # Sera mis à jour lors de l'extraction
                'source': 'Archives AN'
            })
        
        # Si peu de documents trouvés, en ajouter des simulés pour la démo
        if len(documents) < 5:
            st.warning("Peu de documents trouvés. Ajout de documents de démonstration...")
            documents.extend(get_sample_documents()[:10])
        
        st.success(f"✅ {len(documents)} documents trouvés pour analyse")
        return documents[:100]  # Limiter à 100 documents max
        
    except Exception as e:
        st.error(f"❌ Erreur lors du scraping: {str(e)}")
        # Retourner des documents de démo en cas d'échec
        return get_sample_documents()[:20]

def get_sample_documents():
    """Documents de démonstration si le scraping échoue"""
    base_url = "https://archives.assemblee-nationale.fr"
    
    sample_docs = [
        {
            "title": "Rapport sur les activités du BUMIDOM 1963-1965",
            "url": f"{base_url}/documents/example1.pdf",
            "date": "1966",
            "type": "Rapport",
            "pages": 45,
            "source": "Démo"
        },
        {
            "title": "Audition du directeur du BUMIDOM - Commission des affaires culturelles",
            "url": f"{base_url}/documents/example2.pdf",
            "date": "1970",
            "type": "Compte rendu",
            "pages": 28,
            "source": "Démo"
        },
        {
            "title": "Bilan des migrations DOM-TOM organisées par le BUMIDOM 1963-1977",
            "url": f"{base_url}/documents/example3.pdf",
            "date": "1978",
            "type": "Bilan",
            "pages": 62,
            "source": "Démo"
        },
        {
            "title": "Questions au gouvernement concernant le BUMIDOM",
            "url": f"{base_url}/documents/example4.pdf",
            "date": "1975",
            "type": "Question écrite",
            "pages": 12,
            "source": "Démo"
        },
        {
            "title": "Débats parlementaires sur le financement du BUMIDOM",
            "url": f"{base_url}/documents/example5.pdf",
            "date": "1972",
            "type": "Débats",
            "pages": 35,
            "source": "Démo"
        },
        {
            "title": "Rapport d'enquête sur les conditions d'accueil des migrants du BUMIDOM",
            "url": f"{base_url}/documents/example6.pdf",
            "date": "1980",
            "type": "Rapport d'enquête",
            "pages": 78,
            "source": "Démo"
        },
        {
            "title": "Statistiques des migrations BUMIDOM 1963-1981",
            "url": f"{base_url}/documents/example7.pdf",
            "date": "1982",
            "type": "Statistiques",
            "pages": 54,
            "source": "Démo"
        },
        {
            "title": "Projet de loi de finances - Budget BUMIDOM 1974",
            "url": f"{base_url}/documents/example8.pdf",
            "date": "1974",
            "type": "Budget",
            "pages": 42,
            "source": "Démo"
        }
    ]
    
    # Ajouter plus de documents variés
    for i in range(9, 21):
        year = 1963 + (i * 2) % 20
        sample_docs.append({
            "title": f"Document BUMIDOM {i} - Analyse {year}",
            "url": f"{base_url}/documents/example{i}.pdf",
            "date": str(year),
            "type": ["Rapport", "Note", "Étude", "Communication"][i % 4],
            "pages": 20 + (i * 3) % 40,
            "source": "Démo"
        })
    
    return sample_docs

# ==================== FONCTIONS D'EXTRACTION PDF ====================

def extract_text_from_pdf_real(pdf_url, max_pages=50):
    """
    Extrait le texte d'un PDF réel depuis une URL
    """
    # Vérifier le cache d'abord
    cached_text, cached_pages = document_cache.get_cached_text(pdf_url)
    if cached_text is not None:
        return cached_text, cached_pages
    
    try:
        # Headers pour la requête
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf, */*',
            'Referer': 'https://archives.assemblee-nationale.fr/'
        }
        
        # Télécharger le PDF
        response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        # Vérifier le type de contenu
        content_type = response.headers.get('content-type', '')
        is_pdf = 'pdf' in content_type.lower() or response.content[:4] == b'%PDF'
        
        if not is_pdf:
            # Essayer de lire quand même
            st.warning(f"Type de contenu suspect pour {pdf_url}: {content_type}")
        
        # Ouvrir le PDF avec PyMuPDF
        pdf_document = fitz.open(stream=response.content, filetype="pdf")
        
        # Extraire le texte page par page
        text = ""
        total_pages = pdf_document.page_count
        
        # Limiter le nombre de pages pour les gros documents
        pages_to_extract = min(max_pages, total_pages)
        
        for page_num in range(pages_to_extract):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text("text")
            
            if page_text:
                # Nettoyer le texte
                page_text = re.sub(r'\s+', ' ', page_text)
                page_text = re.sub(r'\n\s*\n', '\n\n', page_text)
                text += f"--- Page {page_num + 1} ---\n{page_text}\n\n"
        
        pdf_document.close()
        
        # Mettre en cache
        document_cache.cache_text(pdf_url, text, total_pages)
        
        return text, total_pages
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Erreur réseau: {str(e)}"
        st.warning(f"❌ {error_msg} pour {pdf_url}")
        return error_msg, 0
    except fitz.FileDataError as e:
        error_msg = f"Fichier PDF invalide: {str(e)}"
        return error_msg, 0
    except Exception as e:
        error_msg = f"Erreur d'extraction: {str(e)}"
        return error_msg, 0

# ==================== FONCTIONS D'ANALYSE ====================

def analyze_document_text(text):
    """Analyse le texte d'un document"""
    if not isinstance(text, str) or len(text.strip()) < 10:
        return {
            'word_count': 0,
            'keyword_counts': {},
            'top_words': [],
            'themes': {},
            'is_valid': False
        }
    
    try:
        # Compter les mots
        words = text.split()
        word_count = len(words)
        
        # Mots-clés spécifiques BUMIDOM
        keywords = [
            "BUMIDOM", "bumidom", "migration", "migrant", "migrants",
            "outre-mer", "DOM", "TOM", "département", "départements",
            "Guadeloupe", "Martinique", "Réunion", "Guyane", "Mayotte",
            "emploi", "travail", "chômage", "intégration", "accueil",
            "organisé", "développement", "bureau", "politique", "métropole",
            "transport", "logement", "santé", "éducation", "formation",
            "famille", "jeunes", "contrat", "statistique", "bilan"
        ]
        
        # Compter les occurrences
        keyword_counts = {}
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Utiliser regex pour des mots complets
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            count = len(re.findall(pattern, text_lower))
            if count > 0:
                keyword_counts[keyword] = count
        
        # Mots les plus fréquents (hors mots vides)
        try:
            stop_words = set(stopwords.words('french'))
            # Ajouter des mots vides courants
            stop_words.update(['plus', 'tout', 'tous', 'toutes', 'comme', 'faire', 'très'])
            
            tokens = word_tokenize(text_lower)
            filtered_tokens = [
                word for word in tokens 
                if word.isalnum() 
                and word not in stop_words 
                and len(word) > 2
                and not any(char.isdigit() for char in word)
            ]
            
            word_freq = Counter(filtered_tokens)
            top_words = word_freq.most_common(10)
        except:
            top_words = []
        
        # Identifier les thèmes
        themes = {
            "Migration": ["migration", "migrant", "départ", "arrivée", "déplacement", "voyage"],
            "Territoires": ["guadeloupe", "martinique", "réunion", "guyane", "mayotte", "dom", "tom"],
            "Emploi": ["emploi", "travail", "chômage", "qualification", "formation", "métier"],
            "Politique": ["politique", "gouvernement", "ministère", "budget", "loi", "décision"],
            "Social": ["intégration", "accueil", "logement", "famille", "santé", "éducation"],
            "Administratif": ["bureau", "administration", "service", "direction", "organisation"]
        }
        
        theme_counts = {}
        for theme, theme_keywords in themes.items():
            total = 0
            for keyword in theme_keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                total += len(re.findall(pattern, text_lower))
            if total > 0:
                theme_counts[theme] = total
        
        return {
            'word_count': word_count,
            'keyword_counts': keyword_counts,
            'top_words': top_words,
            'themes': theme_counts,
            'is_valid': True
        }
        
    except Exception as e:
        st.warning(f"Erreur analyse texte: {str(e)}")
        return {
            'word_count': 0,
            'keyword_counts': {},
            'top_words': [],
            'themes': {},
            'is_valid': False
        }

def analyze_all_documents(documents):
    """Analyse tous les documents"""
    st.info(f"🔬 Analyse de {len(documents)} documents en cours...")
    
    all_analyses = []
    all_stats = []
    all_text = ""
    corpus_word_freq = Counter()
    theme_frequencies = Counter()
    
    # Barre de progression
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialiser les compteurs de thèmes
    theme_categories = ["Migration", "Territoires", "Emploi", "Politique", "Social", "Administratif"]
    for theme in theme_categories:
        theme_frequencies[theme] = 0
    
    for idx, doc in enumerate(documents):
        # Mise à jour de la progression
        progress = (idx + 1) / len(documents)
        progress_bar.progress(progress)
        status_text.text(f"📄 Document {idx+1}/{len(documents)}: {doc['title'][:50]}...")
        
        # Extraire le texte
        text, pages = extract_text_from_pdf_real(doc['url'])
        
        # Mettre à jour le nombre de pages
        doc['pages'] = pages
        
        # Analyser le texte
        analysis = analyze_document_text(text)
        
        # Préparer l'analyse du document
        doc_analysis = {
            'title': doc['title'],
            'date': doc['date'],
            'type': doc['type'],
            'pages': pages,
            'url': doc['url'],
            'source': doc.get('source', 'Archive'),
            'word_count': analysis['word_count'],
            'keyword_counts': analysis['keyword_counts'],
            'top_words': analysis['top_words'],
            'themes': analysis['themes'],
            'is_valid': analysis['is_valid'],
            'text_preview': text[:500] + "..." if isinstance(text, str) and len(text) > 500 else text
        }
        
        all_analyses.append(doc_analysis)
        
        # Ajouter aux statistiques
        all_stats.append({
            'Titre': doc['title'][:80],
            'Année': doc['date'],
            'Type': doc['type'],
            'Pages': pages,
            'Mots': analysis['word_count'],
            'Fréq. BUMIDOM': analysis['keyword_counts'].get('BUMIDOM', 0),
            'Migrants': analysis['keyword_counts'].get('migrant', 0) + analysis['keyword_counts'].get('migrants', 0),
            'Valide': "✅" if analysis['is_valid'] else "❌"
        })
        
        # Ajouter au corpus global
        if isinstance(text, str) and analysis['is_valid']:
            all_text += text + " "
            
            # Ajouter aux fréquences de mots du corpus
            try:
                stop_words = set(stopwords.words('french'))
                tokens = word_tokenize(text.lower())
                filtered_tokens = [
                    word for word in tokens 
                    if word.isalnum() 
                    and word not in stop_words 
                    and len(word) > 3
                ]
                corpus_word_freq.update(filtered_tokens)
            except:
                pass
            
            # Ajouter aux thèmes
            for theme, count in analysis['themes'].items():
                theme_frequencies[theme] += count
        
        # Petite pause pour ne pas surcharger
        time.sleep(0.05)
    
    # Analyser le corpus complet
    corpus_analysis = {}
    if all_text:
        # Thèmes principaux dans tout le corpus
        corpus_analysis['theme_frequencies'] = dict(theme_frequencies)
        
        # Mots les plus fréquents
        corpus_analysis['top_corpus_words'] = corpus_word_freq.most_common(20)
        
        # Statistiques générales
        total_words = len(all_text.split())
        valid_docs = sum(1 for a in all_analyses if a['is_valid'])
        
        corpus_analysis['total_words'] = total_words
        corpus_analysis['valid_documents'] = valid_docs
        corpus_analysis['total_documents'] = len(documents)
    
    progress_bar.empty()
    status_text.empty()
    
    return {
        'document_analyses': all_analyses,
        'document_stats': all_stats,
        'corpus_analysis': corpus_analysis,
        'all_text': all_text
    }

# ==================== FONCTIONS DE VISUALISATION ====================

def create_visualizations(data):
    """Crée les visualisations pour le dashboard"""
    
    # Extraire les données
    stats_df = pd.DataFrame(data['document_stats'])
    corpus_analysis = data['corpus_analysis']
    
    visualizations = {}
    
    # 1. Graphique des documents par année
    if not stats_df.empty and 'Année' in stats_df.columns:
        try:
            # Nettoyer les années
            stats_df['Année_clean'] = stats_df['Année'].apply(
                lambda x: int(x) if str(x).isdigit() and 1900 <= int(x) <= 2024 else None
            )
            stats_df = stats_df.dropna(subset=['Année_clean'])
            
            year_counts = stats_df['Année_clean'].value_counts().sort_index()
            
            fig_years = px.bar(
                x=year_counts.index.astype(str),
                y=year_counts.values,
                title="📅 Documents par année",
                labels={'x': 'Année', 'y': 'Nombre de documents'},
                color=year_counts.values,
                color_continuous_scale='Blues'
            )
            fig_years.update_layout(xaxis_tickangle=-45)
            visualizations['years_chart'] = fig_years
        except:
            pass
    
    # 2. Graphique par type de document
    if not stats_df.empty and 'Type' in stats_df.columns:
        type_counts = stats_df['Type'].value_counts()
        fig_types = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="📋 Répartition par type de document",
            hole=0.3
        )
        fig_types.update_traces(textposition='inside', textinfo='percent+label')
        visualizations['types_chart'] = fig_types
    
    # 3. Graphique des thèmes principaux
    if 'theme_frequencies' in corpus_analysis:
        theme_data = corpus_analysis['theme_frequencies']
        if theme_data:
            themes_df = pd.DataFrame({
                'Thème': list(theme_data.keys()),
                'Fréquence': list(theme_data.values())
            }).sort_values('Fréquence', ascending=False)
            
            fig_themes = px.bar(
                themes_df,
                x='Thème',
                y='Fréquence',
                title="🏷️ Thèmes principaux du corpus",
                color='Fréquence',
                color_continuous_scale='Viridis'
            )
            visualizations['themes_chart'] = fig_themes
    
    # 4. Mots les plus fréquents
    if 'top_corpus_words' in corpus_analysis:
        top_words = corpus_analysis['top_corpus_words'][:15]
        if top_words:
            words, counts = zip(*top_words)
            fig_words = px.bar(
                x=list(words),
                y=list(counts),
                title="🔤 Mots les plus fréquents (hors mots vides)",
                labels={'x': 'Mot', 'y': 'Fréquence'},
                color=list(counts),
                color_continuous_scale='thermal'
            )
            fig_words.update_layout(xaxis_tickangle=-45)
            visualizations['words_chart'] = fig_words
    
    # 5. Nuage de mots (simplifié)
    if 'top_corpus_words' in corpus_analysis:
        top_words = corpus_analysis['top_corpus_words'][:30]
        if top_words:
            words, counts = zip(*top_words)
            sizes = [c * 2 for c in counts]  # Ajuster la taille
            
            fig_cloud = go.Figure()
            
            # Positionner les mots aléatoirement
            import random
            for word, size in zip(words, sizes):
                fig_cloud.add_trace(go.Scatter(
                    x=[random.random()],
                    y=[random.random()],
                    mode='text',
                    text=[word],
                    textfont=dict(size=size, color=f'rgb({random.randint(50,200)},{random.randint(50,200)},{random.randint(50,200)})'),
                    showlegend=False
                ))
            
            fig_cloud.update_layout(
                title="☁️ Nuage de mots clés",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='white'
            )
            visualizations['wordcloud'] = fig_cloud
    
    return visualizations

# ==================== INTERFACE STREAMLIT ====================

# Initialisation de l'état de session
if 'documents_data' not in st.session_state:
    st.session_state.documents_data = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'visualizations' not in st.session_state:
    st.session_state.visualizations = None

# Sidebar
with st.sidebar:
    st.header("🔧 Contrôles")
    
    # Mode de fonctionnement
    mode = st.radio(
        "Mode d'opération",
        ["Scraping réel", "Données de démonstration", "Test unitaire"],
        help="Choisissez le mode de récupération des documents"
    )
    
    # Options de scraping
    st.subheader("Options de recherche")
    max_documents = st.slider("Nombre max de documents", 10, 100, 50)
    
    # Bouton d'action principal
    if st.button("🚀 Lancer la recherche et l'analyse", type="primary", use_container_width=True):
        with st.spinner("Scraping et analyse en cours..."):
            try:
                # Recherche des documents
                if mode == "Scraping réel":
                    documents = search_bumidom_documents_real()
                elif mode == "Test unitaire":
                    documents = get_sample_documents()[:5]
                else:  # Mode démo
                    documents = get_sample_documents()[:max_documents]
                
                if documents:
                    # Analyse des documents
                    analysis_results = analyze_all_documents(documents)
                    
                    # Créer les visualisations
                    visualizations = create_visualizations(analysis_results)
                    
                    # Stocker dans la session
                    st.session_state.documents_data = analysis_results
                    st.session_state.visualizations = visualizations
                    st.session_state.analysis_done = True
                    st.session_state.search_performed = True
                    
                    st.success(f"✅ Analyse terminée! {len(documents)} documents traités.")
                else:
                    st.error("❌ Aucun document trouvé.")
                    
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")
    
    st.divider()
    
    # Gestion du cache
    st.header("💾 Gestion des données")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Vider le cache", type="secondary"):
            if os.path.exists("pdf_cache"):
                import shutil
                shutil.rmtree("pdf_cache")
                st.success("Cache vidé!")
                st.rerun()
    
    with col2:
        if st.button("🔄 Rafraîchir", type="secondary"):
            st.rerun()
    
    # Informations
    if st.session_state.analysis_done:
        st.divider()
        st.header("📊 Statistiques")
        
        data = st.session_state.documents_data
        if data and 'corpus_analysis' in data:
            stats = data['corpus_analysis']
            
            st.metric("Documents totaux", stats.get('total_documents', 0))
            st.metric("Documents valides", stats.get('valid_documents', 0))
            st.metric("Mots analysés", f"{stats.get('total_words', 0):,}")
    
    st.divider()
    st.caption("Dashboard BUMIDOM v1.0 • Archives Assemblée Nationale")

# ==================== CONTENU PRINCIPAL ====================

if st.session_state.search_performed and st.session_state.analysis_done:
    data = st.session_state.documents_data
    visuals = st.session_state.visualizations
    
    # Métriques principales
    st.header("📈 Vue d'ensemble")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_docs = len(data['document_stats'])
        st.metric("Documents", total_docs)
    
    with col2:
        valid_docs = sum(1 for doc in data['document_stats'] if doc['Valide'] == '✅')
        st.metric("Documents valides", valid_docs)
    
    with col3:
        total_pages = sum(doc['Pages'] for doc in data['document_stats'])
        st.metric("Pages totales", total_pages)
    
    with col4:
        if data['corpus_analysis']:
            total_words = data['corpus_analysis'].get('total_words', 0)
            st.metric("Mots analysés", f"{total_words:,}")
    
    # Tableau des documents
    st.header("📄 Documents analysés")
    
    stats_df = pd.DataFrame(data['document_stats'])
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not stats_df.empty and 'Année' in stats_df.columns:
            years = sorted([y for y in stats_df['Année'].unique() if str(y).isdigit()])
            selected_years = st.multiselect("Filtrer par année", years, default=years)
            if selected_years:
                stats_df = stats_df[stats_df['Année'].isin(selected_years)]
    
    with col2:
        if not stats_df.empty and 'Type' in stats_df.columns:
            types = sorted(stats_df['Type'].unique())
            selected_types = st.multiselect("Filtrer par type", types, default=types)
            if selected_types:
                stats_df = stats_df[stats_df['Type'].isin(selected_types)]
    
    with col3:
        if not stats_df.empty and 'Valide' in stats_df.columns:
            validity_filter = st.multiselect("État", ['✅', '❌'], default=['✅', '❌'])
            if validity_filter:
                stats_df = stats_df[stats_df['Valide'].isin(validity_filter)]
    
    # Afficher le tableau
    st.dataframe(
        stats_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Titre": st.column_config.TextColumn(width="large"),
            "URL": st.column_config.LinkColumn(display_text="Lien")
        }
    )
    
    # Visualisations
    st.header("📊 Visualisations interactives")
    
    if visuals:
        # Onglets pour les graphiques
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Chronologie", "📋 Types", "🏷️ Thèmes", "🔤 Mots"])
        
        with tab1:
            if 'years_chart' in visuals:
                st.plotly_chart(visuals['years_chart'], use_container_width=True)
            else:
                st.info("Graphique chronologique non disponible")
        
        with tab2:
            if 'types_chart' in visuals:
                st.plotly_chart(visuals['types_chart'], use_container_width=True)
            else:
                st.info("Graphique des types non disponible")
        
        with tab3:
            if 'themes_chart' in visuals:
                st.plotly_chart(visuals['themes_chart'], use_container_width=True)
            else:
                st.info("Graphique des thèmes non disponible")
        
        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                if 'words_chart' in visuals:
                    st.plotly_chart(visuals['words_chart'], use_container_width=True)
            with col2:
                if 'wordcloud' in visuals:
                    st.plotly_chart(visuals['wordcloud'], use_container_width=True)
    
    # Analyse détaillée par document
    st.header("🔍 Analyse document par document")
    
    for i, doc_analysis in enumerate(data['document_analyses']):
        # Appliquer les filtres
        if not stats_df.empty:
            if doc_analysis['title'][:80] not in stats_df['Titre'].values:
                continue
        
        with st.expander(f"{doc_analysis['title']} ({doc_analysis['date']}) - {doc_analysis['type']}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Mots", doc_analysis['word_count'])
            
            with col2:
                st.metric("Pages", doc_analysis['pages'])
            
            with col3:
                bumidom_count = doc_analysis['keyword_counts'].get('BUMIDOM', 0)
                st.metric("BUMIDOM", bumidom_count)
            
            with col4:
                migrant_count = doc_analysis['keyword_counts'].get('migrant', 0) + doc_analysis['keyword_counts'].get('migrants', 0)
                st.metric("Migrants", migrant_count)
            
            # Aperçu du texte
            st.subheader("Extrait")
            st.text(doc_analysis['text_preview'])
            
            # Mots-clés
            st.subheader("Mots-clés principaux")
            if doc_analysis['keyword_counts']:
                keywords_df = pd.DataFrame(
                    list(doc_analysis['keyword_counts'].items()),
                    columns=['Mot-clé', 'Occurrences']
                ).sort_values('Occurrences', ascending=False)
                
                st.dataframe(keywords_df, use_container_width=True, hide_index=True)
            
            # Thèmes détectés
            st.subheader("Thèmes détectés")
            if doc_analysis['themes']:
                themes_df = pd.DataFrame(
                    list(doc_analysis['themes'].items()),
                    columns=['Thème', 'Occurrences']
                ).sort_values('Occurrences', ascending=False)
                
                st.dataframe(themes_df, use_container_width=True, hide_index=True)
    
    # Export des données
    st.header("💾 Export des résultats")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV
        csv_data = stats_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv_data,
            file_name="bumidom_analysis.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export JSON
        export_data = {
            'metadata': {
                'date_export': datetime.now().isoformat(),
                'total_documents': len(data['document_analyses']),
                'source': 'Archives Assemblée Nationale'
            },
            'documents': data['document_analyses']
        }
        
        json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Télécharger JSON",
            data=json_data,
            file_name="bumidom_analysis.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Rapport texte
        report_text = f"""RAPPORT D'ANALYSE BUMIDOM
{'='*50}

Date d'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Documents analysés: {len(data['document_analyses'])}
Documents valides: {valid_docs}
Pages totales: {total_pages}
Mots analysés: {total_words:,}

THÈMES PRINCIPAUX:
"""
        
        if data['corpus_analysis'].get('theme_frequencies'):
            for theme, freq in data['corpus_analysis']['theme_frequencies'].items():
                report_text += f"\n- {theme}: {freq} occurrences"
        
        report_text += "\n\nDOCUMENTS ANALYSÉS:\n"
        for doc in data['document_stats'][:20]:  # Limiter aux 20 premiers
            report_text += f"\n- {doc['Titre'][:60]}... ({doc['Année']}, {doc['Type']}, {doc['Pages']} pages)"
        
        if len(data['document_stats']) > 20:
            report_text += f"\n\n... et {len(data['document_stats']) - 20} autres documents"
        
        st.download_button(
            label="📄 Rapport texte",
            data=report_text.encode('utf-8'),
            file_name="rapport_bumidom.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # Écran d'accueil
    st.header("Bienvenue dans l'Analyseur BUMIDOM")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 À propos
        Cet outil analyse les documents parlementaires français concernant le **BUMIDOM**, organisme ayant géré les migrations des DOM-TOM vers la métropole entre 1963 et 1982.
        
        ### 🔍 Sources
        - Archives de l'Assemblée Nationale
        - Documents parlementaires
        - Rapports officiels
        - Comptes rendus de débats
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Comment utiliser
        1. **Configurez** le mode dans la sidebar
        2. **Lancez** la recherche et l'analyse
        3. **Explorez** les résultats via les visualisations
        4. **Exportez** les données pour vos recherches
        
        ### 📊 Fonctionnalités
        - Scraping automatique des archives
        - Extraction de texte depuis PDF
        - Analyse lexicale et thématique
        - Visualisations interactives
        - Export multi-formats
        """)
    
    st.divider()
    
    # Section technique
    with st.expander("🛠️ Configuration technique"):
        st.markdown("""
        **Dépendances Python:**
        ```bash
        pip install streamlit requests beautifulsoup4 pymupdf pandas plotly nltk
        ```
        
        **Fonctions principales:**
        1. `search_bumidom_documents_real()` - Scraping du site
        2. `extract_text_from_pdf_real()` - Extraction PDF
        3. `analyze_all_documents()` - Analyse textuelle
        4. `create_visualizations()` - Génération de graphiques
        
        **Structure des données:**
        - Cache PDF local pour éviter les re-téléchargements
        - Analyse NLTK pour le traitement du langage
        - Visualisations Plotly pour l'interactivité
        - Interface Streamlit responsive
        """)

# ==================== PIED DE PAGE ====================

st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    Dashboard d'analyse BUMIDOM • Archives de l'Assemblée Nationale • 
    <a href='https://archives.assemblée-nationale.fr' target='_blank'>Source des données</a> • 
    Outil de recherche historique
    </div>
    """,
    unsafe_allow_html=True
)
