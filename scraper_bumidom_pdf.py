import requests
import fitz  # PyMuPDF
import io
import pandas as pd
import re
import os
from datetime import datetime
import time
from bs4 import BeautifulSoup
import urllib.parse

class PDFBUMIDOMScraper:
    def __init__(self):
        self.base_url = "http://archives.assemblee-nationale.fr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.pdf_data_dir = "pdf_documents"
        os.makedirs(self.pdf_data_dir, exist_ok=True)
    
    def find_pdf_links(self, search_term="BUMIDOM", max_pages=10):
        """Trouve les liens PDF contenant le terme BUMIDOM"""
        print(f"Recherche de PDF contenant '{search_term}'...")
        
        pdf_links = []
        search_patterns = [
            "bumidom", "BUMIDOM", "Bureau.*migration.*outre-mer",
            "départements.*outre-mer.*migration"
        ]
        
        # URLs à explorer pour trouver des PDF
        base_urls = [
            f"{self.base_url}/14/documents/",
            f"{self.base_url}/13/documents/",
            f"{self.base_url}/12/documents/",
            f"{self.base_url}/11/documents/",
            f"{self.base_url}/10/documents/",
            f"{self.base_url}/9/documents/"
        ]
        
        for base_url in base_urls:
            try:
                print(f"Exploration de {base_url}")
                response = self.session.get(base_url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Recherche tous les liens PDF
                pdf_elements = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for element in pdf_elements[:20]:  # Limite pour éviter trop de requêtes
                    pdf_url = element['href']
                    if not pdf_url.startswith('http'):
                        pdf_url = urllib.parse.urljoin(base_url, pdf_url)
                    
                    pdf_title = element.get_text(strip=True) or element.get('title', '')
                    
                    # Vérifier si le titre suggère un contenu BUMIDOM
                    if any(pattern.lower() in pdf_title.lower() for pattern in search_patterns):
                        pdf_links.append({
                            'url': pdf_url,
                            'title': pdf_title,
                            'source_url': base_url
                        })
                        print(f"  PDF trouvé: {pdf_title}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Erreur avec {base_url}: {e}")
                continue
        
        return pdf_links
    
    def download_and_analyze_pdf(self, pdf_info):
        """Télécharge et analyse un PDF"""
        try:
            print(f"Téléchargement: {pdf_info['title']}")
            response = self.session.get(pdf_info['url'], timeout=30)
            
            if response.status_code == 200:
                # Sauvegarde du PDF
                filename = re.sub(r'[^\w\-_\. ]', '_', pdf_info['title'][:100])
                filename = f"{filename}.pdf"
                filepath = os.path.join(self.pdf_data_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Analyse du contenu PDF
                pdf_data = self.extract_pdf_content(response.content, pdf_info)
                
                # Ajouter les métadonnées de fichier
                pdf_data.update({
                    'fichier_pdf': filename,
                    'chemin_local': filepath,
                    'taille_ko': len(response.content) / 1024
                })
                
                return pdf_data
                
        except Exception as e:
            print(f"Erreur lors du téléchargement {pdf_info['url']}: {e}")
        
        return None
    
    def extract_pdf_content(self, pdf_content, pdf_info):
        """Extrait le contenu et les métadonnées d'un PDF"""
        try:
            # Ouvrir le PDF depuis la mémoire
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            # Extraire le texte
            full_text = ""
            for page_num in range(min(10, pdf_document.page_count)):  # Limiter aux 10 premières pages
                page = pdf_document[page_num]
                full_text += page.get_text()
            
            # Analyser le contenu pour le BUMIDOM
            bumidom_info = self.analyze_bumidom_content(full_text)
            
            # Extraire les métadonnées
            metadata = pdf_document.metadata
            
            pdf_document.close()
            
            # Structure des données extraites
            return {
                'titre': pdf_info['title'],
                'url': pdf_info['url'],
                'source': pdf_info['source_url'],
                'nombre_pages': pdf_document.page_count,
                'texte_complet': full_text[:5000],  # Limiter pour la base de données
                'mots_cles_bumidom': bumidom_info.get('mots_cles', []),
                'mentions_bumidom': bumidom_info.get('mentions', 0),
                'contextes_bumidom': bumidom_info.get('contextes', []),
                'date_extraction': datetime.now().strftime('%Y-%m-%d'),
                'auteur': metadata.get('author', 'Inconnu'),
                'date_creation': metadata.get('creationDate', 'Inconnue'),
                'sujet': metadata.get('subject', '')
            }
            
        except Exception as e:
            print(f"Erreur d'extraction PDF: {e}")
            return {
                'titre': pdf_info['title'],
                'url': pdf_info['url'],
                'source': pdf_info['source_url'],
                'erreur': str(e)
            }
    
    def analyze_bumidom_content(self, text):
        """Analyse spécifique du contenu BUMIDOM"""
        text_lower = text.lower()
        
        # Mots-clés liés au BUMIDOM
        keywords = [
            'bumidom', 'bureau.*migration.*outre-mer',
            'départements.*outre-mer', 'dom', 'martinique', 'guadeloupe',
            'guyane', 'réunion', 'mayotte', 'migration.*organisée',
            'transfert.*population', 'émigration.*organisée'
        ]
        
        found_keywords = []
        contexts = []
        mentions = 0
        
        for keyword in keywords:
            pattern = re.compile(keyword, re.IGNORECASE)
            matches = pattern.findall(text)
            if matches:
                found_keywords.append(keyword.replace('.*', ''))
                mentions += len(matches)
                
                # Extraire le contexte des mentions
                for match in matches[:3]:  # Premières 3 occurrences
                    start = max(0, text_lower.find(match) - 100)
                    end = min(len(text), text_lower.find(match) + len(match) + 100)
                    context = text[start:end].replace('\n', ' ')
                    contexts.append(context.strip())
        
        return {
            'mots_cles': list(set(found_keywords)),
            'mentions': mentions,
            'contextes': contexts[:5]  # Limiter à 5 contextes
        }
    
    def search_questions_ecrites(self):
        """Recherche spécifique dans les questions écrites"""
        print("\nRecherche dans les questions écrites...")
        
        questions_data = []
        
        # Recherche dans différentes législatures
        for legislature in range(8, 15):
            try:
                url = f"{self.base_url}/{legislature}/qst/index.html"
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Recherche de liens contenant BUMIDOM
                links = soup.find_all('a', string=re.compile(r'bumidom', re.I))
                
                for link in links[:10]:
                    question_url = link.get('href')
                    if question_url:
                        if not question_url.startswith('http'):
                            question_url = urllib.parse.urljoin(url, question_url)
                        
                        # Vérifier si c'est un PDF
                        if '.pdf' in question_url.lower():
                            questions_data.append({
                                'url': question_url,
                                'titre': link.get_text(strip=True),
                                'legislature': legislature,
                                'type': 'question_ecrite'
                            })
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Erreur législature {legislature}: {e}")
                continue
        
        return questions_data
    
    def run_complete_scrape(self):
        """Exécute un scraping complet"""
        print("=== Début du scraping BUMIDOM ===\n")
        
        all_data = []
        
        # 1. Recherche de PDF généraux
        print("1. Recherche de PDF...")
        pdf_links = self.find_pdf_links(max_pages=5)
        
        for pdf_info in pdf_links[:10]:  # Limiter à 10 PDF
            pdf_data = self.download_and_analyze_pdf(pdf_info)
            if pdf_data:
                all_data.append(pdf_data)
                print(f"  ✓ Analysé: {pdf_data['titre']}")
                time.sleep(2)  # Respect du serveur
        
        # 2. Recherche dans les questions écrites
        print("\n2. Recherche dans les questions écrites...")
        questions = self.search_questions_ecrites()
        
        for q_info in questions[:5]:
            q_data = self.download_and_analyze_pdf(q_info)
            if q_data:
                all_data.append(q_data)
                print(f"  ✓ Question: {q_data['titre']}")
                time.sleep(2)
        
        # 3. Sauvegarde des données
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Sauvegarde CSV
            csv_file = 'bumidom_pdf_analysis.csv'
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ {len(all_data)} documents analysés")
            print(f"✓ Données sauvegardées dans: {csv_file}")
            print(f"✓ PDFs sauvegardés dans: {self.pdf_data_dir}/")
            
            # Créer un fichier de résumé
            self.create_summary_report(df)
            
            return df
        else:
            print("\n✗ Aucun document trouvé")
            return None
    
    def create_summary_report(self, df):
        """Crée un rapport de synthèse"""
        report = f"""
        RAPPORT D'ANALYSE BUMIDOM
        =========================
        Date d'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        Documents analysés: {len(df)}
        
        RÉSUMÉ DES DOCUMENTS:
        ---------------------
        """
        
        for idx, row in df.iterrows():
            report += f"""
        Document {idx + 1}:
        - Titre: {row.get('titre', 'N/A')}
        - Pages: {row.get('nombre_pages', 'N/A')}
        - Mentions BUMIDOM: {row.get('mentions_bumidom', 0)}
        - Mots-clés: {', '.join(row.get('mots_cles_bumidom', []))}
        - Source: {row.get('source', 'N/A')}
        """
        
        # Statistiques
        total_mentions = df['mentions_bumidom'].sum() if 'mentions_bumidom' in df.columns else 0
        
        report += f"""
        
        STATISTIQUES:
        -------------
        - Total mentions BUMIDOM: {total_mentions}
        - Documents avec mention BUMIDOM: {len(df[df['mentions_bumidom'] > 0])}
        - Taille moyenne: {df['taille_ko'].mean() if 'taille_ko' in df.columns else 'N/A':.1f} Ko
        
        FICHIERS PDF:
        -------------
        """
        
        for pdf_file in os.listdir(self.pdf_data_dir):
            if pdf_file.endswith('.pdf'):
                filepath = os.path.join(self.pdf_data_dir, pdf_file)
                size = os.path.getsize(filepath) / 1024
                report += f"  - {pdf_file} ({size:.1f} Ko)\n"
        
        # Sauvegarder le rapport
        with open('rapport_bumidom.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✓ Rapport généré: rapport_bumidom.txt")

# Exécution
if __name__ == "__main__":
    scraper = PDFBUMIDOMScraper()
    data = scraper.run_complete_scrape()
    
    if data is not None:
        print("\n=== Données extraites ===")
        print(data[['titre', 'mentions_bumidom', 'nombre_pages', 'source']])
