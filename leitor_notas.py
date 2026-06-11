import requests
from bs4 import BeautifulSoup
import json
import google.generativeai as genai
from collections import Counter  # <-- Adicionado para a lista inteligente

# =========================================================
# CONFIGURAÇÕES GERAIS
# =========================================================
# Substitua pela chave que você gerou no Google AI Studio
GOOGLE_API_KEY = "AIzaSyCGRpk5LoL3ZOVHyFjXcqTdnHwLhNUSAL4"
genai.configure(api_key=GOOGLE_API_KEY)

# =========================================================
# FUNÇÃO 1: O Web Scraper (Raspador de Dados REAL - PR)
# =========================================================
def raspar_dados_sefaz(url_nota):
    print(f"\n[1] Acessando o portal da nota fiscal: {url_nota[:30]}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    try:
        resposta = requests.get(url_nota, headers=headers)
        resposta.raise_for_status() 
        sopa = BeautifulSoup(resposta.text, 'html.parser')
        
        # Buscando pela classe 'txtTit2' do Paraná
        tags_produtos = sopa.find_all('span', class_='txtTit2')
        
        itens_extraidos = []
        for tag in tags_produtos:
            nome_produto = tag.get_text(strip=True)
            if nome_produto:
                itens_extraidos.append(nome_produto)
        
        print(f" -> Encontrados {len(itens_extraidos)} itens na nota.")
        return itens_extraidos

    except Exception as e:
        print(f" -> Erro ao tentar acessar o link da SEFAZ: {e}")
        return []

# =========================================================
# FUNÇÃO 2: A Inteligência (Hidratação e Validade)
# =========================================================
def analisar_alimentos_com_gemini(lista_itens):
    if not lista_itens:
        return []
        
    print("[2] Enviando dados para o Gemini (Análise Nutricional)...")
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash', # Atualizado para o seu modelo
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    Aja como um nutricionista e engenheiro de dados. Analise a seguinte lista de compras: {lista_itens}
    Para cada item, identifique o nome real, a categoria, a validade estimada na geladeira em dias, e os mililitros de água que esse alimento fornece.
    Devolva APENAS uma lista JSON com chaves: nome_produto, categoria, validade_dias, agua_ml.
    """
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f" -> Erro ao consultar o Gemini: {e}")
        return []

# =========================================================
# FUNÇÃO 3: A Lista Inteligente (Hábitos)
# =========================================================
def gerar_lista_inteligente(historico_compras):
    print("\n[3] Analisando seu histórico para gerar a Lista Inteligente...")
    
    todos_os_itens = [item for compra in historico_compras for item in compra]
    total_compras = len(historico_compras)
    contagem = Counter(todos_os_itens)
    
    itens_recorrentes = [item for item, freq in contagem.items() if freq / total_compras >= 0.5]
    
    model = genai.GenerativeModel(
        'models/gemini-2.5-flas',
        generation_config={"response_mime_type": "application/json"}
    )
    
    perfil_consumo = ", ".join(contagem.keys())
    
    prompt = f"""
    O usuário costuma comprar estes itens: {perfil_consumo}.
    Sugira APENAS UM novo ingrediente estratégico (saudável, barato e de longa validade) para adicionar à lista para melhorar a saúde.
    Retorne um JSON com:
    - 'sugestao_item': Nome do produto sugerido.
    - 'justificativa': Uma frase curta explicando o benefício prático.
    """
    
    try:
        response = model.generate_content(prompt)
        sugestao_ia = json.loads(response.text)
        return {"itens_base": itens_recorrentes, "upgrade_saudavel": sugestao_ia}
    except Exception as e:
        print(f" -> Erro ao gerar sugestão: {e}")
        return {"itens_base": itens_recorrentes, "upgrade_saudavel": None}

# =========================================================
# EXECUÇÃO PRINCIPAL (Testando tudo de uma vez)
# =========================================================
if __name__ == "__main__":
    print("=== INICIANDO SISTEMA DO APP ===")
    
    # 1. Testando a Leitura da Nota (O "Hoje")
    url_qr_code = "https://www.fazenda.pr.gov.br/nfce/qrcode?p=41260278413325001327650680003137911904698441|2|1|1|58D4AF6AE2430EF7B89F1343BD8A9D38B678EA60" 
    itens_extraidos = raspar_dados_sefaz(url_qr_code)
    dados_processados = analisar_alimentos_com_gemini(itens_extraidos)
    
    if dados_processados:
        print("\n--- RECOMPENSA IMEDIATA ---")
        agua_total = 0
        for item in dados_processados:
            print(f"🛒 {item.get('nome_produto', 'Desconhecido')} | ⏳ Estraga em: {item.get('validade_dias', 0)} dias | 💧 Hidratação: {item.get('agua_ml', 0)} ml")
            agua_total += item.get('agua_ml', 0)
        print(f"🎯 RESUMO: Garantidos {agua_total} ml de água 'mastigável'!")

    # 2. Testando a Lista Inteligente (O "Futuro")
    # Aqui, além da nota que você acabou de ler, simulamos que havia outras compras anteriores.
    meu_historico_simulado = [
        ["PAO FRANCES KG", "OLEO SOJA LIZA PET 9", "REFRIGERANTE 2L", "SAB PALMOLIVE 150G H"],
        ["PAO FRANCES KG", "UVA VITORIA BDJ 500G", "REFRIGERANTE 2L", "PAO QUEIJO MINEIRACO"],
        itens_extraidos # Adicionamos a nota real de hoje no histórico!
    ]
    
    lista_final = gerar_lista_inteligente(meu_historico_simulado)
    
    print("\n--- SUA PRÓXIMA LISTA DE COMPRAS ---")
    print("✅ Já adicionamos o que você sempre compra:")
    for item in lista_final['itens_base']:
        print(f" - [ ] {item}")
        
    if lista_final['upgrade_saudavel']:
        s = lista_final['upgrade_saudavel']
        print(f"\n✨ Sugestão Extra do App: {s.get('sugestao_item')}")
        print(f"💡 Por que? {s.get('justificativa')}")
        
    print("\n=== FIM DO PROCESSAMENTO ===")