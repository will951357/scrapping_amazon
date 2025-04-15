import os
import logging
import pandas as pd
import time
import pdb

from bs4 import BeautifulSoup as bs
from typing import Dict, List, Optional
from dotenv import load_dotenv
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Carrega a env
load_dotenv()

class AmazonScraper():
    def __init__(self,  headless: bool = True):
        self.base_url = "https://www.amazon.com.br"
        self.user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.logger = self._setup_logger()
        self.driver = self._init_driver(headless)

    def _setup_logger(self) -> logging.Logger:
        """Configura logging para monitoramento."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        return logging.getLogger(__name__)
    
    def _init_driver(self, headless: bool) -> Chrome:
        """Configura o driver do Chrome com opções personalizadas."""
        options = Options()
        if headless:
            options.add_argument("--headless=new")  # Modo headless moderno
        options.add_argument(f"user-agent={self.user_agent}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        driver = Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver
    
    def _get_html(self, url: str) -> Optional[str]:
        """Carrega a URL e retorna o HTML."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item"))
            )
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Erro ao carregar {url}: {e}")
            return None
        
    def _parse_product(self, html: str) -> Dict[str, str]:
        """Extrai dados do produto (usando BeautifulSoup ou Selenium diretamente)."""
        soup = bs(html, "html.parser")
        title = soup.select_one("span#productTitle")
        price = soup.select_one("span.a-price-whole")
        return {
            "title": title.get_text(strip=True) if title else None,
            "price": price.get_text(strip=True) if price else None,
            "url": self.driver.current_url
        }
    
    def scrape_product(self, product_url: str) -> Dict[str, str]:
        """Raspa um produto específico."""
        try:
            self.driver.get(product_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span#productTitle"))
            )
            
            title = self.driver.find_element(By.CSS_SELECTOR, "span#productTitle").text
            price = self.driver.find_element(By.CSS_SELECTOR, "span.a-price-whole").text if self.driver.find_elements(By.CSS_SELECTOR, "span.a-price-whole") else "Preço não encontrado"
            
            return {
                "title": title.strip(),
                "price": price.strip(),
                "url": product_url
            }
        except Exception as e:
            self.logger.error(f"Falha ao raspar {product_url}: {e}")
            return {}
    

    def scrape_search(self, query: str, max_pages: int = 10) -> List[Dict[str, str]]:
        """Raspa resultados de busca."""
        products = []
        product_links = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/s?k={query}&page={page}"
            self.driver.get(url)
            
            # Aguarda o carregamento dos produtos
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@role="listitem"]'))
                )
            except Exception as e:
                self.logger.error(f"Erro ao carregar resultados: {e}")
                continue
    
            # Coleta todos os itens da lista (role="listitem")
            product_elements = []
            product_elements = self.driver.find_elements(By.XPATH, '//div[@data-cy = "title-recipe"]')
            product_info = {
                'titulo': "",
                'valor': "",
                'link': ""
            }
            print(len(product_elements))
            i = 0
            for elem in product_elements:  # Limita a 5 produtos por página (para teste)
                try:
                    link = elem.find_element(By.XPATH, './a[contains(@href, "/dp/")]')
                    
                    href = link.get_attribute("href")
                    if href and "/dp/" in href:  # Filtra apenas URLs de produtos
                        titulo = link.find_element(By.XPATH, './/h2//span').text
                        value_area = elem.find_element(By.XPATH, './following-sibling::div[@data-cy = "price-recipe"]')
                        try:
                            valor = str(value_area.text).split('\n')[0] + ',' + str(value_area.text).split('\n')[1]
                        except IndexError:
                            valor = 0

                        product_info = {
                            'titulo': titulo,
                            'valor': valor,
                            'link': href
                        }

                        product_links.append(product_info)
                except Exception as e:
                    self.logger.warning(f"Erro ao coletar link")
                    continue
                i += 1

        self.save_to_csv(product_links)
            
            
        return products

    def save_to_csv(self, data: List[Dict[str, str]], filename: str = "amazon_products.csv") -> None:
        """Salva dados em CSV."""
        df = pd.DataFrame(data)
        os.makedirs("data", exist_ok=True)
        df.to_csv(f"data/{filename}", index=False)
        self.logger.info(f"Dados salvos em data/{filename}!")