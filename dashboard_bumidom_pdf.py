def explore_site_structure():
    """Explore la structure du site pour trouver comment rechercher"""
    
    base_url = "https://archives.assemblee-nationale.fr"
    
    try:
        response = requests.get(base_url, timeout=10, headers=get_headers())
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Trouver tous les liens
        links = soup.find_all('a', href=True)
        
        # Chercher des liens de recherche
        search_links = []
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            if any(term in href or term in text for term in ['search', 'recherche', 'chercher', 'find']):
                search_links.append({
                    'text': link.get_text(strip=True),
                    'href': link.get('href'),
                    'full_url': make_absolute_url(link.get('href'))
                })
        
        return search_links
        
    except Exception as e:
        st.error(f"Erreur exploration: {e}")
        return []
