# 🍏 NutriScan: Sistema Inteligente de Gestão Nutricional e Despensa

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688.svg)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-AI-orange.svg)
![Vanilla JS](https://img.shields.io/badge/JavaScript-Vanilla-F7DF1E.svg)

O **NutriScan** é uma aplicação web desenvolvida para automatizar a gestão de alimentos domésticos, combater o desperdício e promover a educação nutricional. Utilizando a Inteligência Artificial do Google Gemini e técnicas de Web Scraping, o sistema lê notas fiscais ou entradas manuais, analisa as compras e cria um painel interativo de saúde.

Projeto desenvolvido como **Projeto Integrador** do Curso de Análise e Desenvolvimento de Sistemas (UNISA).

---

## ✨ Funcionalidades

* 📷 **Leitura de Nota Fiscal (NFC-e):** Cole o link do QR Code da sua nota fiscal e o sistema extrai automaticamente os produtos através de Web Scraping (focado no portal da SEFAZ).
* 🍎 **Feira Livre (Entrada Manual):** Processamento de Linguagem Natural (NLP) para identificar alimentos e quantidades a partir de frases como *"Comprei 1kg de tomate e 2 bananas"*.
* 🧠 **Análise com IA (Classificação NOVA):** A inteligência artificial cataloga cada alimento em *In Natura*, *Processado* ou *Ultraprocessado*, seguindo o Guia Alimentar para a População Brasileira.
* 💧 **Cálculo de Hidratação:** Estima a quantidade de água presente nos alimentos para compor a meta diária de hidratação.
* ⏰ **Gestão de Validades e Alertas:** Estima o tempo de prateleira de cada item na geladeira e avisa o que está prestes a estragar.
* 👨‍🍳 **Chef Anti-Desperdício:** Sugere receitas rápidas utilizando apenas os ingredientes que estão mais próximos da data de vencimento.
* 🏆 **Gamificação (NutriPontos):** Sistema de recompensas e evolução de nível baseado no consumo saudável e na redução de desperdício.

---

## 🛠️ Stack Tecnológica

**Backend:**
* **Python** com **FastAPI** (API RESTful assíncrona)
* **SQLite3** (Banco de dados relacional leve e autocontido)
* **Google GenAI API** (Modelo `gemma-3-1b-it` para inferência)
* **BeautifulSoup4** (Parsing HTML para scraping)

**Frontend:**
* **HTML5, CSS3, Vanilla JavaScript** (Arquitetura Single Page Application - SPA)
* Design Mobile-First com fontes do Google Fonts (Comfortaa).

---

## 🚀 Como Executar o Projeto Localmente

### 1. Clonar o Repositório
```bash
git clone [https://github.com/seu-usuario/nutriscan.git](https://github.com/seu-usuario/nutriscan.git)
cd nutriscan
