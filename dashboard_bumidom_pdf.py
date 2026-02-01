import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from urllib.parse import urljoin, quote
import json
import base64
from datetime import datetime
import cloudscraper  # Pour contourner Cloudflare
import undetected_chromedriver as uc  # Alternative avec Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
from queue import Queue
import os

# Configuration
st.set_page_config(
    page_title="Scraper BUMIDOM - Contournement AN", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛡️ Scraper BUMIDOM - Contournement des protections AN")
st.markdown("Scraping avancé avec contournement des protections anti-bot")

class AdvancedBUMIDOMScraper:
    def __init__(self):
        self.base_url = "https://www.assemblee-nationale.fr"
        self.search_url = "https://www.assemblee-nationale.fr/recherche/"
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        self.session = None
        self.driver = None
    
    def create_stealth_session(self):
        """Crée une session furtive pour contourner les protections"""
        try:
            # Essayer cloudscraper d'abord (contourne Cloudflare)
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False,
                    'desktop': True,
                }
            )
            
            # Headers aléatoires
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'TE': 'trailers',
            }
            
            scraper.headers.update(headers)
            return scraper
            
        except Exception as e:
            st.warning(f"Cloudscraper échoué: {e}")
            # Fallback à requests normal
            session = requests.Session()
            session.headers.update({
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
            })
            return session
    
    def setup_selenium_driver(self):
        """Configure Selenium pour le scraping JavaScript"""
        try:
            options = uc.ChromeOptions()
            
            # Options de furtivité
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            
            # Exécuter en mode headless (sans interface)
            options.add_argument('--headless')
            
            # Désactiver les logs
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            driver = uc.Chrome(options=options)
            
            # Exécuter du JavaScript pour masquer WebDriver
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            return driver
            
        except Exception as e:
            st.error(f"Erreur Selenium: {e}")
            return None
    
    def search_with_selenium(self, keyword="BUMIDOM", max_pages=10):
        """Recherche avec Selenium (contourne JavaScript)"""
        
        if not self.driver:
            self.driver = self.setup_selenium_driver()
            if not self.driver:
                return []
        
        st.info(f"Recherche Selenium pour '{keyword}'...")
        
        all_pdf_links = []
        
        try:
            # Accéder à la page de recherche
            self.driver.get(self.search_url)
            time.sleep(3)  # Attendre le chargement
            
            # Remplir le formulaire de recherche
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "quoi"))
            )
            
            search_box.clear()
            search_box.send_keys(keyword)
            time.sleep(1)
            
            # Soumettre la recherche
            search_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or @type='button']")
            search_button.click()
            time.sleep(3)
            
            # Parcourir les pages
            for page_num in range(1, max_pages + 1):
                st.write(f"📄 Page {page_num} via Selenium...")
                
                # Extraire les liens de la page actuelle
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Chercher les liens PDF
                pdf_elements = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for element in pdf_elements:
                    href = element.get('href', '')
                    if href and 'assemblee-nationale.fr' in href:
                        full_url = href if href.startswith('http') else urljoin(self.base_url, href)
                        
                        title = element.get_text(strip=True)
                        if not title:
                            title = full_url.split('/')[-1]
                        
                        pdf_info = {
                            'url': full_url,
                            'title': title[:200],
                            'page': page_num,
                            'method': 'Selenium',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        if not any(p['url'] == full_url for p in all_pdf_links):
                            all_pdf_links.append(pdf_info)
                            st.write(f"  → {title[:80]}...")
                
                # Essayer d'aller à la page suivante
                if page_num < max_pages:
                    try:
                        next_buttons = self.driver.find_elements(
                            By.XPATH, 
                            "//a[contains(text(), 'suivant') or contains(text(), 'Suivant') or contains(text(), '>')]"
                        )
                        
                        if next_buttons:
                            next_buttons[0].click()
                            time.sleep(3)
                        else:
                            # Chercher la pagination
                            page_links = self.driver.find_elements(
                                By.XPATH, f"//a[contains(text(), '{page_num + 1}')]"
                            )
                            if page_links:
                                page_links[0].click()
                                time.sleep(3)
                            else:
                                st.info("Dernière page atteinte")
                                break
                                
                    except Exception as e:
                        st.warning(f"Impossible d'aller à la page {page_num + 1}: {e}")
                        break
            
            return all_pdf_links[:100]
            
        except Exception as e:
            st.error(f"Erreur Selenium: {str(e)[:200]}")
            return []
    
    def search_with_google_dork(self, keyword="BUMIDOM", max_results=100):
        """Utilise Google Dorking pour trouver des PDF"""
        
        st.info(f"Recherche Google Dork pour '{keyword}'...")
        
        all_pdf_links = []
        
        # Construction de la requête Google Dork
        dork_query = f'site:assemblee-nationale.fr filetype:pdf "{keyword}"'
        google_url = f"https://www.google.com/search?q={quote(dork_query)}&num=100"
        
        try:
            # Créer une session furtive
            session = self.create_stealth_session()
            
            response = session.get(google_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Chercher les résultats Google
                results = soup.find_all('div', class_=re.compile(r'^g\b'))
                
                for result in results:
                    link = result.find('a', href=True)
                    if link:
                        href = link['href']
                        
                        # Nettoyer l'URL Google
                        if '/url?q=' in href:
                            match = re.search(r'/url\?q=([^&]+)', href)
                            if match:
                                href = requests.utils.unquote(match.group(1))
                        
                        # Vérifier si c'est un PDF de l'AN
                        if ('.pdf' in href.lower() and 
                            'assemblee-nationale.fr' in href and
                            keyword.lower() in href.lower()):
                            
                            title_elem = result.find('h3')
                            title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
                            
                            pdf_info = {
                                'url': href,
                                'title': title[:200],
                                'page': 1,
                                'method': 'Google Dork',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if not any(p['url'] == href for p in all_pdf_links):
                                all_pdf_links.append(pdf_info)
                                st.write(f"  → Google Dork: {title[:80]}...")
                
                # Si on a besoin de plus de résultats, on peut simuler le scroll
                if len(all_pdf_links) < max_results:
                    st.info("Tentative de récupération de plus de résultats...")
                    
                    # Ajouter des paramètres pour plus de résultats
                    for start in [100, 200, 300]:
                        more_url = f"https://www.google.com/search?q={quote(dork_query)}&num=100&start={start}"
                        try:
                            response = session.get(more_url, timeout=15)
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            more_results = soup.find_all('div', class_=re.compile(r'^g\b'))
                            for result in more_results:
                                link = result.find('a', href=True)
                                if link:
                                    href = link['href']
                                    if '/url?q=' in href:
                                        match = re.search(r'/url\?q=([^&]+)', href)
                                        if match:
                                            href = requests.utils.unquote(match.group(1))
                                    
                                    if ('.pdf' in href.lower() and 
                                        'assemblee-nationale.fr' in href):
                                        
                                        title_elem = result.find('h3')
                                        title = title_elem.get_text(strip=True) if title_elem else ''
                                        
                                        pdf_info = {
                                            'url': href,
                                            'title': title[:200],
                                            'page': start // 100 + 1,
                                            'method': 'Google Dork',
                                            'timestamp': datetime.now().isoformat()
                                        }
                                        
                                        if not any(p['url'] == href for p in all_pdf_links):
                                            all_pdf_links.append(pdf_info)
                            
                            time.sleep(2)
                            
                        except:
                            break
                
                return all_pdf_links[:max_results]
                
            else:
                st.warning(f"Google a bloqué la requête: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            st.error(f"Erreur Google Dork: {str(e)[:200]}")
            return []
    
    def search_with_proxies(self, keyword="BUMIDOM"):
        """Essaie avec différents proxies pour contourner le blocage"""
        
        st.info("Tentative avec rotation de proxies...")
        
        # Liste de proxies publics (à utiliser avec précaution)
        proxies_list = [
            None,  # Pas de proxy
            {'http': 'http://proxy:8080', 'https': 'https://proxy:8080'},
        ]
        
        all_pdf_links = []
        
        for proxy in proxies_list:
            try:
                st.write(f"Essai avec proxy: {proxy}")
                
                session = requests.Session()
                session.headers.update({
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                })
                
                # Construire l'URL de recherche
                search_params = {
                    'quoi': keyword,
                    'type': 'pdf',
                    'legislature': 'toutes',
                    'sort': 'date',
                }
                
                response = session.get(
                    self.search_url, 
                    params=search_params,
                    proxies=proxy,
                    timeout=15
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extraire les résultats
                    results = soup.find_all(['a', 'div'], class_=re.compile(r'result|doc|pdf', re.I))
                    
                    for result in results:
                        link = result.find('a', href=re.compile(r'\.pdf$', re.I))
                        if link:
                            href = link.get('href', '')
                            if href:
                                full_url = urljoin(self.base_url, href)
                                
                                title = link.get_text(strip=True)
                                if not title:
                                    title = result.get_text(strip=True)[:200]
                                
                                pdf_info = {
                                    'url': full_url,
                                    'title': title[:200],
                                    'page': 1,
                                    'method': f'Proxy {proxy}' if proxy else 'Direct',
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                if not any(p['url'] == full_url for p in all_pdf_links):
                                    all_pdf_links.append(pdf_info)
                                    st.write(f"  → Proxy: {title[:80]}...")
                    
                    if all_pdf_links:
                        break
                        
                time.sleep(2)
                
            except Exception as e:
                st.warning(f"Proxy échoué: {str(e)[:100]}")
                continue
        
        return all_pdf_links
    
    def search_alternative_sites(self, keyword="BUMIDOM"):
        """Cherche sur des sites alternatifs qui référencent les PDF"""
        
        st.info("Recherche sur sites alternatifs...")
        
        all_pdf_links = []
        
        # Sites qui pourraient référencer les PDF
        alternative_sites = [
            f"https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&version=1.2&query=(gallica%20all%20%22{quote(keyword)}%22)%20and%20(gallica%20all%20%22assemblee%20nationale%22)",
            f"https://www.senat.fr/recherche/index.html?q={quote(keyword)}&type=pdf",
            f"https://www.vie-publique.fr/recherche?search_api_fulltext={quote(keyword)}&type%5B0%5D=pdf",
        ]
        
        for site_url in alternative_sites:
            try:
                st.write(f"Recherche sur: {site_url[:80]}...")
                
                session = self.create_stealth_session()
                response = session.get(site_url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Chercher les liens PDF
                    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    
                    for link in pdf_links:
                        href = link.get('href', '')
                        if href and 'assemblee-nationale.fr' in href:
                            full_url = href if href.startswith('http') else urljoin(site_url, href)
                            
                            title = link.get_text(strip=True)
                            if not title:
                                title = href.split('/')[-1]
                            
                            pdf_info = {
                                'url': full_url,
                                'title': title[:200],
                                'page': 1,
                                'method': 'Site alternatif',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if not any(p['url'] == full_url for p in all_pdf_links):
                                all_pdf_links.append(pdf_info)
                                st.write(f"  → Alternatif: {title[:80]}...")
                
                time.sleep(1)
                
            except Exception as e:
                st.warning(f"Site alternatif échoué: {str(e)[:100]}")
                continue
        
        return all_pdf_links
    
    def multi_method_search(self, keyword="BUMIDOM", max_results=100):
        """Combine toutes les méthodes de recherche"""
        
        st.info(f"Lancement de la recherche multi-méthodes pour '{keyword}'...")
        
        all_pdf_links = []
        methods = [
            ("Google Dork", self.search_with_google_dork),
            ("Selenium", self.search_with_selenium),
            ("Sites alternatifs", self.search_alternative_sites),
            ("Proxies", self.search_with_proxies),
        ]
        
        progress_bar = st.progress(0)
        
        for idx, (method_name, method_func) in enumerate(methods):
            progress = (idx + 1) / len(methods)
            progress_bar.progress(progress)
            
            st.write(f"🔍 Méthode: {method_name}...")
            
            try:
                results = method_func(keyword)
                
                # Fusionner les résultats
                for pdf in results:
                    if not any(p['url'] == pdf['url'] for p in all_pdf_links):
                        all_pdf_links.append(pdf)
                
                st.success(f"  → {len(results)} PDF trouvés avec {method_name}")
                time.sleep(1)
                
            except Exception as e:
                st.warning(f"  → {method_name} échoué: {str(e)[:100]}")
        
        progress_bar.empty()
        
        # Limiter aux meilleurs résultats
        return all_pdf_links[:max_results]
    
    def analyze_pdf_content(self, pdf_info, keyword="BUMIDOM"):
        """Analyse le contenu d'un PDF"""
        try:
            # Utiliser une session furtive
            session = self.create_stealth_session()
            
            st.write(f"📥 Téléchargement: {pdf_info['title'][:50]}...")
            
            response = session.get(pdf_info['url'], timeout=30, stream=True)
            
            if response.status_code != 200:
                return {
                    **pdf_info,
                    'error': f"HTTP {response.status_code}",
                    'keyword_count': 0,
                    'analyzed': False
                }
            
            content = response.content
            
            # Vérifier si c'est un PDF
            if not content.startswith(b'%PDF'):
                return {
                    **pdf_info,
                    'error': "Fichier non PDF",
                    'keyword_count': 0,
                    'analyzed': False
                }
            
            # Analyser avec PyMuPDF
            try:
                import fitz
                
                with fitz.open(stream=content, filetype="pdf") as pdf_doc:
                    page_count = pdf_doc.page_count
                    
                    # Extraire le texte (limité)
                    full_text = ""
                    for page_num in range(min(20, page_count)):
                        page = pdf_doc[page_num]
                        full_text += page.get_text() + "\n"
                    
                    # Rechercher le mot-clé
                    keyword_count = full_text.lower().count(keyword.lower())
                    
                    # Extraire le contexte
                    contexts = []
                    if keyword_count > 0:
                        text_lower = full_text.lower()
                        pos = text_lower.find(keyword.lower())
                        if pos != -1:
                            start = max(0, pos - 150)
                            end = min(len(full_text), pos + len(keyword) + 150)
                            contexts.append(full_text[start:end].replace('\n', ' ').strip())
                    
                    return {
                        **pdf_info,
                        'keyword_count': keyword_count,
                        'page_count': page_count,
                        'size_kb': len(content) / 1024,
                        'contexts': contexts[:2],
                        'analyzed': True,
                        'error': None
                    }
                    
            except ImportError:
                # Fallback: recherche simple dans les bytes
                keyword_count = content.lower().count(keyword.lower().encode())
                return {
                    **pdf_info,
                    'keyword_count': keyword_count,
                    'analyzed': True,
                    'error': 'PyMuPDF non disponible'
                }
                
        except Exception as e:
            return {
                **pdf_info,
                'error': f"Analyse: {str(e)[:100]}",
                'keyword_count': 0,
                'analyzed': False
            }

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Méthodes de contournement")
        
        keyword = st.text_input("Mot-clé:", value="BUMIDOM")
        
        search_method = st.selectbox(
            "Méthode de recherche:",
            [
                "Multi-méthodes (recommandé)",
                "Google Dorking", 
                "Selenium (JavaScript)",
                "Sites alternatifs",
                "Test rapide"
            ]
        )
        
        max_results = st.slider("Résultats max:", 10, 200, 50)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            search_btn = st.button("🔍 Rechercher PDF", use_container_width=True)
        
        with col_btn2:
            analyze_btn = st.button("🔬 Analyser PDF", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.info("""
        **Méthodes disponibles:**
        1. **Multi-méthodes** : Combine toutes les techniques
        2. **Google Dork** : Recherche Google avancée
        3. **Selenium** : Contourne JavaScript
        4. **Alternatifs** : Cherche ailleurs
        """)
    
    # Initialisation
    scraper = AdvancedBUMIDOMScraper()
    
    # État de session
    if 'pdf_links' not in st.session_state:
        st.session_state.pdf_links = []
    if 'pdf_data' not in st.session_state:
        st.session_state.pdf_data = []
    
    # Actions
    if search_btn:
        with st.spinner("Recherche en cours (peut prendre 1-2 minutes)..."):
            if search_method == "Multi-méthodes (recommandé)":
                pdf_links = scraper.multi_method_search(keyword, max_results)
            elif search_method == "Google Dorking":
                pdf_links = scraper.search_with_google_dork(keyword, max_results)
            elif search_method == "Selenium (JavaScript)":
                pdf_links = scraper.search_with_selenium(keyword, 5)
            elif search_method == "Sites alternatifs":
                pdf_links = scraper.search_alternative_sites(keyword)
            else:
                pdf_links = scraper.search_with_proxies(keyword)
            
            st.session_state.pdf_links = pdf_links
            
            if pdf_links:
                st.success(f"✅ {len(pdf_links)} PDF trouvés")
                
                # Afficher les résultats
                df = pd.DataFrame(pdf_links)
                
                # Statistiques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("PDF trouvés", len(df))
                with col2:
                    methods = df['method'].nunique()
                    st.metric("Méthodes", methods)
                with col3:
                    unique_urls = df['url'].nunique()
                    st.metric("URLs uniques", unique_urls)
                
                # Table des résultats
                st.subheader("📋 PDF trouvés")
                st.dataframe(df[['title', 'method', 'url']], use_container_width=True)
                
                # Export
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Télécharger la liste",
                    data=csv,
                    file_name=f"bumidom_urls_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.warning("❌ Aucun PDF trouvé")
                
                with st.expander("🔧 Dépannage"):
                    st.markdown("""
                    **Si aucune méthode ne fonctionne:**
                    
                    1. **Testez manuellement:**
                       - Allez sur https://www.assemblee-nationale.fr/recherche/
                       - Cherchez "BUMIDOM"
                       - Capturez l'URL de la page de résultats
                    
                    2. **Utilisez Google directement:**
                       ```
                       site:assemblee-nationale.fr filetype:pdf BUMIDOM
                       ```
                    
                    3. **Explorez les archives:**
                       - https://archives.assemblee-nationale.fr
                       - https://gallica.bnf.fr (Journal Officiel)
                    """)
    
    elif analyze_btn:
        if not st.session_state.pdf_links:
            st.warning("Veuillez d'abord rechercher des PDF")
        else:
            with st.spinner(f"Analyse de {len(st.session_state.pdf_links[:max_results])} PDF..."):
                results = []
                
                for pdf_info in st.session_state.pdf_links[:max_results]:
                    result = scraper.analyze_pdf_content(pdf_info, keyword)
                    results.append(result)
                
                st.session_state.pdf_data = results
                
                # Filtrer les PDF avec occurrences
                pdfs_with_keyword = [p for p in results if p.get('keyword_count', 0) > 0]
                analyzed_pdfs = [p for p in results if p.get('analyzed', False)]
                
                if analyzed_pdfs:
                    st.success(f"""
                    ✅ Analyse terminée:
                    - {len(analyzed_pdfs)} PDF analysés
                    - {len(pdfs_with_keyword)} contiennent '{keyword}'
                    """)
                    
                    if pdfs_with_keyword:
                        # Afficher les résultats
                        df_results = pd.DataFrame(pdfs_with_keyword)
                        
                        st.subheader(f"📊 {len(pdfs_with_keyword)} PDF avec occurrences")
                        
                        for pdf in pdfs_with_keyword:
                            with st.expander(f"📄 {pdf['title'][:80]}... ({pdf['keyword_count']} occ.)"):
                                col_a, col_b = st.columns([3, 1])
                                
                                with col_a:
                                    st.markdown(f"**URL:** `{pdf['url']}`")
                                    st.markdown(f"**Méthode:** {pdf.get('method', 'N/A')}")
                                    st.markdown(f"**Pages:** {pdf.get('page_count', 'N/A')}")
                                    
                                    if pdf.get('contexts'):
                                        st.markdown("**Contexte:**")
                                        for ctx in pdf['contexts']:
                                            highlighted = re.sub(
                                                r'(' + re.escape(keyword) + ')',
                                                r'**\1**',
                                                ctx,
                                                flags=re.IGNORECASE
                                            )
                                            st.markdown(f"> {highlighted}")
                                
                                with col_b:
                                    st.markdown(f"[🌐 Ouvrir]({pdf['url']})", unsafe_allow_html=True)
                        
                        # Export
                        st.subheader("💾 Export des analyses")
                        csv_data = pd.DataFrame(pdfs_with_keyword).to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Télécharger analyses",
                            data=csv_data,
                            file_name=f"bumidom_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv"
                        )
                    
                else:
                    st.warning("Aucun PDF n'a pu être analysé")
    
    else:
        # Écran d'accueil
        st.markdown("""
        ## 🛡️ Pourquoi 403 Forbidden ?
        
        Le site `www.assemblee-nationale.fr` utilise des protections avancées:
        
        **Protections détectées:**
        1. **WAF (Web Application Firewall)** : Bloque les requêtes automatiques
        2. **Cloudflare** : Protection DDoS et anti-bot
        3. **JavaScript requis** : Le contenu est chargé dynamiquement
        4. **Rate limiting** : Limite le nombre de requêtes
        
        ## 🔧 Solutions implémentées
        
        ### 1. **Multi-méthodes**
        Combine plusieurs approches pour maximiser les résultats
        
        ### 2. **Google Dorking**
        Utilise Google pour trouver des PDF indexés
        
        ### 3. **Selenium**
        Simule un vrai navigateur avec JavaScript
        
        ### 4. **Rotation d'User-Agents**
        Change l'identité du navigateur
        
        ### 5. **Sites alternatifs**
        Cherche sur d'autres sites qui référencent les PDF
        
        ## 🚀 Instructions
        
        1. **Cliquez sur "🔍 Rechercher PDF"** avec "Multi-méthodes"
        2. **Attendez 1-2 minutes** pour la recherche
        3. **Puis "🔬 Analyser PDF"** pour lire le contenu
        
        ## ⚠️ Limitations
        
        - Le site peut détecter et bloquer le scraping
        - Certains PDF peuvent être protégés
        - La recherche Google peut être limitée
        """)

# Installation requirements
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Installation requise")
st.sidebar.code("""
pip install streamlit requests beautifulsoup4 \
pandas cloudscraper undetected-chromedriver \
selenium pymupdf
""")

if __name__ == "__main__":
    main()
