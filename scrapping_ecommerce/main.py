from scraper import AmazonScraper
import time

def main():
    # Inicializa o scraper (headless=False para ver o navegador em ação)
    scraper = AmazonScraper(headless=False)
    
    try:
        # Exemplo: Raspar busca por "iphone" (1 página)
        products = scraper.scrape_search("iphone", max_pages=10)
        scraper.save_to_csv(products, "amazon_iphone.csv")
        
    finally:
        ... #scraper.close()  # Garante que o navegador será fechado

if __name__ == "__main__":
    main()